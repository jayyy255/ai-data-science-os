from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import TimelineEvent, KnowledgeCard
from services.gemini import GeminiService

router = APIRouter(prefix="/api/projects", tags=["chat"])

gemini = GeminiService()

class ChatQuery(BaseModel):
    question: str

@router.post("/{project_id}/chat")
def chat(project_id: str, payload: ChatQuery, db: Session = Depends(get_db)):
    card = db.query(KnowledgeCard).filter(KnowledgeCard.project_id == project_id).first()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.project_id == project_id).limit(5).all()
    
    card_dict = {
        "best_model": card.best_model if card else "None",
        "best_f1": card.best_f1 if card else 0.0,
        "rows_count": card.rows_count if card else 0,
        "columns_count": card.columns_count if card else 0,
        "status": card.status if card else "N/A"
    }
    
    timeline_list = [f"{evt.title}: {evt.description}" for evt in timeline]
    
    response = gemini.assistant_chat(payload.question, card_dict, timeline_list)
    return {"answer": response}
