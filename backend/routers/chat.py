from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database.connection import get_db
from database.models import Project, User
from services.gemini import GeminiService
from services.cache import RedisCacheService
from services.security import get_current_user
from services.assistant_context import build_assistant_context

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
    context, revision = build_assistant_context(db, project)
    cache_question = 'v4:' + revision + ':' + payload.question
    cached_response = cache.get_cached_chat(project_id, cache_question)
    if cached_response:
        return {'answer': cached_response}
    response = gemini.assistant_chat(payload.question, context['knowledge_card'], context['timeline'], context['execution_logs'])

    # 2. Store response in Redis Assistant Cache
    if not response.startswith(('Gemini is unavailable.', 'Gemini timed out.', 'Gemini is not configured.')):
        cache.set_cached_chat(project_id, cache_question, response)

    return {"answer": response}
