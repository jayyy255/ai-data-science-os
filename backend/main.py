import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import engine
from database.models import Base
from routers.projects import router as projects_router
from routers.training import router as training_router
from routers.chat import router as chat_router
from routers.auth import router as auth_router
from routers.test_storage import router as test_storage_router

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Add new columns if they do not exist in the database (migration fallback)
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS dataset_path VARCHAR;"))
        conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS username VARCHAR;"))
        conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS eda_profile_json JSON;"))
        conn.execute(text("ALTER TABLE knowledge_cards ADD COLUMN IF NOT EXISTS model_path VARCHAR;"))
        conn.execute(text("ALTER TABLE knowledge_cards ADD COLUMN IF NOT EXISTS models_comparison_json JSON;"))
        conn.execute(text("ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS imputation_method VARCHAR DEFAULT 'Median';"))
        conn.execute(text("ALTER TABLE decision_memory ADD COLUMN IF NOT EXISTS comparison_metrics_json JSON;"))
        conn.commit()
        print("Database schema migration checked successfully.")
    except Exception as e:
        print(f"Database migration columns exception: {e}")

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
app.include_router(auth_router)
app.include_router(test_storage_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
