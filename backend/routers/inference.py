import io
import json
import pickle
from datetime import datetime
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Project, KnowledgeCard, User, TimelineEvent
from services.security import get_current_user, validate_csv_content
from services.preprocessing import clean_frame
from services.storage.factory import get_storage_provider

router = APIRouter(prefix='/api/projects', tags=['inference'])

def owned_project(project_id, user, db):
    project = db.query(Project).filter_by(id=project_id, username=user.username).first()
    if not project: raise HTTPException(status_code=404, detail='Project not found')
    return project

class PredictionRequest(BaseModel):
    rows: list[dict]

class ChampionRequest(BaseModel):
    model_name: str

@router.post('/{project_id}/champion')
def select_champion(project_id: str, payload: ChampionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if project.status == 'Training': raise HTTPException(status_code=409, detail='Wait for training to finish')
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    candidate = (card.models_comparison_json or {}).get(payload.model_name) if card else None
    if not candidate or candidate.get('status') != 'Trained': raise HTTPException(status_code=400, detail='Choose a successfully trained model')
    storage = get_storage_provider()
    model = pickle.loads(storage.download_file(candidate['artifact_path']))
    preprocessor = model.named_steps['preprocess']
    wrapped = model.named_steps['model']
    estimator = wrapped.estimator if project.problem_type == 'classification' else wrapped
    names = preprocessor.get_feature_names_out()
    card.best_model = payload.model_name
    card.model_path = candidate['artifact_path']
    card.best_f1 = candidate['metric'] if project.problem_type == 'classification' else None
    card.best_mse = candidate['metric'] if project.problem_type == 'regression' else None
    card.best_accuracy = candidate.get('accuracy')
    importance = getattr(estimator, 'feature_importances_', None)
    method = 'Native feature importance'
    if importance is None:
        from sklearn.inspection import permutation_importance
        frame = clean_frame(pd.read_csv(io.BytesIO(storage.download_file(project.dataset_path)))).dropna(subset=[project.target_variable]).head(30)
        features = preprocessor.transform(frame.drop(columns=[project.target_variable]))
        target = wrapped.encoder_.transform(frame[project.target_variable]) if project.problem_type == 'classification' else frame[project.target_variable]
        importance = np.maximum(permutation_importance(estimator, features, target, n_repeats=2, random_state=42).importances_mean, 0)
        method = 'Permutation importance'
    card.shap_global_json = sorted([{'feature': name, 'shap': float(value), 'type': method} for name, value in zip(names, importance)], key=lambda item: item['shap'], reverse=True)
    card.top_features = [item['feature'] for item in card.shap_global_json[:8]]
    card.shap_local_json = None
    project.updated_at = datetime.utcnow()
    db.add(TimelineEvent(project_id=project_id, title='Champion Model Selected', description=f'User selected {payload.model_name} as the inference model', event_type='success'))
    db.commit()
    return {'status': 'success', 'champion': payload.model_name}

@router.post('/{project_id}/predict')
def predict(project_id: str, payload: PredictionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    if not card or not card.model_path: raise HTTPException(status_code=409, detail='Train a model first')
    if not 1 <= len(payload.rows) <= 1000: raise HTTPException(status_code=400, detail='Provide between 1 and 1000 rows')
    storage = get_storage_provider()
    model = pickle.loads(storage.download_file(card.model_path))
    required = model.named_steps['preprocess'].feature_names_in_.tolist()
    frame = pd.DataFrame(payload.rows)
    missing = set(required) - set(frame.columns)
    if missing: raise HTTPException(status_code=400, detail='Missing columns: ' + ', '.join(sorted(missing)))
    try:
        frame = clean_frame(frame[required])
        predictions = model.predict(frame).tolist()
        result = {'predictions': predictions, 'target': project.target_variable}
        if project.problem_type == 'classification':
            result['probabilities'] = model.predict_proba(frame).tolist()
            result['classes'] = model.named_steps['model'].classes_.tolist()
        return result
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.get('/{project_id}/explain/{row_index}')
def explain(project_id: str, row_index: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    if not card or not card.model_path: raise HTTPException(status_code=409, detail='Train a model first')
    storage = get_storage_provider()
    frame = clean_frame(pd.read_csv(io.BytesIO(storage.download_file(project.dataset_path))))
    if row_index < 0 or row_index >= len(frame): raise HTTPException(status_code=400, detail='Row index is outside the dataset')
    model = pickle.loads(storage.download_file(card.model_path))
    row = frame.drop(columns=[project.target_variable]).iloc[[row_index]]
    preprocessing = model.named_steps['preprocess']
    values = preprocessing.transform(row)
    names = preprocessing.get_feature_names_out().tolist()
    classification = project.problem_type == 'classification'
    wrapped = model.named_steps['model']
    estimator = wrapped.estimator if classification else wrapped
    prediction = model.predict(row)[0]
    drivers = []
    method = 'Local SHAP unavailable for this model'
    try:
        import shap
        explanation = shap.TreeExplainer(estimator).shap_values(values)
        class_index = int(wrapped.encoder_.transform([prediction])[0]) if classification else 0
        if isinstance(explanation, list): explanation = explanation[class_index]
        explanation = np.asarray(explanation)
        if explanation.ndim == 3: explanation = explanation[:, :, class_index]
        for index in np.argsort(np.abs(explanation[0]))[::-1][:8]:
            drivers.append({'feature': names[index], 'value': str(round(float(values[0,index]), 4)), 'impact': f'{float(explanation[0,index]):+.4f} SHAP'})
        method = 'SHAP'
    except Exception:
        pass
    return {'customerId': str(row_index), 'prediction': str(prediction), 'probability': float(model.predict_proba(row)[0].max()) if classification else None, 'risk': f'Predicted class: {prediction}' if classification else f'Predicted value: {float(prediction):.4f}', 'drivers': drivers, 'explanation_method': method}

@router.post('/{project_id}/monitor')
async def monitor(project_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    data = await file.read(50 * 1024 * 1024 + 1)
    if len(data) > 50 * 1024 * 1024: raise HTTPException(status_code=400, detail='Maximum dataset size is 50MB')
    try:
        validate_csv_content(data)
        current = clean_frame(pd.read_csv(io.BytesIO(data)))
    except ValueError as error: raise HTTPException(status_code=400, detail=str(error))
    storage = get_storage_provider()
    baseline = clean_frame(pd.read_csv(io.BytesIO(storage.download_file(project.dataset_path))))
    columns = baseline.columns.drop(project.target_variable)
    if current.empty or len(current) > 100000: raise HTTPException(status_code=400, detail='Provide between 1 and 100000 rows')
    if not set(columns).issubset(current.columns): raise HTTPException(status_code=400, detail='Monitoring data must contain all predictor columns')
    features = []
    for column in columns:
        before, after = baseline[column], current[column]
        if pd.api.types.is_numeric_dtype(before):
            edges = np.unique(np.quantile(before.dropna(), np.linspace(0, 1, 11))) if before.notna().any() else np.array([0])
            edges = np.concatenate(([-np.inf], edges[1:-1], [np.inf]))
            expected = np.append(np.histogram(before.dropna(), edges)[0], before.isna().sum()) / len(before)
            actual = np.append(np.histogram(pd.to_numeric(after, errors='coerce').dropna(), edges)[0], after.isna().sum()) / len(after)
        else:
            labels = list(set(before.fillna('__missing__')) | set(after.fillna('__missing__')))
            expected = before.fillna('__missing__').value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy()
            actual = after.fillna('__missing__').value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy()
        expected, actual = np.clip(expected, .0001, 1), np.clip(actual, .0001, 1)
        psi = float(np.sum((actual-expected)*np.log(actual/expected)))
        features.append({'feature': column, 'psi': round(psi, 4)})
    maximum = max((item['psi'] for item in features), default=0)
    result = {'driftPsi': maximum, 'driftStatus': 'DRIFT DETECTED' if maximum > .2 else 'HEALTHY', 'features': features, 'rows': len(current), 'driftAlerts': [{'feature': item['feature'], 'message': f"PSI {item['psi']:.4f} exceeds 0.20", 'severity': 'warning'} for item in features if item['psi'] > .2]}
    storage.upload_report(f'{project_id}_monitoring.json', json.dumps(result).encode())
    db.add(TimelineEvent(project_id=project_id, title='Monitoring Dataset Compared', description=f"Compared {len(current)} rows with baseline; maximum PSI: {maximum:.4f}", event_type='warning' if maximum > .2 else 'success'))
    db.commit()
    return result

@router.get('/{project_id}/monitor')
def monitoring_result(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    storage = get_storage_provider()
    path = f"s3://{storage.bucket_name}/reports/{project_id}_monitoring.json" if getattr(storage, 'client_enabled', True) else 'file://' + __import__('os').path.abspath(__import__('os').path.join(storage.local_fallback_dir, f'{project_id}_monitoring.json'))
    try: return json.loads(storage.download_file(path))
    except FileNotFoundError: return None
    except Exception as error:
        if getattr(error, 'response', {}).get('Error', {}).get('Code') in {'NoSuchKey', '404'}: return None
        raise HTTPException(status_code=503, detail='Monitoring storage is temporarily unavailable')
