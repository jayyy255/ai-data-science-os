"""Run from backend: python -m unittest discover -s tests -v."""
import io
import json
import os
import pickle
import tempfile
import unittest
from pathlib import Path

# Every run uses isolated storage and a disposable database.
Path('tmp').mkdir(exist_ok=True)
test_directory = tempfile.TemporaryDirectory(dir=Path('tmp').resolve())
os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(test_directory.name) / 'test.db').as_posix()
os.environ['LOCAL_STORAGE_DIR'] = str(Path(test_directory.name) / 'artifacts')
os.environ['ENVIRONMENT'] = 'local'
os.environ['AIDSO_LOAD_ENV_FILE'] = '0'
os.environ.pop('MINIO_ENDPOINT', None)
os.environ.pop('REDIS_URL', None)
os.environ.pop('GEMINI_API_KEY', None)

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from main import app
from database.connection import SessionLocal, engine
from database.models import KnowledgeCard, Project, TrainingJob
from database.schema import initialize_database
from pipeline.kafka_worker import TrainingWorker


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.other = TestClient(app)
        for client, username in [(cls.client, 'workflow'), (cls.other, 'other')]:
            result = client.post('/api/auth/signup', json={'full_name': 'Test User', 'username': username, 'email': username + '@example.test', 'password': 'test-password-123'})
            assert result.status_code == 200, result.text
        rng = np.random.default_rng(41)
        size = 150
        spend = rng.normal(80, 20, size)
        age = rng.integers(18, 70, size).astype(float)
        target = np.where(spend > 90, 'high', np.where(age > 45, 'medium', 'low'))
        age[::17] = np.nan
        cls.frame = pd.DataFrame({'age': age, 'spend': spend, 'segment': rng.choice(['basic', 'premium'], size), 'empty': np.nan, 'target': target})

    def create(self, frame=None, name='Workflow'):
        frame = self.frame if frame is None else frame
        result = self.client.post('/api/projects', data={'name': name, 'target_variable': 'target', 'description': 'Predict test outcome'}, files={'file': ('data.csv', frame.to_csv(index=False).encode(), 'text/csv')})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['project']['id']

    def test_gemini_local_file_and_production_environment_precedence(self):
        from services.gemini import GeminiService
        from unittest.mock import patch
        with patch('services.gemini.Path.is_file', return_value=True), patch('services.gemini.dotenv_values', return_value={'GEMINI_API_KEY': 'local-test-key'}) as read_file, patch('services.gemini.genai.Client') as client:
            with patch.dict(os.environ, {'ENVIRONMENT': 'local', 'AIDSO_LOAD_ENV_FILE': '1', 'GEMINI_API_KEY': 'inherited-test-key'}):
                GeminiService()
                self.assertEqual(client.call_args.kwargs['api_key'], 'local-test-key')
            client.reset_mock(); read_file.reset_mock()
            with patch.dict(os.environ, {'ENVIRONMENT': 'production', 'GEMINI_API_KEY': 'production-test-key'}):
                GeminiService()
                self.assertEqual(client.call_args.kwargs['api_key'], 'production-test-key')
                read_file.assert_not_called()
            client.reset_mock(); read_file.reset_mock()
            with patch.dict(os.environ, {'ENVIRONMENT': 'local', 'AIDSO_LOAD_ENV_FILE': '0', 'GEMINI_API_KEY': 'isolated-test-key'}):
                GeminiService()
                self.assertEqual(client.call_args.kwargs['api_key'], 'isolated-test-key')
                read_file.assert_not_called()

    def test_assistant_falls_back_when_provider_fails(self):
        from services.gemini import GeminiService
        from unittest.mock import Mock
        service = GeminiService()
        service.client_enabled = True
        service.client = Mock()
        service.client.models.generate_content.side_effect = RuntimeError('Provider unavailable')
        answer = service.assistant_chat('Explain the champion', {
            'target': 'sales', 'problem_type': 'regression', 'best_model': 'Random Forest',
            'best_mse': 12.5, 'rows_count': 150, 'columns_count': 5,
            'status': 'Ready', 'decisions': [], 'top_features': ['spend']}, [])
        self.assertIn('local summary', answer)
        self.assertIn('test MSE: 12.5', answer)
        self.assertIn('Random Forest', answer)
        self.assertIn('sales', answer)
        self.assertNotIn('F1:', answer)

    def test_authentication_isolation_and_revocation(self):
        project_id = self.create()
        self.assertEqual(self.other.get(f'/api/projects/{project_id}').status_code, 404)
        self.assertEqual(TestClient(app).get('/api/projects').status_code, 401)
        client = TestClient(app)
        result = client.post('/api/auth/login', json={'identity': 'workflow', 'password': 'wrong'})
        self.assertEqual(result.status_code, 401)
        result = client.post('/api/auth/login', json={'identity': 'workflow', 'password': 'test-password-123'})
        token = result.json()['refreshToken']
        self.assertEqual(client.get('/api/projects').status_code, 200)
        client.post('/api/auth/logout', json={'refresh_token': token})
        self.assertEqual(client.get('/api/projects', headers={'Authorization': 'Bearer ' + token}).status_code, 401)

    def test_upload_validation_and_unique_identity(self):
        first, second = self.create(name='Same name'), self.create(name='Same name')
        self.assertNotEqual(first, second)
        detail = self.client.get(f'/api/projects/{first}').json()
        self.assertEqual(detail['project']['target_variable'], 'target')
        self.assertEqual(detail['project']['description'], 'Predict test outcome')
        self.assertEqual(detail['cached_eda']['rows_count'], 150)
        for raw, target in [(b'a,b\n1,2\n', 'missing'), (b'a,target\n', 'target'), (b'a,target\n1,yes\n2,yes\n', 'target'), (b'%PDFfake', 'target')]:
            result = self.client.post('/api/projects', data={'name': 'Bad', 'target_variable': target, 'description': ''}, files={'file': ('bad.csv', raw, 'text/csv')})
            self.assertEqual(result.status_code, 400, result.text)
        self.assertEqual(self.client.get('/api/projects/download-local-file', params={'filename': '../main.py'}).status_code, 400)

    def test_transformations_are_idempotent_and_reversible(self):
        project_id = self.create()
        def transform(choice):
            result = self.client.post(f'/api/projects/{project_id}/transform', json={'feature_name': 'segment', 'transformation': choice})
            self.assertEqual(result.status_code, 200, result.text)
            return self.client.get(f'/api/projects/{project_id}/download-transformed').content
        encoded = transform('One-Hot Encoding')
        self.assertEqual(encoded, transform('One-Hot Encoding'))
        original = transform('Keep Raw')
        self.assertIn('segment', pd.read_csv(io.BytesIO(original)).columns)
        self.assertNotIn('segment_basic', pd.read_csv(io.BytesIO(original)).columns)
        self.assertEqual(encoded, transform('recommended'))
        for feature, choice in [('target', 'Standard Scaling'), ('age', 'unsupported')]:
            result = self.client.post(f'/api/projects/{project_id}/transform', json={'feature_name': feature, 'transformation': choice})
            self.assertEqual(result.status_code, 400)

    def test_imputation_and_drift_use_real_data(self):
        project_id = self.create()
        for method in ['Median', 'Mean', 'Mode', 'KNN']:
            result = self.client.get(f'/api/projects/{project_id}/download-dataset', params={'imputation_method': method})
            self.assertEqual(result.status_code, 200, result.text)
            data = pd.read_csv(io.BytesIO(result.content))
            self.assertFalse(data.drop(columns='target').isna().any().any())
            self.assertEqual(data['target'].tolist(), self.frame['target'].tolist())
        raw = self.frame.to_csv(index=False).encode()
        result = self.client.post(f'/api/projects/{project_id}/monitor', files={'file': ('baseline.csv', raw, 'text/csv')})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['driftPsi'], 0)
        shifted = self.frame.copy()
        shifted['spend'] += 500
        result = self.client.post(f'/api/projects/{project_id}/monitor', files={'file': ('shift.csv', shifted.to_csv(index=False).encode(), 'text/csv')})
        self.assertEqual(result.json()['driftStatus'], 'DRIFT DETECTED')
        self.assertEqual(self.client.get(f'/api/projects/{project_id}/monitor').json(), result.json())
        self.assertEqual(self.other.get(f'/api/projects/{project_id}/monitor').status_code, 404)

    def test_classification_and_regression_pipeline_artifacts(self):
        for kind in ['classification', 'regression']:
            frame = self.frame.copy()
            if kind == 'regression': frame['target'] = frame['spend'] * 2.3 + np.arange(len(frame)) * .01
            project_id = self.create(frame)
            result = self.client.post(f'/api/projects/{project_id}/train', params={'imputation_method': 'KNN'})
            self.assertEqual(result.status_code, 200)
            self.client.post(f'/api/projects/{project_id}/train')
            self.assertEqual(len(self.client.get(f'/api/projects/{project_id}/jobs').json()['jobs']), 1)
            result = TrainingWorker(SessionLocal).process_training_job(project_id, 'target', kind, 'KNN')
            self.assertGreaterEqual(len(result['models_comparison']), 2)
            self.assertEqual(len(result['hpo_trials']), len(result['models_comparison']) * 5)
            self.assertEqual({trial['model'] for trial in result['hpo_trials']}, set(result['models_comparison']))
            from services.storage.factory import get_storage_provider
            for model in result['models_comparison'].values():
                self.assertEqual(model['status'], 'Trained', model)
                fitted = pickle.loads(get_storage_provider().download_file(model['artifact_path']))
                sample = frame.drop(columns='target').head(3)
                self.assertEqual(len(fitted.predict(sample)), 3)
                self.assertIn('numeric_knn', fitted.named_steps['preprocess'].named_transformers_)
                unseen = sample.copy(); unseen['segment'] = 'unseen-category'
                self.assertEqual(len(fitted.predict(unseen)), 3)
            with SessionLocal() as db:
                card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
                card.model_path = result['model_path']; card.models_comparison_json = result['models_comparison']
                project = db.query(Project).filter_by(id=project_id).first(); project.status = 'Ready for Deployment'
                job = db.query(TrainingJob).filter_by(project_id=project_id).first(); job.status = 'completed'
                db.commit()
            rows = json.loads(frame.drop(columns='target').head(3).to_json(orient='records'))
            response = self.client.post(f'/api/projects/{project_id}/predict', json={'rows': rows})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()['predictions']), 3)
            self.assertEqual(self.client.get(f'/api/projects/{project_id}/explain/0').status_code, 200)
            self.assertEqual(self.client.get(f'/api/projects/{project_id}/explain/99999').status_code, 400)
            self.client.post(f'/api/projects/{project_id}/champion', json={'model_name': 'Neural Network'})
            neural_explanation = self.client.get(f'/api/projects/{project_id}/explain/0')
            self.assertTrue(neural_explanation.json()['drivers'], neural_explanation.text)
            name = next(iter(result['models_comparison']))
            response = self.client.post(f'/api/projects/{project_id}/champion', json={'model_name': name})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.client.get(f'/api/projects/{project_id}/download-model', params={'model_name': name}).status_code, 200)
            self.assertEqual(self.other.post(f'/api/projects/{project_id}/predict', json={'rows': rows}).status_code, 404)

    def test_profile_detects_dates_and_text_and_real_quality_issues(self):
        from services.dataset import DatasetService
        frame = pd.DataFrame({'amount': [1., 2., 3., 1000.] + [4.] * 30,
            'day': ['2026-10-12'] * 34,
            'notes': ['A detailed free text observation containing several different words for the profile detector.'] * 34,
            'category': ['a', 'b'] * 17, 'target': ['yes'] * 30 + ['no'] * 4})
        profile = DatasetService.profile_dataset(frame.to_csv(index=False).encode(), 'target')
        self.assertEqual(profile['datetime_count'], 1)
        self.assertEqual(profile['text_count'], 1)
        self.assertEqual(profile['categorical_count'], 2)
        self.assertIn('outliers found', profile['quality_health']['outliers'])
        self.assertNotEqual(profile['quality_health']['duplicates'], '0 duplicates')
        self.assertIn('Imbalance detected', profile['quality_health']['classImbalance'])
        self.assertEqual(profile['features'][1]['semantic_type'], 'datetime')

    def test_model_download_preserves_custom_bucket_artifact_path(self):
        from unittest.mock import Mock, patch
        project_id = self.create()
        path = f's3://custom-production-bucket/models/{project_id}/random_forest.pkl'
        with SessionLocal() as db:
            card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
            card.model_path = path
            card.models_comparison_json = {'Random Forest': {'status': 'Trained', 'artifact_path': path}}
            db.commit()
        storage = Mock()
        storage.download_file.return_value = b'pipeline-bytes'
        storage.generate_presigned_download_url.return_value = 'https://example.test/signed-model'
        with patch('routers.projects.storage', storage):
            response = self.client.get(f'/api/projects/{project_id}/download-model', params={'model_name': 'Random Forest'})
            self.assertEqual(response.content, b'pipeline-bytes')
            storage.download_file.assert_called_once_with(path)
            response = self.client.get(f'/api/projects/{project_id}/presigned-download-model', params={'model_name': 'Random Forest'})
            self.assertEqual(response.status_code, 200)
            storage.generate_presigned_download_url.assert_called_once_with(path)
            response = self.client.get(f'/api/projects/{project_id}/download-model', params={'model_name': '../missing'})
            self.assertEqual(response.status_code, 404)

    def test_schema_upgrade_is_repeatable(self):
        initialize_database(engine)
        initialize_database(engine)
        self.assertEqual(self.client.get('/api/projects').status_code, 200)

def tearDownModule():
    WorkflowTests.client.close()
    WorkflowTests.other.close()
    engine.dispose()
    test_directory.cleanup()

if __name__ == '__main__': unittest.main()
