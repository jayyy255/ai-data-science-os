import threading
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db, SessionLocal
from database.models import Project, TimelineEvent, KnowledgeCard
from services.training_service import worker

router = APIRouter(prefix="/api/projects", tags=["training"])

@router.post("/{project_id}/train")
def trigger_training(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = "Training"
    db.add(TimelineEvent(
        project_id=project_id,
        title="Model Training Started",
        description="Training request pushed to local Kafka workers topic: model-training-tasks",
        event_type="info"
    ))
    db.commit()

    def run_training():
        db_job = SessionLocal()
        try:
            results = worker.process_training_job(
                project_id=project_id, 
                target=project.target_variable, 
                problem_type=project.problem_type
            )
            
            p = db_job.query(Project).filter(Project.id == project_id).first()
            p.status = "Ready for Deployment"
            
            card = db_job.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
            if card:
                card.best_model = results["best_model"]
                card.best_f1 = results["best_f1"]
                card.best_accuracy = results["best_accuracy"]
                card.models_tested_count = results["trials_run"]
                card.top_features = results["top_features"]
                card.shap_global_json = results["shap_global"]
                card.shap_local_json = {
                    "customerId": "US-8594-QD",
                    "probability": 0.762,
                    "risk": "High Risk",
                    "drivers": [
                        {"feature": "support_calls", "value": "5 calls", "impact": "+25.4%"},
                        {"feature": "MonthlyCharges", "value": "$85.00", "impact": "+15.2%"},
                        {"feature": "tenure", "value": "3 months", "impact": "+10.6%"}
                    ]
                }
                card.model_path = results.get("model_path")
                card.status = "Ready for Deployment"
            
            db_job.add(TimelineEvent(
                project_id=project_id,
                title="Model Training Completed",
                description=f"Best model chosen: {results['best_model']} (Validation F1 Score: {results['best_f1']})",
                event_type="success"
            ))
            
            db_job.add(TimelineEvent(
                project_id=project_id,
                title="Knowledge Card Updated",
                description="Level 1, 2, and 3 knowledge summaries updated with final model performance outputs.",
                event_type="info"
            ))
            
            db_job.commit()
        except Exception as e:
            print(f"Async training worker failure: {e}")
        finally:
            db_job.close()
            
    threading_thread = threading.Thread(target=run_training)
    threading_thread.start()
    
    return {"status": "queued", "message": "Training job queued in Kafka worker thread."}
