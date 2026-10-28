"""Download three UCI datasets and test the running local API/worker.

Run from the repository root: python scripts/verify_public_datasets.py
Only public benchmark data is uploaded. Projects remain available for review.
Requires the seeded local demo account and local services on port 8002.
"""
import io
import json
import pickle
import shlex
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import httpx
import numpy as np
import pandas as pd

DATASETS = [
    {'name': 'UCI Iris - Species', 'slug': 'iris', 'target': 'species', 'task': 'classification',
     'page': 'https://archive.ics.uci.edu/dataset/53/iris',
     'download': 'https://archive.ics.uci.edu/static/public/53/iris.zip', 'file': 'iris.data', 'rows': 150},
    {'name': 'UCI Banknote - Authenticity', 'slug': 'banknote', 'target': 'authenticity', 'task': 'classification',
     'page': 'https://archive.ics.uci.edu/dataset/267/banknote%2Bauthentication',
     'download': 'https://archive.ics.uci.edu/static/public/267/banknote%2Bauthentication.zip',
     'file': 'data_banknote_authentication.txt', 'rows': 1372},
    {'name': 'UCI Auto MPG - Fuel Economy', 'slug': 'auto-mpg', 'target': 'mpg', 'task': 'regression',
     'page': 'https://archive.ics.uci.edu/dataset/9/auto%2Bmpg',
     'download': 'https://archive.ics.uci.edu/static/public/9/auto%2Bmpg.zip', 'file': 'auto-mpg.data', 'rows': 398},
]


def prepare(dataset):
    folder = ROOT / 'tmp' / 'public-datasets'
    folder.mkdir(parents=True, exist_ok=True)
    response = httpx.get(dataset['download'], timeout=60, follow_redirects=True)
    response.raise_for_status()
    (folder / (dataset['slug'] + '.zip')).write_bytes(response.content)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        member = next(name for name in archive.namelist() if Path(name).name == dataset['file'])
        raw = archive.read(member)  # No arbitrary archive paths are extracted.
    (folder / dataset['file']).write_bytes(raw)
    if dataset['slug'] == 'iris':
        frame = pd.read_csv(io.BytesIO(raw), header=None, names=['sepal_length', 'sepal_width', 'petal_length', 'petal_width', 'species'])
    elif dataset['slug'] == 'banknote':
        frame = pd.read_csv(io.BytesIO(raw), header=None, names=['variance', 'skewness', 'kurtosis', 'entropy', 'authenticity'])
    else:
        records = [shlex.split(line) for line in raw.decode().splitlines() if line.strip()]
        frame = pd.DataFrame(records, columns=['mpg', 'cylinders', 'displacement', 'horsepower', 'weight', 'acceleration', 'model_year', 'origin', 'car_name'])
        frame = frame.drop(columns='car_name')  # UCI marks car_name as an ID, not a predictor.
        for column in frame:
            frame[column] = pd.to_numeric(frame[column].replace('?', np.nan))
        frame['origin'] = frame['origin'].map({1: 'USA', 2: 'Europe', 3: 'Japan'})
    assert len(frame) == dataset['rows'], 'Unexpected UCI dataset size'
    path = folder / (dataset['slug'] + '.csv')
    frame.to_csv(path, index=False)
    dataset.update(csv=str(path), missing_cells=int(frame.isna().sum().sum()))
    print(f"Downloaded {dataset['slug']}: {len(frame)} rows, {len(frame.columns)} columns, {dataset['missing_cells']} missing cells", flush=True)
    return dataset, frame


def main():
    prepared = list(ThreadPoolExecutor(max_workers=3).map(prepare, DATASETS))
    results = []
    folder = ROOT / 'tmp' / 'public-datasets'
    with httpx.Client(base_url='http://127.0.0.1:8002/api', timeout=120) as client:
        response = client.post('/auth/login', json={'identity': 'dummy_user', 'password': 'password123'})
        response.raise_for_status()
        token = response.json()['refreshToken']
        try:
            for dataset, frame in prepared:
                response = client.post('/projects', data={'name': dataset['name'], 'target_variable': dataset['target'],
                    'problem_type': 'auto', 'description': 'Public UCI benchmark verification. Source: ' + dataset['page']},
                    files={'file': (Path(dataset['csv']).name, frame.to_csv(index=False).encode(), 'text/csv')})
                response.raise_for_status()
                project_id = response.json()['project']['id']
                path = '/projects/' + project_id
                details = client.get(path).json()
                assert details['project']['problem_type'] == dataset['task'], 'Automatic task detection incorrect'
                assert details['project']['eda_profile_json']['rows_count'] == len(frame)
                assert details['project']['eda_profile_json']['distributions']
                assert details['project']['eda_profile_json']['correlations']['values']
                for method in ['Median', 'Mean', 'Mode', 'KNN']:
                    response = client.get(path + '/download-dataset', params={'imputation_method': method})
                    response.raise_for_status()
                    cleaned = pd.read_csv(io.BytesIO(response.content))
                    assert not cleaned.drop(columns=dataset['target']).isna().any().any()
                    assert cleaned[dataset['target']].equals(frame[dataset['target']]) or np.allclose(cleaned[dataset['target']], frame[dataset['target']])
                response = client.post(path + '/train', params={'imputation_method': 'KNN'})
                response.raise_for_status()
                print('Training:', dataset['name'], flush=True)
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    jobs = client.get(path + '/jobs').json()['jobs']
                    if jobs and jobs[0]['status'] in ['completed', 'failed']: break
                    time.sleep(1)
                assert jobs[0]['status'] == 'completed', jobs[0].get('metrics_json')
                assert len(jobs[0]['metrics_json']['hpo_trials']) == 20
                card = client.get(path).json()['knowledge_card']
                models = card['models_comparison_json']
                assert len(models) == 4 and all(m['status'] == 'Trained' for m in models.values()), models
                baseline_card = card
                engineering_feature = {'iris': 'sepal_length', 'banknote': 'entropy', 'auto-mpg': 'horsepower'}[dataset['slug']]
                transformation = 'Standard Scaling' if dataset['slug'] == 'auto-mpg' else 'Discretize Binning'
                response = client.post(path + '/transform', json={'feature_name': engineering_feature, 'transformation': transformation})
                response.raise_for_status()
                transformed = client.get(path + '/download-transformed')
                transformed.raise_for_status()
                engineered = pd.read_csv(io.BytesIO(transformed.content))
                assert len(engineered) == len(frame) and not engineered.isna().any().any()
                response = client.post(path + '/train', params={'imputation_method': 'KNN'})
                response.raise_for_status()
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    jobs = client.get(path + '/jobs').json()['jobs']
                    if jobs and jobs[0]['status'] in ['completed', 'failed']: break
                    time.sleep(1)
                assert jobs[0]['status'] == 'completed', jobs[0].get('metrics_json')
                card = client.get(path).json()['knowledge_card']
                models = card['models_comparison_json']
                assert len(jobs[0]['metrics_json']['hpo_trials']) == 20
                assert all(m['hpo_trials'] == 5 and m['best_params'] for m in models.values())
                print('Feature engineered and re-optimized:', dataset['slug'], engineering_feature, transformation, flush=True)
                sample = frame.drop(columns=dataset['target']).head(5)
                rows = json.loads(sample.to_json(orient='records'))
                for name, model in models.items():
                    response = client.get(path + '/download-model', params={'model_name': name})
                    response.raise_for_status()
                    pipeline = pickle.loads(response.content)
                    assert len(pipeline.predict(sample)) == 5
                    (folder / f"{dataset['slug']}-{name.replace(' ', '_')}.pkl").write_bytes(response.content)
                response = client.post(path + '/predict', json={'rows': rows})
                response.raise_for_status()
                predictions = response.json()
                assert len(predictions['predictions']) == 5
                if dataset['task'] == 'classification':
                    assert len(predictions['classes']) == frame[dataset['target']].nunique()
                    assert all(abs(sum(p)-1) < 1e-5 for p in predictions['probabilities'])
                else:
                    assert np.isfinite(predictions['predictions']).all()
                response = client.get(path + '/explain/0')
                response.raise_for_status()
                assert response.json()['drivers']
                response = client.post(path + '/monitor', files={'file': ('baseline.csv', frame.to_csv(index=False).encode(), 'text/csv')})
                response.raise_for_status()
                assert response.json()['driftPsi'] == 0
                shifted = frame.copy()
                predictor = next(c for c in frame.select_dtypes(include=np.number).columns if c != dataset['target'])
                shifted[predictor] += max(float(frame[predictor].std()), 1) * 20
                response = client.post(path + '/monitor', files={'file': ('shifted.csv', shifted.to_csv(index=False).encode(), 'text/csv')})
                response.raise_for_status()
                assert response.json()['driftPsi'] > .2
                original_champion = card['best_model']
                response = client.post(path + '/champion', json={'model_name': 'Random Forest'})
                response.raise_for_status()
                response = client.post(path + '/predict', json={'rows': rows})
                response.raise_for_status()
                assert len(response.json()['predictions']) == 5
                response = client.post(path + '/champion', json={'model_name': original_champion})
                response.raise_for_status()
                metric = card['best_mse'] if dataset['task'] == 'regression' else card['best_f1']
                result = {**dataset, 'project_id': project_id, 'champion': original_champion,
                          'baseline_test_metric': baseline_card['best_mse'] if dataset['task'] == 'regression' else baseline_card['best_f1'],
                          'engineering': {'feature': engineering_feature, 'transformation': transformation},
                          'hpo_trials': 20, 'test_metric': metric, 'test_accuracy': card.get('best_accuracy'),
                          'models': models, 'checks': ['upload', 'automatic task detection', 'profile', 'four imputation exports',
                          'EDA distributions/correlations', 'feature transformation/export', 'baseline and engineered optimized training', 'five HPO trials per model', 'four executable model exports', 'predictions',
                          'row explanation', 'baseline drift', 'shifted drift', 'champion switching'], 'status': 'passed'}
                results.append(result)
                (folder / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
                print(f"PASS {dataset['slug']}: champion={original_champion}, test metric={metric:.4f}", flush=True)
        finally:
            client.post('/auth/logout', json={'refresh_token': token})
    print('All three public dataset workflows passed.', flush=True)


if __name__ == '__main__': main()
