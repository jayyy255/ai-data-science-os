import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import engine
from database.models import Base
from routers.projects import router as projects_router
from routers.training import router as training_router
from routers.chat import router as chat_router

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIDSO Backend API", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(projects_router)
app.include_router(training_router)
app.include_router(chat_router)

if __name__ == "__main__":
    uvicorn.run("main.py:app", host="0.0.0.0", port=8000, reload=True)
