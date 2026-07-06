from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import io
import os
import re
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import Project, DecisionMemory, TimelineEvent, KnowledgeCard
from services.dataset import DatasetService
from services.gemini import GeminiService
from services.storage.factory import get_storage_provider
from services.cache import RedisCacheService
from services.security import validate_csv_content, scan_file_for_virus

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
def get_presigned_upload_url(payload: PresignedUrlRequest):
    try:
        res = storage.generate_presigned_upload_url(payload.filename)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned upload URL: {e}")

@router.post("/upload-local")
async def upload_local_file(filename: str, file: UploadFile = File(...)):
    try:
        content = await file.read()
        path = storage.upload_dataset(filename, content)
        return {"status": "success", "s3_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload local file: {e}")

@router.get("/download-local-file")
def download_local_file(filename: str):
    try:
        filepath = os.path.join("./tmp/minio_fallback", filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Local file not found")
        with open(filepath, 'rb') as f:
            data = f.read()
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/octet-stream",
            headers={"content-disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/presigned-download-dataset")
def get_presigned_download_dataset(project_id: str, imputation_method: str = None, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.dataset_path:
        raise HTTPException(status_code=404, detail="Dataset not found for this project")
    try:
        path = project.dataset_path
        if imputation_method:
            raw_bytes = storage.download_file(project.dataset_path)
            import pandas as pd
            df = pd.read_csv(io.BytesIO(raw_bytes))
            
            df = apply_imputation(df, imputation_method)
            
            out = io.StringIO()
            df.to_csv(out, index=False)
            imputed_bytes = out.getvalue().encode("utf-8")
            
            base_filename = os.path.basename(project.dataset_path).replace(".csv", "")
            imputed_filename = f"imputed_{base_filename}_{imputation_method.lower()}.csv"
            
            path = storage.upload_dataset(imputed_filename, imputed_bytes)
            
        signed_url = storage.generate_presigned_download_url(path)
        return {"url": signed_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned download URL: {e}")

@router.get("/{project_id}/presigned-download-model")
def get_presigned_download_model(project_id: str, model_name: str = None, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    if not project or not card or not card.model_path:
        raise HTTPException(status_code=404, detail="Model binary not found for this project")
    
    path = card.model_path
    if model_name:
        m_slug = model_name.lower().replace(" ", "_")
        if path.startswith("s3://"):
            path = f"s3://aidso-runs/models/{project_id}/{m_slug}.pkl"
        elif path.startswith("file://"):
            folder = re.sub(r'/[^/]+\.pkl$', '', path)
            path = f"{folder}/{project_id}_{m_slug}.pkl"
            
    try:
        signed_url = storage.generate_presigned_download_url(path)
        return {"url": signed_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned download URL: {e}")

@router.post("")
async def create_project(
    name: str = Form(...),
    target_variable: str = Form(...),
    description: str = Form(...),
    username: str = Form(None),
    dataset_path: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    s3_path = dataset_path
    filename = "dataset.csv"
    if file:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        file_bytes = await file.read()
        filename = file.filename
        s3_path = storage.upload_dataset(filename, file_bytes)
    elif dataset_path:
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
    MAX_FILE_SIZE = 100 * 1024 * 1024 # 100 MB
    if len(file_bytes) > MAX_FILE_SIZE:
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(
            status_code=400, 
            detail=f"File exceeds maximum allowed size of 100MB (actual: {len(file_bytes) / (1024*1024):.1f}MB)"
        )

    # Dataset Intelligence Service
    profile = DatasetService.profile_dataset(file_bytes, target_variable)
    
    # Enforce rows and columns limit
    if profile.get("rows_count", 0) > 200000:
        if s3_path:
            storage.delete_file(s3_path)
        raise HTTPException(
            status_code=400,
            detail=f"Dataset rows exceed maximum allowed limit of 200,000 (actual: {profile['rows_count']})"
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
    
    project_id = name.lower().replace(" ", "-")
    db_project = Project(
        id=project_id,
        name=name,
        target_variable=target_variable,
        problem_type=understanding.get("problem_type", "classification"),
        description=description,
        status="EDA Phase",
        dataset_path=s3_path,
        username=username,
        eda_profile_json=profile
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
    
    # Fetch cached EDA profile from Redis with DB fallback
    cached_eda = cache.get_cached_eda(project_id)
    if not cached_eda:
        cached_eda = project.eda_profile_json
    
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
    
    if method == 'KNN':
        try:
            from sklearn.impute import KNNImputer
            num_cols = df_copy.select_dtypes(include=[np.number]).columns.tolist()
            if len(num_cols) > 0:
                imputer = KNNImputer(n_neighbors=min(5, len(df_copy)))
                df_copy[num_cols] = imputer.fit_transform(df_copy[num_cols])
        except Exception as e:
            print(f"KNN Imputer failed, falling back to interpolation: {e}")
            for col in df_copy.columns:
                if df_copy[col].isnull().sum() > 0 and df_copy[col].dtype in ['int64', 'float64', 'float32', 'int32']:
                    df_copy[col] = df_copy[col].interpolate().fillna(df_copy[col].mean())
    else:
        for col in df_copy.columns:
            if df_copy[col].isnull().sum() > 0:
                if df_copy[col].dtype in ['int64', 'float64', 'float32', 'int32']:
                    if method == 'Mean':
                        df_copy[col] = df_copy[col].fillna(df_copy[col].mean())
                    elif method == 'Mode':
                        df_copy[col] = df_copy[col].fillna(df_copy[col].mode().iloc[0] if not df_copy[col].mode().empty else 0)
                    else: # Median (Default)
                        df_copy[col] = df_copy[col].fillna(df_copy[col].median())
                else:
                    df_copy[col] = df_copy[col].fillna(df_copy[col].mode().iloc[0] if not df_copy[col].mode().empty else "Missing")
                    
    # Ensure any remaining missing values are filled
    for col in df_copy.columns:
        if df_copy[col].isnull().sum() > 0:
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


class TransformFeaturePayload(BaseModel):
    feature_name: str
    transformation: str


@router.post("/{project_id}/transform")
def transform_feature(project_id: str, payload: TransformFeaturePayload, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    try:
        # 1. Download current raw/transformed dataset from storage
        # Check if transformed already exists, otherwise download original raw dataset
        filename = f"{project_id}_transformed.csv"
        if hasattr(storage, "bucket_name"):
            path = f"s3://{storage.bucket_name}/datasets/{filename}"
        else:
            path = f"file://{os.path.abspath(os.path.join('./tmp/minio_fallback', filename))}"
            
        try:
            file_bytes = storage.download_file(path)
            print(f"Loading already transformed dataset from {path}")
        except Exception:
            path = project.dataset_path
            file_bytes = storage.download_file(path)
            print(f"Loading raw base dataset from {path}")
            
        import pandas as pd
        import numpy as np
        import io
        
        df = pd.read_csv(io.BytesIO(file_bytes))
        
        # 2. Check if feature exists
        feature_name = payload.feature_name
        transformation = payload.transformation
        
        if feature_name not in df.columns:
            raise HTTPException(status_code=400, detail=f"Feature '{feature_name}' not found in dataset")
        if project.target_variable not in df.columns:
            raise HTTPException(status_code=400, detail=f"Target variable '{project.target_variable}' not found in dataset")
            
        # Helper to convert series to numeric representation for Pearson correlation computation
        def to_numeric_representation(series):
            if series.isnull().all():
                return pd.Series(0, index=series.index)
            if series.dtype == 'object' or series.dtype.name == 'category' or series.dtype == 'bool':
                return pd.Series(pd.factorize(series.fillna('Missing'))[0], index=series.index)
            return pd.to_numeric(series.fillna(0), errors='coerce').fillna(0)
            
        target_numeric = to_numeric_representation(df[project.target_variable])
        feat_before = df[feature_name]
        feat_before_numeric = to_numeric_representation(feat_before)
        
        # Calculate correlation before
        corr_before = feat_before_numeric.corr(target_numeric)
        corr_before = 0.0 if pd.isna(corr_before) else float(np.abs(corr_before))
        missing_before = int(feat_before.isnull().sum())
        
        # 3. Apply selected transformation
        df_trans = df.copy()
        val = df[feature_name]
        val_trans = val.copy()
        
        if transformation == "Impute Median":
            if val.dtype in [np.float64, np.float32, np.int64, np.int32]:
                val_trans = val.fillna(val.median())
            else:
                val_trans = val.fillna(val.mode().iloc[0] if not val.mode().empty else "Missing")
            df_trans[feature_name] = val_trans
            
        elif transformation == "Impute Mean":
            if val.dtype in [np.float64, np.float32, np.int64, np.int32]:
                val_trans = val.fillna(val.mean())
            else:
                val_trans = val.fillna(val.mode().iloc[0] if not val.mode().empty else "Missing")
            df_trans[feature_name] = val_trans
            
        elif transformation == "Standard Scaling":
            if val.dtype in [np.float64, np.float32, np.int64, np.int32]:
                val_filled = val.fillna(val.median())
            else:
                val_filled = pd.Series(pd.factorize(val.fillna('Missing'))[0], index=val.index)
            std_val = val_filled.std()
            if std_val > 0:
                val_trans = (val_filled - val_filled.mean()) / std_val
            else:
                val_trans = val_filled - val_filled.mean()
            df_trans[feature_name] = val_trans
            
        elif transformation == "One-Hot Encoding":
            dummies = pd.get_dummies(df[feature_name], prefix=feature_name, dtype=float)
            df_trans = df_trans.drop(columns=[feature_name])
            df_trans = pd.concat([df_trans, dummies], axis=1)
            
            # Find max absolute correlation of dummy columns
            max_corr = 0.0
            for col in dummies.columns:
                c_numeric = to_numeric_representation(dummies[col])
                corr_val = c_numeric.corr(target_numeric)
                corr_val = 0.0 if pd.isna(corr_val) else float(np.abs(corr_val))
                if corr_val > max_corr:
                    max_corr = corr_val
            corr_after = max_corr
            val_trans = pd.Series(0, index=val.index)
            
        elif transformation == "Discretize Binning":
            if val.dtype in [np.float64, np.float32, np.int64, np.int32]:
                val_filled = val.fillna(val.median())
            else:
                val_filled = pd.Series(pd.factorize(val.fillna('Missing'))[0], index=val.index)
            try:
                val_trans = pd.qcut(val_filled, q=4, labels=False, duplicates='drop')
            except Exception:
                val_trans = pd.cut(val_filled, bins=4, labels=False)
            df_trans[feature_name] = val_trans
            
        else: # Keep Raw / Apply AI Recommended / fallback
            val_trans = val.copy()
            df_trans[feature_name] = val_trans
            
        # Calculate correlation after (if not already set by One-Hot Encoding)
        if transformation != "One-Hot Encoding":
            feat_after_numeric = to_numeric_representation(val_trans)
            corr_after = feat_after_numeric.corr(target_numeric)
            corr_after = 0.0 if pd.isna(corr_after) else float(np.abs(corr_after))
            missing_after = int(val_trans.isnull().sum())
        else:
            missing_after = 0
            
        improvement = corr_after - corr_before
        better = improvement > 0.001 or (missing_before > 0 and missing_after == 0)
        
        comparison = {
            "before_corr": round(corr_before, 4),
            "after_corr": round(corr_after, 4),
            "improvement": round(improvement, 4),
            "before_missing": missing_before,
            "after_missing": missing_after,
            "better": bool(better)
        }
        
        # 4. Upload the transformed dataset back to storage (overwriting the project transformed file)
        out_buf = io.StringIO()
        df_trans.to_csv(out_buf, index=False)
        csv_bytes = out_buf.getvalue().encode("utf-8")
        
        transformed_filename = f"{project_id}_transformed.csv"
        storage.upload_dataset(transformed_filename, csv_bytes)
        
        # 5. Update DecisionMemory database record
        dec = db.query(DecisionMemory).filter(
            DecisionMemory.project_id == project_id,
            DecisionMemory.feature_name == feature_name
        ).first()
        
        if not dec:
            dec = DecisionMemory(
                project_id=project_id,
                feature_name=feature_name,
                decision="User Choice Applied",
                reason="User Override Action",
                confidence=1.0
            )
            db.add(dec)
            
        dec.override_active = True
        dec.user_choice = transformation
        dec.comparison_metrics_json = comparison
        
        db.add(TimelineEvent(
            project_id=project_id,
            title="Feature Transformed",
            description=f"Applied {transformation} on '{feature_name}'. Target correlation: {round(corr_before, 3)} -> {round(corr_after, 3)}.",
            event_type="success"
        ))
        db.commit()
        db.refresh(dec)
        
        return {
            "status": "success",
            "decision": {
                "id": dec.id,
                "project_id": dec.project_id,
                "feature_name": dec.feature_name,
                "decision": dec.decision,
                "reason": dec.reason,
                "confidence": dec.confidence,
                "override_active": dec.override_active,
                "user_choice": dec.user_choice,
                "comparison_metrics_json": dec.comparison_metrics_json
            },
            "metrics": comparison
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to transform feature: {e}")


@router.get("/{project_id}/presigned-download-transformed")
def get_presigned_download_transformed(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        filename = f"{project_id}_transformed.csv"
        if hasattr(storage, "bucket_name"):
            path = f"s3://{storage.bucket_name}/datasets/{filename}"
        else:
            path = f"file://{os.path.abspath(os.path.join('./tmp/minio_fallback', filename))}"
            
        signed_url = storage.generate_presigned_download_url(path)
        return {"url": signed_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned download URL: {e}")


@router.get("/{project_id}/download-transformed")
def download_transformed_dataset(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        filename = f"{project_id}_transformed.csv"
        if hasattr(storage, "bucket_name"):
            path = f"s3://{storage.bucket_name}/datasets/{filename}"
        else:
            path = f"file://{os.path.abspath(os.path.join('./tmp/minio_fallback', filename))}"
            
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

