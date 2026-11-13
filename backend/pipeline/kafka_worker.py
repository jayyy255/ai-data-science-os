"""Database-worker training pipeline. No synthetic data or fabricated metrics."""
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import LabelEncoder

class EncodedClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, estimator): self.estimator = estimator
    def fit(self, X, y):
        self.encoder_ = LabelEncoder().fit(y)
        self.classes_ = self.encoder_.classes_
        self.estimator.fit(X, self.encoder_.transform(y))
        return self
    def predict(self, X): return self.encoder_.inverse_transform(self.estimator.predict(X).astype(int))
    def predict_proba(self, X): return self.estimator.predict_proba(X)

class TrainingWorker:
    def __init__(self, db_session_maker=None):
        self.db_session_maker = db_session_maker

    def update_models_comparison_db(self, project_id, comparison):
        from database.models import KnowledgeCard
        with self.db_session_maker() as db:
            card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
            if card:
                card.models_comparison_json = comparison
                db.commit()

    def process_training_job(self, project_id, target, problem_type, imputation_method='Median', features_override=None):
        from database.models import Project, DecisionMemory, TrainingJob
        from services.storage.factory import get_storage_provider
        from services.sandbox import run_operation
        storage = get_storage_provider()
        with self.db_session_maker() as db:
            project = db.query(Project).filter_by(id=project_id).first()
            if not project or not project.dataset_path:
                raise ValueError('Uploaded dataset is missing')
            data = storage.download_file(project.dataset_path)
            choices = {d.feature_name: d.user_choice if d.override_active else 'Keep Raw' if d.decision.startswith('Impute ') else d.decision for d in db.query(DecisionMemory).filter_by(project_id=project_id).all()}
        self.update_models_comparison_db(project_id, {name: {'status': 'Training', 'phase': 'Sandboxed HPO', 'metric': None} for name in ['Random Forest', 'XGBoost', 'LightGBM', 'Neural Network']})
        try:
            result, artifacts, audit = run_operation('train', {'target': target, 'problem_type': problem_type, 'imputation_method': imputation_method, 'choices': choices}, {'dataset.csv': data}, with_audit=True)
        except Exception as error:
            from services.sandbox import redact
            message = redact(str(error))[:1000]
            self.update_models_comparison_db(project_id, {name: {'status': 'Failed', 'metric': None, 'error': message} for name in ['Random Forest', 'XGBoost', 'LightGBM', 'Neural Network']})
            with self.db_session_maker() as db:
                job = db.query(TrainingJob).filter_by(project_id=project_id).order_by(TrainingJob.id.desc()).first()
                if job:
                    job.metrics_json = {'error': message, 'execution_log': [{'event': 'sandbox_failed', 'message': message}], 'sandbox': getattr(error, 'audit', {})}
                    db.commit()
            raise
        paths = {}
        for filename, content in artifacts.items():
            paths[filename] = storage.upload_model(project_id, filename.removesuffix('.pkl'), content)
        for item in result['models_comparison'].values():
            if item.get('artifact_path'):
                item['artifact_path'] = paths[item['artifact_path']]
        result['model_path'] = paths[result['model_path']]
        result['sandbox'] = audit
        self.update_models_comparison_db(project_id, result['models_comparison'])
        with self.db_session_maker() as db:
            job = db.query(TrainingJob).filter_by(project_id=project_id).order_by(TrainingJob.id.desc()).first()
            if job:
                job.metrics_json = {**(job.metrics_json or {}), 'execution_log': result['execution_log'], 'model_selection': result['model_selection'], 'sandbox': audit, 'hpo_trials': result['hpo_trials']}
                db.commit()
        return result
