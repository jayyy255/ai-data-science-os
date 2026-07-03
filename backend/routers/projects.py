from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import Project, DecisionMemory, TimelineEvent, KnowledgeCard
from services.dataset import DatasetService
from services.gemini import GeminiService
from services.minio_client import MinIOClient
from services.cache import RedisCacheService

router = APIRouter(prefix="/api/projects", tags=["projects"])

gemini = GeminiService()
minio = MinIOClient()
cache = RedisCacheService()

class DecisionOverride(BaseModel):
    feature_name: str
    user_choice: str

@router.post("")
async def create_project(
    name: str = Form(...),
    target_variable: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_bytes = await file.read()
    s3_path = minio.upload_dataset(file.filename, file_bytes)
    
    # Dataset Intelligence Service
    profile = DatasetService.profile_dataset(file_bytes, target_variable)
    
    # Gemini AI Project Understanding Agent
    understanding = gemini.understand_project(name, description, target_variable)
    
    project_id = name.lower().replace(" ", "-")
    db_project = Project(
        id=project_id,
        name=name,
        target_variable=target_variable,
        problem_type=understanding.get("problem_type", "classification"),
        description=description,
        status="EDA Phase"
    )
    db.add(db_project)
    
    # Log Timeline events
    db.add(TimelineEvent(
        project_id=project_id,
        title="Dataset Uploaded",
        description=f"Raw dataset file {file.filename} uploaded successfully to local S3 bucket: {s3_path}",
        event_type="success"
    ))
    
    db.add(TimelineEvent(
        project_id=project_id,
        title="Project Understood",
        description=f"Gemini classified task as {understanding.get('problem_type')} targeting '{target_variable}'. Suggested metrics: {', '.join(understanding.get('recommended_metrics', []))}",
        event_type="info"
    ))

    # Initialize Knowledge Card
    db_card = KnowledgeCard(
        project_id=project_id,
        best_model="None",
        rows_count=profile["rows_count"],
        columns_count=profile["columns_count"],
        missing_values_pct=profile["missing_pct"],
        balancing_method="SMOTE" if profile["is_imbalanced"] != "None" else "None",
        models_tested_count=0,
        numerical_count=profile["numerical_count"],
        categorical_count=profile["categorical_count"],
        quality_health_json=profile["quality_health"],
        status="EDA Phase"
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_project)
    
    # Cache EDA profile in Redis Cache
    cache.set_cached_eda(project_id, profile)
    
    return {
        "project": db_project,
        "s3_path": s3_path,
        "understanding": understanding
    }

@router.get("")
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Fetch cached EDA profile from Redis
    cached_eda = cache.get_cached_eda(project_id)
    
    decisions = db.query(DecisionMemory).filter(DecisionMemory.project_id == project_id).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.project_id == project_id).order_by(TimelineEvent.timestamp.desc()).all()
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    
    return {
        "project": project,
        "decisions": decisions,
        "timeline": timeline,
        "knowledge_card": card,
        "cached_eda": cached_eda
    }

@router.post("/{project_id}/override")
def apply_override(project_id: str, payload: DecisionOverride, db: Session = Depends(get_db)):
    dec = db.query(DecisionMemory).filter(
        DecisionMemory.project_id == project_id, 
        DecisionMemory.feature_name == payload.feature_name
    ).first()
    
    if not dec:
        dec = DecisionMemory(
            project_id=project_id,
            feature_name=payload.feature_name,
            decision="User Choice Applied",
            reason="User Override Action",
            confidence=1.0
        )
        db.add(dec)

    dec.override_active = True
    dec.user_choice = payload.user_choice
    
    db.add(TimelineEvent(
        project_id=project_id,
        title="User Override Applied",
        description=f"Feature '{payload.feature_name}' transformation overridden to: {payload.user_choice}",
        event_type="warning"
    ))
    db.commit()
    return {"status": "success", "decision": dec}
