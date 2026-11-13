import io
import json
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Project, KnowledgeCard, User, TimelineEvent
from services.security import get_current_user, validate_csv_content
from services.sandbox import run_operation
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
    reason: str | None = Field(default=None, max_length=1000)

@router.post('/{project_id}/champion')
def select_champion(project_id: str, payload: ChampionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if project.status == 'Training': raise HTTPException(status_code=409, detail='Wait for training to finish')
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    candidate = (card.models_comparison_json or {}).get(payload.model_name) if card else None
    if not candidate or candidate.get('status') != 'Trained': raise HTTPException(status_code=400, detail='Choose a successfully trained model')
    storage = get_storage_provider()
    info = run_operation('champion', {'target': project.target_variable, 'problem_type': project.problem_type}, {'model.pkl': storage.download_file(candidate['artifact_path']), 'dataset.csv': storage.download_file(project.dataset_path)})
    card.best_model = payload.model_name
    card.model_path = candidate['artifact_path']
    card.best_f1 = candidate['metric'] if project.problem_type == 'classification' else None
    card.best_mse = candidate['metric'] if project.problem_type == 'regression' else None
    card.best_accuracy = candidate.get('accuracy')
    card.shap_global_json = info['shap_global']
    card.top_features = info['top_features']
    card.shap_local_json = None
    project.updated_at = datetime.utcnow()
    db.add(TimelineEvent(project_id=project_id, title='Champion Model Selected', description=f'User selected {payload.model_name} as the inference model. Reason: {payload.reason or "No reason supplied by the user; this is a manual override."}', event_type='success'))
    db.commit()
    return {'status': 'success', 'champion': payload.model_name}

@router.post('/{project_id}/predict')
def predict(project_id: str, payload: PredictionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    if not card or not card.model_path: raise HTTPException(status_code=409, detail='Train a model first')
    if not 1 <= len(payload.rows) <= 1000: raise HTTPException(status_code=400, detail='Provide between 1 and 1000 rows')
    storage = get_storage_provider()
    try:
        return run_operation('predict', {'rows': payload.rows, 'target': project.target_variable, 'problem_type': project.problem_type}, {'model.pkl': storage.download_file(card.model_path)})
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.get('/{project_id}/explain/{row_index}')
def explain(project_id: str, row_index: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    if not card or not card.model_path: raise HTTPException(status_code=409, detail='Train a model first')
    storage = get_storage_provider()
    try:
        return run_operation('explain', {'row_index': row_index, 'target': project.target_variable, 'problem_type': project.problem_type}, {'model.pkl': storage.download_file(card.model_path), 'dataset.csv': storage.download_file(project.dataset_path)})
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.post('/{project_id}/monitor')
async def monitor(project_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    data = await file.read(50 * 1024 * 1024 + 1)
    if len(data) > 50 * 1024 * 1024: raise HTTPException(status_code=400, detail='Maximum dataset size is 50MB')
    try:
        await run_in_threadpool(validate_csv_content, data)
    except ValueError as error: raise HTTPException(status_code=400, detail=str(error))
    storage = get_storage_provider()
    try:
        result = await run_in_threadpool(run_operation, 'monitor', {'target': project.target_variable}, {'dataset.csv': storage.download_file(project.dataset_path), 'current.csv': data})
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    maximum = result['driftPsi']
    observations = result['rows']
    storage.upload_report(f'{project_id}_monitoring.json', json.dumps(result).encode())
    db.add(TimelineEvent(project_id=project_id, title='Monitoring Dataset Compared', description=f"Compared {observations} rows with baseline; maximum PSI: {maximum:.4f}", event_type='warning' if maximum > .2 else 'success'))
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
