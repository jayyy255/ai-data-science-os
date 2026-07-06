import threading
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Project, TimelineEvent, KnowledgeCard, TrainingJob

router = APIRouter(prefix="/api/projects", tags=["training"])

@router.post("/{project_id}/train")
def trigger_training(project_id: str, imputation_method: str = "Median", db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if there is already a queued or running job for this project
    existing_job = db.query(TrainingJob).filter(
        TrainingJob.project_id == project_id,
        TrainingJob.status.in_(["queued", "running"])
    ).first()
    
    if existing_job:
        return {"status": existing_job.status, "message": f"Training job is already {existing_job.status}."}

    project.status = "Training"
    db.add(TimelineEvent(
        project_id=project_id,
        title="Model Training Queued",
        description=f"Training job successfully registered in database task queue using '{imputation_method}' imputation method.",
        event_type="info"
    ))
    
    # Create the training job entry
    new_job = TrainingJob(
        project_id=project_id,
        status="queued",
        model_type=f"Multi-Model Ensemble & HPO ({imputation_method})",
        imputation_method=imputation_method
    )
    db.add(new_job)
    db.commit()
    
    return {"status": "queued", "message": "Training job registered in database task queue."}


@router.get("/{project_id}/jobs")
def list_training_jobs(project_id: str, db: Session = Depends(get_db)):
    jobs = db.query(TrainingJob).filter(TrainingJob.project_id == project_id).order_by(TrainingJob.created_at.desc()).all()
    return {"jobs": jobs}

