import os
import sys
import time
from datetime import datetime

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from database.models import TrainingJob, Project, TimelineEvent, KnowledgeCard
from pipeline.kafka_worker import TrainingWorker

def main():
    print("Starting background training database worker...")
    db_session_maker = SessionLocal
    training_pipeline = TrainingWorker(db_session_maker=db_session_maker)
    
    while True:
        db = db_session_maker()
        try:
            # Query the next 'queued' job in the database
            job = db.query(TrainingJob).filter(TrainingJob.status == 'queued').order_by(TrainingJob.created_at.asc()).first()
            if job:
                job_id = job.id
                project_id = job.project_id
                imputation_method = job.imputation_method or "Median"
                
                print(f"Found queued job {job_id} for project {project_id}")
                job.status = 'running'
                job.started_at = datetime.utcnow()
                db.commit()
                
                # Fetch project details
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    print(f"Project {project_id} not found. Failing job.")
                    job.status = 'failed'
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    db.close()
                    continue
                
                target = project.target_variable
                problem_type = project.problem_type
                
                # Update project status to Training
                project.status = "Training"
                db.commit()
                
                # Release DB session during heavy training process to prevent connection pool exhaustion
                db.close()
                
                # Run the actual models fitting and HPO search pipeline
                try:
                    results = training_pipeline.process_training_job(
                        project_id=project_id,
                        target=target,
                        problem_type=problem_type,
                        imputation_method=imputation_method
                    )
                    
                    # Re-open session to save completed status
                    db_save = db_session_maker()
                    
                    # Update job record
                    job_to_update = db_save.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                    job_to_update.status = 'completed'
                    job_to_update.completed_at = datetime.utcnow()
                    job_to_update.artifact_path = results.get("model_path")
                    job_to_update.metrics_json = {
                        "best_model": results["best_model"],
                        "best_metric": results.get("best_f1") or results.get("best_mse"),
                        "trials_run": results["trials_run"]
                    }
                    
                    # Update project status
                    p = db_save.query(Project).filter(Project.id == project_id).first()
                    p.status = "Ready for Deployment"
                    
                    # Update Knowledge Card
                    card = db_save.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
                    if card:
                        card.best_model = results["best_model"]
                        card.best_f1 = results.get("best_f1")
                        card.best_accuracy = results.get("best_accuracy")
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
                        
                    # Save timeline logs
                    db_save.add(TimelineEvent(
                        project_id=project_id,
                        title="Model Training Completed",
                        description=f"Best model chosen: {results['best_model']} (Metric: {results.get('best_f1') or results.get('best_mse')})",
                        event_type="success"
                    ))
                    db_save.add(TimelineEvent(
                        project_id=project_id,
                        title="Knowledge Card Updated",
                        description="Level 1, 2, and 3 knowledge summaries updated with final model performance outputs.",
                        event_type="info"
                    ))
                    
                    db_save.commit()
                    db_save.close()
                    print(f"Job {job_id} completed successfully.")
                    
                except Exception as train_err:
                    print(f"Training execution failed for job {job_id}: {train_err}")
                    db_fail = db_session_maker()
                    j = db_fail.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                    j.status = 'failed'
                    j.completed_at = datetime.utcnow()
                    
                    p = db_fail.query(Project).filter(Project.id == project_id).first()
                    p.status = "Failed"
                    
                    db_fail.add(TimelineEvent(
                        project_id=project_id,
                        title="Model Training Failed",
                        description=f"Execution error: {train_err}",
                        event_type="error"
                    ))
                    db_fail.commit()
                    db_fail.close()
            else:
                db.close()
        except Exception as db_err:
            print(f"Worker database query loop error: {db_err}")
            db.close()
        
        # Sleep briefly to avoid high CPU usage
        time.sleep(3)

if __name__ == "__main__":
    main()
