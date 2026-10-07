from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database.connection import get_db
from database.models import TimelineEvent, KnowledgeCard, Project, User, DecisionMemory
from services.gemini import GeminiService
from services.cache import RedisCacheService
from services.security import get_current_user

router = APIRouter(prefix="/api/projects", tags=["chat"])

gemini = GeminiService()
cache = RedisCacheService()

class ChatQuery(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

@router.post("/{project_id}/chat")
def chat(project_id: str, payload: ChatQuery, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id, Project.username == current_user.username).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")

    if not payload.question.strip(): raise HTTPException(status_code=400, detail='Question is required')
    cache_question = str(project.updated_at) + ':' + payload.question
    # Cache responses against the project revision.
    cached_response = cache.get_cached_chat(project_id, cache_question)
    if cached_response:
        print(f"Serving chatbot response from Redis Cache for key: {payload.question}")
        return {"answer": cached_response}

    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.project_id == project_id).order_by(TimelineEvent.timestamp.desc()).limit(5).all()
    
    card_dict = {
        "best_model": card.best_model if card else "None",
        "best_f1": card.best_f1 if card else None,
        "best_mse": card.best_mse if card else None,
        "problem_type": project.problem_type,
        "target": project.target_variable,
        "top_features": card.top_features if card else [],
        "decisions": [{'feature': d.feature_name, 'transformation': d.user_choice if d.override_active else d.decision} for d in db.query(DecisionMemory).filter_by(project_id=project_id).all()],
        "rows_count": card.rows_count if card else 0,
        "columns_count": card.columns_count if card else 0,
        "status": project.status
    }
    
    timeline_list = [f"{evt.title}: {evt.description}" for evt in timeline]
    
    response = gemini.assistant_chat(payload.question, card_dict, timeline_list)
    
    # 2. Store response in Redis Assistant Cache
    cache.set_cached_chat(project_id, cache_question, response)
    
    return {"answer": response}

