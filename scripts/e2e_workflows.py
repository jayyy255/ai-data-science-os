"""Real-process E2E checks. Run: python scripts/e2e_workflows.py.

Creates disposable SQLite/artifact storage, starts HTTP API and worker processes,
and writes results to tmp/e2e-results.json. Never uses the development database.
"""
import io
import json
import os
import pickle
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))  # Downloaded pipelines reference their estimator class.
import httpx
import numpy as np
import pandas as pd


def main():
    results = []
    processes = []
    logs = []
    output = ROOT / 'tmp'
    output.mkdir(exist_ok=True)
    started = time.monotonic()
    succeeded = False
    with tempfile.TemporaryDirectory(prefix='aidso-e2e-', dir=output) as scratch:
        scratch = Path(scratch)
        env = os.environ.copy()
        env.update(DATABASE_URL='sqlite:///' + (scratch / 'database.db').as_posix(),
                   LOCAL_STORAGE_DIR=str(scratch / 'artifacts'), ENVIRONMENT='local', AIDSO_LOAD_ENV_FILE='0')
        for name in ['MINIO_ENDPOINT', 'REDIS_URL', 'GEMINI_API_KEY', 'DATABASE_URI']:
            env.pop(name, None)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}/api'

        def launch(name, args):
            log = open(scratch / f'{name}.log', 'w', encoding='utf-8')
            logs.append(log)
            process = subprocess.Popen([sys.executable, '-u', *args], cwd=BACKEND,
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
            processes.append(process)
            return process

        def check(condition, label):
            if not condition:
                raise AssertionError(label)
            results.append(label)
            print('PASS:', label, flush=True)

        def request(client, method, path, expected=200, **kwargs):
            response = client.request(method, base + path, **kwargs)
            if response.status_code != expected:
                raise AssertionError(f'{method} {path}: expected {expected}, got {response.status_code}: {response.text[:600]}')
            return response

        def create(client, frame, name, task='auto', expected=200):
            response = request(client, 'POST', '/projects', expected,
                               data={'name': name, 'target_variable': 'target', 'description': 'E2E fixture', 'problem_type': task},
                               files={'file': ('fixture.csv', frame.to_csv(index=False).encode(), 'text/csv')})
            return response.json()['project']['id'] if expected == 200 else response

        def await_job(client, project_id, status='completed'):
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                jobs = request(client, 'GET', f'/projects/{project_id}/jobs').json()['jobs']
                if jobs and jobs[0]['status'] in {'completed', 'failed'}:
                    check(jobs[0]['status'] == status, f'{project_id}: worker job {status}')
                    return jobs[0]
                time.sleep(.5)
            raise AssertionError(f'Worker timed out for {project_id}')

        try:
            api = launch('api', ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)])
            with httpx.Client(timeout=30) as owner, httpx.Client(timeout=30) as other:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if api.poll() is not None:
                        raise AssertionError('API exited during startup')
                    try:
                        if owner.get(base + '/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.25)
                check(owner.get(base + '/health').json()['status'] == 'ok', 'API starts with isolated storage')
                launch('worker', ['worker/worker.py'])
                password = 'e2e-password-123'
                for client, username in [(owner, 'e2e_owner'), (other, 'e2e_other')]:
                    response = request(client, 'POST', '/auth/signup', json={
                        'full_name': 'E2E Test', 'username': username,
                        'email': username + '@example.test', 'password': password})
                    check(bool(response.json()['refreshToken']), f'{username}: signup establishes a session')
                request(owner, 'POST', '/auth/signup', 400, json={
                    'full_name': 'E2E', 'username': 'e2e_owner', 'email': 'duplicate@example.test', 'password': password})
                request(owner, 'POST', '/auth/login', 401, json={'identity': 'e2e_owner', 'password': 'wrong'})
                check(request(owner, 'GET', '/auth/me').json()['user']['username'] == 'e2e_owner', 'Rejected login preserves existing session')
                request(owner, 'POST', '/auth/forgot-password', 503, json={'email': 'e2e_owner@example.test'})
                check(True, 'Unconfigured password recovery cannot reset credentials')

                rng = np.random.default_rng(2026)
                size = 150
                spend = rng.normal(80, 20, size)
                age = rng.integers(18, 70, size).astype(float)
                labels = np.where(spend > 90, 'high', np.where(age > 45, 'medium', 'low'))
                age[::17] = np.nan
                baseline = pd.DataFrame({'age': age, 'spend': spend,
                    'segment': rng.choice(['basic', 'premium'], size),
                    'recorded_at': pd.date_range('2026-01-01', periods=size).astype(str),
                    'notes': 'A detailed free text observation containing several words describing a synthetic data record.', 'empty': np.nan, 'target': labels})
                create(owner, baseline, 'Invalid target type', task='regression', expected=400)
                for task in ['classification', 'regression']:
                    frame = baseline.copy()
                    if task == 'regression':
                        frame['target'] = spend * 2.3 + np.arange(size) * .01
                    project_id = create(owner, frame, 'E2E ' + task, task)
                    path = f'/projects/{project_id}'
                    details = request(owner, 'GET', path).json()
                    check(details['project']['problem_type'] == task, f'{task}: explicit task and profile persisted')
                    profile = details['project']['eda_profile_json']
                    check(profile['datetime_count'] == 1 and profile['text_count'] == 1, f'{task}: date and text columns counted from actual data')
                    request(owner, 'POST', path + '/predict', 409, json={'rows': [{'age': 25}]})
                    request(other, 'GET', path, 404)
                    request(owner, 'POST', path + '/transform', 400, json={'feature_name': 'target', 'transformation': 'Keep Raw'})
                    for choice in ['One-Hot Encoding', 'Keep Raw', 'recommended']:
                        request(owner, 'POST', path + '/transform', json={'feature_name': 'segment', 'transformation': choice})
                        preview = pd.read_csv(io.BytesIO(request(owner, 'GET', path + '/download-transformed').content))
                        check(('segment' in preview) == (choice == 'Keep Raw'), f'{task}: transform {choice} changes exported columns')
                    for method in ['Median', 'Mean', 'Mode', 'KNN']:
                        cleaned = pd.read_csv(io.BytesIO(request(owner, 'GET', path + '/download-dataset', params={'imputation_method': method}).content))
                        check(not cleaned.drop(columns='target').isna().any().any(), f'{task}: {method} export fills predictor missing values')
                        check(np.allclose(cleaned['target'], frame['target'], rtol=1e-12, atol=1e-12) if task == 'regression' else cleaned['target'].tolist() == frame['target'].tolist(), f'{task}: {method} export preserves target')
                    request(owner, 'POST', path + '/train', params={'imputation_method': 'KNN'})
                    request(owner, 'POST', path + '/train')
                    check(len(request(owner, 'GET', path + '/jobs').json()['jobs']) == 1, f'{task}: duplicate training request does not duplicate jobs')
                    request(owner, 'POST', path + '/transform', 409, json={'feature_name': 'age', 'transformation': 'Keep Raw'})
                    job = await_job(owner, project_id)
                    check(len(job['metrics_json']['hpo_trials']) == 20, f'{task}: worker persists five HPO trials per model')
                    details = request(owner, 'GET', path).json()
                    card = details['knowledge_card']
                    check(details['project']['status'] == 'Ready for Deployment', f'{task}: project finishes training')
                    models = card['models_comparison_json']
                    check(len(models) == 4, f'{task}: all four installed candidate models present')
                    sample = frame.drop(columns='target').head(3).copy()
                    sample['segment'] = 'previously-unseen'
                    rows = json.loads(sample.to_json(orient='records'))
                    for name, model in models.items():
                        check(model['status'] == 'Trained', f'{task}: {name} trains successfully')
                        data = request(owner, 'GET', path + '/download-model', params={'model_name': name}).content
                        pipeline = pickle.loads(data)
                        check(len(pipeline.predict(sample)) == 3, f'{task}: downloaded {name} accepts raw rows and unknown categories')
                        signed = request(owner, 'GET', path + '/presigned-download-model', params={'model_name': name}).json()['url']
                        check(owner.get(f'http://127.0.0.1:{port}' + signed).content == data, f'{task}: signed {name} download returns same artifact')
                    prediction = request(owner, 'POST', path + '/predict', json={'rows': rows}).json()
                    check(len(prediction['predictions']) == 3, f'{task}: inference uses saved pipeline')
                    if task == 'classification':
                        check(len(prediction['classes']) == 3 and all(abs(sum(p)-1) < 1e-5 for p in prediction['probabilities']), 'Multiclass probabilities align with class labels')
                    request(owner, 'POST', path + '/predict', 400, json={'rows': [{'age': 25}]})
                    request(owner, 'POST', path + '/predict', 400, json={'rows': []})
                    explanation = request(owner, 'GET', path + '/explain/0').json()
                    check(bool(explanation['drivers']), f'{task}: row explanation contains actual drivers')
                    request(owner, 'GET', path + '/explain/9999', 400)
                    request(owner, 'POST', path + '/champion', 400, json={'model_name': 'Missing model'})
                    request(owner, 'POST', path + '/champion', json={'model_name': 'Neural Network'})
                    check(request(owner, 'GET', path).json()['knowledge_card']['best_model'] == 'Neural Network', f'{task}: champion selection persists')
                    request(owner, 'POST', path + '/predict', json={'rows': rows})
                    request(owner, 'POST', path + '/champion', json={'model_name': 'Random Forest'})
                    request(other, 'GET', path + '/download-model', 404)
                    request(other, 'POST', path + '/predict', 404, json={'rows': rows})
                    request(other, 'POST', path + '/train', 404)
                    request(other, 'POST', path + '/chat', 404, json={'question': 'Context?'})
                    request(other, 'GET', path + '/monitor', 404)
                    check(True, f'{task}: all tested private workflow endpoints isolate accounts')
                    for shifted in [False, True]:
                        current = frame.copy()
                        if shifted: current['spend'] += 500
                        response = request(owner, 'POST', path + '/monitor', files={'file': ('monitor.csv', current.to_csv(index=False).encode(), 'text/csv')}).json()
                        check(response['driftPsi'] > .2 if shifted else response['driftPsi'] == 0, f'{task}: {"shifted" if shifted else "baseline"} drift calculated correctly')
                        check(request(owner, 'GET', path + '/monitor').json() == response, f'{task}: monitoring result persists')
                    answer = request(owner, 'POST', path + '/chat', json={'question': 'What model and transformations are used?'}).json()['answer']
                    check('local summary' in answer and 'Random Forest' in answer, f'{task}: assistant uses current project context without Gemini')
                    request(owner, 'POST', path + '/transform', json={'feature_name': 'spend', 'transformation': 'Keep Raw'})
                    check(not request(owner, 'GET', path).json()['knowledge_card']['model_path'], f'{task}: changing features invalidates stale inference model')
                    request(owner, 'POST', path + '/predict', 409, json={'rows': rows})
                    request(owner, 'POST', path + '/train')
                    await_job(owner, project_id)
                    request(owner, 'POST', path + '/predict', json={'rows': rows})
                    check(True, f'{task}: retraining restores usable inference after feature changes')

                failed_id = create(owner, baseline.head(4), 'Insufficient training data', 'classification')
                request(owner, 'POST', f'/projects/{failed_id}/train')
                failed = await_job(owner, failed_id, 'failed')
                check('12 rows' in failed['metrics_json']['error'], 'Worker failures expose actionable validation errors')
                check(request(owner, 'GET', '/projects').json(), 'Failed job does not prevent other project access')
                api.terminate(); api.wait(timeout=15)
                api = launch('api-restart', ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)])
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    try:
                        if owner.get(base + '/health').status_code == 200: break
                    except httpx.TransportError: pass
                    time.sleep(.25)
                check(len(request(owner, 'GET', '/projects').json()) == 3, 'Restart preserves account session and all project records')
                login = request(owner, 'POST', '/auth/login', json={'identity': 'e2e_owner', 'password': password}).json()
                token = login['refreshToken']
                request(owner, 'POST', '/auth/logout', json={'refresh_token': token})
                request(owner, 'GET', '/projects', 401)
                request(owner, 'GET', '/projects', 401, headers={'Authorization': 'Bearer ' + token})
                check(True, 'Logout revokes cookie and bearer access')
                succeeded = True
        except Exception:
            for name in ['api', 'api-restart', 'worker']:
                source = scratch / f'{name}.log'
                if source.exists(): (output / f'e2e-{name}.log').write_bytes(source.read_bytes())
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=15)
                    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=10)
            for log in logs: log.close()
            report = {'status': 'passed' if succeeded else 'failed', 'passed_checks': len(results), 'checks': results, 'seconds': round(time.monotonic()-started, 2)}
            (output / 'e2e-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Completed {len(results)} E2E checks.', flush=True)


if __name__ == '__main__':
    main()
