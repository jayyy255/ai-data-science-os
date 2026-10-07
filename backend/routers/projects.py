from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import io
import os
import re
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import Project, DecisionMemory, TimelineEvent, KnowledgeCard, User, TrainingJob
from services.dataset import DatasetService
from services.gemini import GeminiService
from services.storage.factory import get_storage_provider
from services.cache import RedisCacheService
from services.security import validate_csv_content, scan_file_for_virus, get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])

gemini = GeminiService()
storage = get_storage_provider()
cache = RedisCacheService()

class DecisionOverride(BaseModel):
    feature_name: str
    user_choice: str

class PresignedUrlRequest(BaseModel):
    filename: str

@router.post("/presigned-upload-url")
def get_presigned_upload_url(payload: PresignedUrlRequest, current_user: User = Depends(get_current_user)):
    try:
        res = storage.generate_presigned_upload_url(current_user.username + "_" + __import__("uuid").uuid4().hex + "_" + os.path.basename(payload.filename))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned upload URL: {e}")

@router.post("/upload-local")
async def upload_local_file(filename: str, file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if os.path.basename(filename) != filename or not filename.startswith(current_user.username + '_'):
        raise HTTPException(status_code=400, detail='Invalid upload name')
    try:
        content = await file.read(50 * 1024 * 1024 + 1)
        if len(content) > 50 * 1024 * 1024: raise HTTPException(status_code=400, detail='Maximum dataset size is 50MB')
        if not filename.lower().endswith('.csv'): raise HTTPException(status_code=400, detail='Only CSV files are allowed')
        try: validate_csv_content(content)
        except ValueError as error: raise HTTPException(status_code=400, detail=str(error))
        path = storage.upload_dataset(filename, content)
        return {"status": "success", "s3_path": path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload local file: {e}")

@router.get("/download-local-file")
def download_local_file(filename: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail='Invalid filename')
    owned = db.query(Project).filter(Project.username == current_user.username).all()
    if not any(filename == os.path.basename(p.dataset_path or '') or filename.startswith(p.id + '_') or filename.startswith('imputed_' + os.path.basename(p.dataset_path or '').removesuffix('.csv')) for p in owned):
        raise HTTPException(status_code=404, detail='File not found')
    try:
        filepath = os.path.join(storage.local_fallback_dir, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Local file not found")
        with open(filepath, 'rb') as f:
            data = f.read()
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/octet-stream",
            headers={"content-disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/presigned-download-dataset")
def get_presigned_download_dataset(project_id: str, imputation_method: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.username == current_user.username).first()
    if not project or not project.dataset_path:
        raise HTTPException(status_code=404, detail="Dataset not found or unauthorized")
    try:
        path = project.dataset_path
        if imputation_method:
            raw_bytes = storage.download_file(project.dataset_path)
            import pandas as pd
            df = pd.read_csv(io.BytesIO(raw_bytes))
            
            target_values = df[project.target_variable].copy()
            df = apply_imputation(df.drop(columns=[project.target_variable]), imputation_method)
            df[project.target_variable] = target_values
            
            out = io.StringIO()
            df.to_csv(out, index=False)
            imputed_bytes = out.getvalue().encode("utf-8")
            
            base_filename = os.path.basename(project.dataset_path).replace(".csv", "")
            imputed_filename = f"imputed_{base_filename}_{imputation_method.lower()}.csv"
            
            path = storage.upload_dataset(imputed_filename, imputed_bytes)
            
        signed_url = storage.generate_presigned_download_url(path)
        return {"url": signed_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned download URL: {e}")

@router.get("/{project_id}/presigned-download-model")
def get_presigned_download_model(project_id: str, model_name: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.username == current_user.username).first()
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    if not project or not card or not card.model_path:
        raise HTTPException(status_code=404, detail="Model binary not found for this project")
    
    path = card.model_path
    if model_name:
        m_slug = model_name.lower().replace(" ", "_")
        if path.startswith("s3://"):
            path = f"s3://aidso-runs/models/{project_id}/{m_slug}.pkl"
        elif path.startswith("file://"):
            folder = os.path.dirname(path[7:])
            path = 'file://' + os.path.join(folder, f'{project_id}_{m_slug}.pkl')
            
    try:
        signed_url = storage.generate_presigned_download_url(path)
        return {"url": signed_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned download URL: {e}")

@router.post("")
async def create_project(
    name: str = Form(...),
    target_variable: str = Form(...),
    description: str = Form(''),
    problem_type: str = Form('auto'),
    dataset_path: str = Form(None),
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    s3_path = dataset_path
    filename = "dataset.csv"
    if file:
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        file_bytes = await file.read(50 * 1024 * 1024 + 1)
        if len(file_bytes) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail='Maximum dataset size is 50MB')
        filename = file.filename
        s3_path = storage.upload_dataset(f"{current_user.username}_{__import__('uuid').uuid4().hex}_{os.path.basename(filename)}", file_bytes)
    elif dataset_path:
        if not os.path.basename(dataset_path).startswith(current_user.username + '_') or (dataset_path.startswith('file://') and os.path.commonpath([os.path.abspath(dataset_path[7:]), os.path.abspath('./tmp/minio_fallback')]) != os.path.abspath('./tmp/minio_fallback')):
            raise HTTPException(status_code=400, detail='Dataset must be uploaded by the current user')
        filename = dataset_path.split("/")[-1]
        try:
            file_bytes = storage.download_file(dataset_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to retrieve uploaded file from S3: {e}")
    else:
        raise HTTPException(status_code=400, detail="Either file upload or dataset_path is required")

    # Security validation & Antivirus check
    try:
        validate_csv_content(file_bytes)
    except Exception as e:
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(status_code=400, detail=str(e))

    if not scan_file_for_virus(file_bytes):
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(
            status_code=400,
            detail="Security Threat Detected: File was flagged by Antivirus scan and rejected."
        )

    # Enforce file size limit
    MAX_FILE_SIZE = 50 * 1024 * 1024
    if len(file_bytes) > MAX_FILE_SIZE:
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(
            status_code=400, 
            detail=f"File exceeds maximum allowed size of 50MB (actual: {len(file_bytes) / (1024*1024):.1f}MB)"
        )

    # Dataset Intelligence Service
    try:
        profile = DatasetService.profile_dataset(file_bytes, target_variable, problem_type)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    
    # Enforce rows and columns limit
    if profile.get("rows_count", 0) > 100000:
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(
            status_code=400,
            detail=f"Dataset rows exceed maximum allowed limit of 100,000 (actual: {profile['rows_count']})"
        )
    if profile.get("columns_count", 0) > 200:
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(
            status_code=400,
            detail=f"Dataset columns exceed maximum allowed limit of 200 (actual: {profile['columns_count']})"
        )

    # Gemini AI Project Understanding Agent
    understanding = gemini.understand_project(name, description, target_variable)
    understanding['problem_type'] = profile['problem_type']
    understanding['target_variable'] = target_variable
    understanding['recommended_metrics'] = ['rmse', 'mae', 'r2'] if profile['problem_type'] == 'regression' else ['f1_score', 'accuracy']
    
    # Generate the Gemini dataset summary analysis
    eda_summary = gemini.analyze_eda_profile(name, profile)
    
    if not name.strip(): raise HTTPException(status_code=400, detail='Project name is required')
    import uuid
    project_id = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'project'
    project_id += '-' + uuid.uuid4().hex[:10]
    db_project = Project(
        id=project_id,
        name=name,
        target_variable=target_variable,
        problem_type=understanding.get("problem_type", "classification"),
        description=description,
        status="EDA Phase",
        dataset_path=s3_path,
        username=current_user.username,
        eda_profile_json=profile,
        eda_analysis=eda_summary
    )
    db.add(db_project)
    
    # Log Timeline events
    db.add(TimelineEvent(
        project_id=project_id,
        title="Dataset Uploaded",
        description=f"Raw dataset file {filename} saved successfully to storage: {s3_path}",
        event_type="success"
    ))
    
    db.add(TimelineEvent(
        project_id=project_id,
        title="Project Understood",
        description=f"Dataset task identified as {understanding.get('problem_type')} targeting '{target_variable}'. Suggested metrics: {', '.join(understanding.get('recommended_metrics', []))}",
        event_type="info"
    ))

    # Initialize Knowledge Card
    db_card = KnowledgeCard(
        project_id=project_id,
        best_model="None",
        rows_count=profile["rows_count"],
        columns_count=profile["columns_count"],
        missing_values_pct=profile["missing_pct"],
        balancing_method="None",
        models_tested_count=0,
        numerical_count=profile["numerical_count"],
        categorical_count=profile["categorical_count"],
        quality_health_json=profile["quality_health"],
        models_comparison_json={
            'XGBoost': { 'status': 'Idle', 'metric': None },
            'LightGBM': { 'status': 'Idle', 'metric': None },
            'Random Forest': { 'status': 'Idle', 'metric': None },
            'Neural Network': { 'status': 'Idle', 'metric': None },
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
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Project).filter(Project.username == current_user.username)
    return query.all()

@router.get("/{project_id}")
def get_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    
    # Fetch cached EDA profile from Redis with DB fallback
    cached_eda = cache.get_cached_eda(project_id)
    if not cached_eda:
        cached_eda = project.eda_profile_json
        
    eda_analysis = project.eda_analysis
    if not eda_analysis and cached_eda:
        try:
            eda_analysis = gemini.analyze_eda_profile(project.name, cached_eda)
            project.eda_analysis = eda_analysis
            db.commit()
        except Exception:
            pass
    
    decisions = db.query(DecisionMemory).filter(DecisionMemory.project_id == project_id).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.project_id == project_id).order_by(TimelineEvent.timestamp.desc()).all()
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    
    return {
        "project": project,
        "decisions": decisions,
        "timeline": timeline,
        "knowledge_card": card,
        "cached_eda": cached_eda,
        "eda_analysis": eda_analysis,
        "hpo_trials": (db.query(TrainingJob).filter(TrainingJob.project_id == project_id, TrainingJob.status == 'completed').order_by(TrainingJob.id.desc()).first().metrics_json or {}).get('hpo_trials', []) if db.query(TrainingJob).filter(TrainingJob.project_id == project_id, TrainingJob.status == 'completed').first() else []
    }

@router.post("/{project_id}/override")
def apply_override(project_id: str, payload: DecisionOverride, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    return transform_feature(project_id, TransformFeaturePayload(feature_name=payload.feature_name, transformation=payload.user_choice), current_user, db)

@router.get("/{project_id}/download-model")
def download_model(project_id: str, model_name: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    if not project or not card or not card.model_path:
        raise HTTPException(status_code=404, detail="Model binary not found or unauthorized")
        
    try:
        path = card.model_path
        if model_name:
            m_slug = model_name.lower().replace(" ", "_")
            if path.startswith("s3://"):
                path = f"s3://aidso-runs/models/{project_id}/{m_slug}.pkl"
            elif path.startswith("file://"):
                folder = os.path.dirname(path[7:])
                path = 'file://' + os.path.join(folder, f'{project_id}_{m_slug}.pkl')
                
        model_bytes = storage.download_file(path)
        
        # Parse dataset name from project.dataset_path
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model binary: {e}")


def apply_imputation(df, method: str):
    import numpy as np
    from sklearn.impute import SimpleImputer, KNNImputer
    if method not in {'Median', 'Mean', 'Mode', 'KNN'}:
        raise HTTPException(status_code=400, detail='Unsupported imputation method')
    output = df.copy().replace([np.inf, -np.inf], np.nan)
    numeric = output.select_dtypes(include=np.number).columns.tolist()
    if numeric:
        imputer = KNNImputer(n_neighbors=5, keep_empty_features=True) if method == 'KNN' else SimpleImputer(strategy={'Median':'median', 'Mean':'mean', 'Mode':'most_frequent'}[method], keep_empty_features=True)
        output[numeric] = imputer.fit_transform(output[numeric])
    for column in output.columns.difference(numeric):
        mode = output[column].mode()
        output[column] = output[column].fillna(mode.iloc[0] if len(mode) else 'Missing')
    return output


@router.get("/{project_id}/download-dataset")
def download_dataset(project_id: str, imputation_method: str = "Median", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import pandas as pd
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    if not project or not project.dataset_path:
        raise HTTPException(status_code=404, detail="Dataset not found or unauthorized")
        
    try:
        # Load raw dataset from S3/MinIO
        file_bytes = storage.download_file(project.dataset_path)
        df = pd.read_csv(io.BytesIO(file_bytes))
        
        # Apply imputation method
        modified_df = apply_imputation(df.drop(columns=[project.target_variable]), imputation_method)
        modified_df[project.target_variable] = df[project.target_variable]
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and download dataset: {e}")


class TransformFeaturePayload(BaseModel):
    feature_name: str
    transformation: str


@router.post("/{project_id}/transform")
def transform_feature(project_id: str, payload: TransformFeaturePayload, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
        
    if db.query(TrainingJob).filter(TrainingJob.project_id == project_id, TrainingJob.status.in_(['queued', 'running'])).first():
        raise HTTPException(status_code=409, detail='Wait for training to finish before changing transformations')
    from services.preprocessing import CHOICES, transformed_preview
    import pandas as pd
    import numpy as np
    df = pd.read_csv(io.BytesIO(storage.download_file(project.dataset_path)))
    feature = payload.feature_name
    if feature == project.target_variable or feature not in df.columns:
        raise HTTPException(status_code=400, detail='Choose a predictor column, not the target')
    records = db.query(DecisionMemory).filter(DecisionMemory.project_id == project_id).all()
    dec = next((d for d in records if d.feature_name == feature), None)
    if not dec: raise HTTPException(status_code=400, detail='Unknown feature')
    choice = dec.decision if payload.transformation == 'recommended' else payload.transformation
    if choice not in CHOICES: raise HTTPException(status_code=400, detail='Unsupported transformation')
    choices = {d.feature_name: (d.user_choice if d.override_active else d.decision) for d in records}
    choices[feature] = choice
    try:
        preview = transformed_preview(df, project.target_variable, choices)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    def numeric(series):
        return pd.to_numeric(series, errors='coerce') if pd.api.types.is_numeric_dtype(series) else pd.Series(pd.factorize(series)[0], index=series.index)
    target = numeric(df[project.target_variable])
    before = numeric(df[feature]).corr(target)
    after_columns = [c for c in preview.columns if c == feature or c.startswith(feature + '_')]
    after_values = [abs(numeric(preview[c]).corr(target)) for c in after_columns]
    before = float(abs(before)) if pd.notna(before) else 0.0
    after = max((float(c) for c in after_values if pd.notna(c)), default=0.0)
    missing_before = int(df[feature].isna().sum())
    missing_after = int(preview[after_columns].isna().sum().sum())
    comparison = {'before_corr': round(before, 4), 'after_corr': round(after, 4), 'improvement': round(after-before, 4), 'before_missing': missing_before, 'after_missing': missing_after, 'better': bool(after-before > .001 or missing_after < missing_before)}
    storage.upload_dataset(f'{project_id}_transformed.csv', preview.to_csv(index=False).encode())
    dec.override_active = payload.transformation != 'recommended'
    dec.user_choice = choice if dec.override_active else None
    dec.comparison_metrics_json = comparison
    project.status = 'Preprocessed'
    card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
    if card:
        card.status = 'Preprocessed'
        card.best_model = 'None'
        card.best_f1 = None
        card.best_accuracy = None
        card.best_mse = None
        card.model_path = None
        card.models_tested_count = 0
        card.models_comparison_json = {}
        card.top_features = []
        card.shap_global_json = []
        card.shap_local_json = None
    db.add(TimelineEvent(project_id=project_id, title='Feature Transformed', description=f"Applied {choice} to {feature}; preprocessing will be fitted on training rows only.", event_type='success'))
    db.commit()
    return {'status': 'success', 'metrics': comparison}


@router.get("/{project_id}/presigned-download-transformed")
def get_presigned_download_transformed(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    try:
        filename = f"{project_id}_transformed.csv"
        if getattr(storage, "client_enabled", True):
            path = f"s3://{storage.bucket_name}/datasets/{filename}"
        else:
            path = f"file://{os.path.abspath(os.path.join(storage.local_fallback_dir, filename))}"
            
        signed_url = storage.generate_presigned_download_url(path)
        return {"url": signed_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned download URL: {e}")


@router.get("/{project_id}/download-transformed")
def download_transformed_dataset(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.username == current_user.username
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    try:
        filename = f"{project_id}_transformed.csv"
        if getattr(storage, "client_enabled", True):
            path = f"s3://{storage.bucket_name}/datasets/{filename}"
        else:
            path = f"file://{os.path.abspath(os.path.join(storage.local_fallback_dir, filename))}"
            
        file_bytes = storage.download_file(path)
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        # Fallback to download original dataset if transformed doesn't exist
        try:
            file_bytes = storage.download_file(project.dataset_path)
            orig_filename = os.path.basename(project.dataset_path)
            return StreamingResponse(
                io.BytesIO(file_bytes),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{orig_filename}"'}
            )
        except Exception:
            raise HTTPException(status_code=500, detail=f"Failed to download transformed dataset: {e}")

