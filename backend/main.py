import uvicorn
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from database.connection import engine, get_db
from database.models import WorkerHeartbeat
from routers.projects import router as projects_router
from routers.training import router as training_router
from routers.chat import router as chat_router
from routers.auth import router as auth_router
from routers.inference import router as inference_router

from database.schema import initialize_database
from sqlalchemy import text
from services.security import get_current_user
initialize_database(engine)

with engine.connect() as conn:
    # Seed dummy user: dummy_user / dummy@aidso.ai / password123
    try:
        if os.getenv('ENVIRONMENT', 'local') != 'local':
            raise RuntimeError('Demo account seeding disabled in production')
        cursor = conn.execute(text("SELECT username FROM users WHERE username = 'dummy_user';")).fetchone()
        if not cursor:
            import bcrypt
            hashed = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(text(
                "INSERT INTO users (full_name, username, email, password_hash) "
                "VALUES ('Demo Dummy Account', 'dummy_user', 'dummy@aidso.ai', :pw_hash);"
            ), {"pw_hash": hashed})
            conn.commit()
            print("Seeded 'dummy_user' account successfully.")
    except Exception as e:
        print(f"Database dummy user seeding exception: {e}")

app = FastAPI(title="AIDSO Backend API", version="1.0.0")

@app.get('/api/health')
def health():
    return {"status": "ok"}

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8081,http://127.0.0.1:8081').split(',') if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(projects_router)
app.include_router(training_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(inference_router)
# Storage diagnostics are not exposed as a public data endpoint.

@app.get('/api/system')
def system_status(user=Depends(get_current_user), db=Depends(get_db)):
    from services.storage.factory import get_storage_provider
    from services.gemini import GeminiService
    storage = get_storage_provider()
    heartbeat = db.query(WorkerHeartbeat).order_by(WorkerHeartbeat.timestamp.desc()).first()
    return {
        'database': engine.dialect.name,
        'storage': 'AWS S3' if os.getenv('ENVIRONMENT', 'local') != 'local' else 'MinIO' if storage.client_enabled else 'Local filesystem',
        'gemini': 'Configured' if GeminiService().client_enabled else 'Not configured (local summaries available)',
        'worker_last_seen': heartbeat.timestamp.isoformat() + 'Z' if heartbeat else None,
        'queue': 'Database task queue',
    }

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')), reload=True)
