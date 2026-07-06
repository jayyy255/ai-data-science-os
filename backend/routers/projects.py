from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import Project, DecisionMemory, TimelineEvent, KnowledgeCard
from services.dataset import DatasetService
from services.gemini import GeminiService
from services.storage.factory import get_storage_provider
from services.cache import RedisCacheService

router = APIRouter(prefix="/api/projects", tags=["projects"])

gemini = GeminiService()
storage = get_storage_provider()
cache = RedisCacheService()

class DecisionOverride(BaseModel):
    feature_name: str
    user_choice: str

@router.post("")
async def create_project(
    name: str = Form(...),
    target_variable: str = Form(...),
    description: str = Form(...),
    username: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    file_bytes = await file.read()
    
    # Enforce file size limit
    MAX_FILE_SIZE = 100 * 1024 * 1024 # 100 MB
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File exceeds maximum allowed size of 100MB (actual: {len(file_bytes) / (1024*1024):.1f}MB)"
        )

    # Dataset Intelligence Service
    profile = DatasetService.profile_dataset(file_bytes, target_variable)
    
    # Enforce rows and columns limit
    if profile.get("rows_count", 0) > 200000:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset rows exceed maximum allowed limit of 200,000 (actual: {profile['rows_count']})"
        )
    if profile.get("columns_count", 0) > 200:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset columns exceed maximum allowed limit of 200 (actual: {profile['columns_count']})"
        )

    s3_path = storage.upload_dataset(file.filename, file_bytes)
    
    # Gemini AI Project Understanding Agent
    understanding = gemini.understand_project(name, description, target_variable)
    
    project_id = name.lower().replace(" ", "-")
    db_project = Project(
        id=project_id,
        name=name,
        target_variable=target_variable,
        problem_type=understanding.get("problem_type", "classification"),
        description=description,
        status="EDA Phase",
        dataset_path=s3_path,
        username=username
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
        models_comparison_json={
            'XGBoost': { 'status': 'Idle', 'metric': None },
            'LightGBM': { 'status': 'Idle', 'metric': None },
            'Random Forest': { 'status': 'Idle', 'metric': None },
            'Neural Network': { 'status': 'Idle', 'metric': None },
            'Tabular Transformer': { 'status': 'Idle', 'metric': None }
        },
        status="EDA Phase"
    )
    db.add(db_card)

    # Initialize Feature Engineering Decisions
    for feat in profile["features"]:
        feat_name = feat["name"]
        if feat_name == target_variable:
            continue
        
        missing_pct = feat["missing"]
        feat_type = feat["type"]
        unique_val = feat["unique"]
        
        if missing_pct > 0:
            rec_decision = "Impute Median"
            rec_reason = f"Feature '{feat_name}' has {missing_pct}% missing values. Imputation is required to preserve data matrix integrity."
            confidence = 0.95
        elif "int" in feat_type or "float" in feat_type:
            rec_decision = "Standard Scaling"
            rec_reason = f"Standard scaling normalization is recommended for numeric variable of type {feat_type} to speed up optimizer convergence."
            confidence = 0.90
        else:
            rec_decision = "One-Hot Encoding"
            rec_reason = f"Encode categorical feature '{feat_name}' with {unique_val} unique labels to feed numerical representation to estimators."
            confidence = 0.88
            
        db_decision = DecisionMemory(
            project_id=project_id,
            feature_name=feat_name,
            decision=rec_decision,
            reason=rec_reason,
            confidence=confidence,
            override_active=False,
            user_choice=None
        )
        db.add(db_decision)
        
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
def list_projects(username: str = None, db: Session = Depends(get_db)):
    query = db.query(Project)
    if username:
        query = query.filter(Project.username == username)
    else:
        query = query.filter(Project.username == None)
    return query.all()

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

@router.get("/{project_id}/download-model")
def download_model(project_id: str, model_name: str = None, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    if not project or not card or not card.model_path:
        raise HTTPException(status_code=404, detail="Model binary not found for this project")
        
    try:
        path = card.model_path
        if model_name:
            m_slug = model_name.lower().replace(" ", "_")
            if path.startswith("s3://"):
                path = f"s3://aidso-runs/models/{project_id}/{m_slug}.pkl"
            elif path.startswith("file://"):
                import re
                folder = re.sub(r'/[^/]+\.pkl$', '', path)
                path = f"{folder}/{project_id}_{m_slug}.pkl"
                
        model_bytes = storage.download_file(path)
        
        # Parse dataset name from project.dataset_path
        import os
        import re
        dataset_name = "dataset"
        if project.dataset_path:
            dataset_name = os.path.basename(project.dataset_path).replace(".csv", "")
        
        # Format filename: {project_name}_{dataset_name}_{model_name}.pkl
        proj_slug = re.sub(r'\s+', '_', project.name)
        m_name_slug = re.sub(r'\s+', '_', model_name or card.best_model or "champion")
        filename = f"{proj_slug}_{dataset_name}_{m_name_slug}.pkl"
        
        # Safe characters for HTTP header
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
        
        return StreamingResponse(
            io.BytesIO(model_bytes),
            media_type="application/octet-stream",
            headers={"content-disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model binary: {e}")


def apply_imputation(df, method: str):
    import numpy as np
    import pandas as pd
    df_copy = df.copy()
    for col in df_copy.columns:
        if df_copy[col].isnull().sum() > 0:
            if df_copy[col].dtype in ['int64', 'float64', 'float32', 'int32']:
                if method == 'Mean':
                    df_copy[col] = df_copy[col].fillna(df_copy[col].mean())
                elif method == 'Mode':
                    df_copy[col] = df_copy[col].fillna(df_copy[col].mode().iloc[0] if not df_copy[col].mode().empty else 0)
                elif method == 'KNN':
                    df_copy[col] = df_copy[col].interpolate().fillna(df_copy[col].mean())
                else: # Median (Default)
                    df_copy[col] = df_copy[col].fillna(df_copy[col].median())
            else:
                df_copy[col] = df_copy[col].fillna(df_copy[col].mode().iloc[0] if not df_copy[col].mode().empty else "Missing")
    return df_copy


@router.get("/{project_id}/download-dataset")
def download_dataset(project_id: str, imputation_method: str = "Median", db: Session = Depends(get_db)):
    import pandas as pd
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.dataset_path:
        raise HTTPException(status_code=404, detail="Dataset not found for this project")
        
    try:
        # Load raw dataset from S3/MinIO
        file_bytes = storage.download_file(project.dataset_path)
        df = pd.read_csv(io.BytesIO(file_bytes))
        
        # Apply imputation method
        modified_df = apply_imputation(df, imputation_method)
        
        # Export to CSV bytes
        out_buf = io.StringIO()
        modified_df.to_csv(out_buf, index=False)
        csv_bytes = out_buf.getvalue().encode("utf-8")
        
        filename = f"{project_id}_imputed_{imputation_method.lower()}.csv"
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and download dataset: {e}")

