# AIDSO (AI Data Science OS)

AIDSO turns a CSV into a reproducible classification or regression project: profile data, review transformations, train models, export fitted pipelines, run predictions and explanations, and compare new data for drift.

The React frontend talks to FastAPI. A separate Python worker claims training jobs from the database. Production services share PostgreSQL and S3; local development can use SQLite and local files. Redis and Gemini are optional. Kafka and MLflow are not required for the training workflow.

## Local development

Use Python 3.11 or 3.12 and Node 22. From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
./scripts/start-local.ps1
```

Open http://127.0.0.1:5176. The launcher starts the API on port 8002, the training worker, and Vite. Logs and process IDs are saved in `tmp/`. Stop only those saved IDs to shut down. Change ports with `-BackendPort` and `-FrontendPort`.

Alternatively, start three separate terminals:

```powershell
# From backend/
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload
# From backend/, another terminal
python worker/worker.py
# From frontend/, another terminal
$env:AIDSO_BACKEND_URL = 'http://127.0.0.1:8002'
npm run dev -- --port 5176
```

Create an account in the app. A local demo account is seeded: `dummy_user` / `password123`. Demo seeding is disabled in production. Training requires at least 12 rows and at least 3 examples of every classification class.

With Docker Desktop running, `docker compose up --build -d` serves the app at http://localhost:8081. Configuration examples are in `backend/.env.example` and `frontend/.env.example`.

## Workflow

1. Upload a CSV and choose a target and task type.
2. Inspect distributions, correlations, missing values, and target balance.
3. Review feature decisions. Training fits preprocessing only on training data and saves it with each pipeline.
4. Start training. The worker compares Random Forest, XGBoost, LightGBM, and a neural network when installed, with five validation HPO trials per available model. Automatic champion selection uses validation scores; held-out test metrics are reported separately.
5. Compare held-out test metrics, select a champion, and download pipelines accepting original predictor columns.
6. Run predictions and explanations, export the knowledge card, or upload new data for a population stability comparison.

For local Gemini responses, set `GEMINI_API_KEY` in `backend/.env` and restart the API. Production reads the service environment variable. The assistant uses Gemini when available and clearly identified local summaries otherwise. Password recovery is not configured; unauthenticated requests cannot reset passwords.

## Verification

```powershell
# From backend/
python -m unittest discover -s tests -v
# From frontend/
npm run lint
npm run build
```

Tests use an isolated temporary database and artifact folder. They cover authentication isolation, uploads, transformations, imputation, classification/regression training, inference, explanations, downloads, drift, provider failures, and schema initialization.

For the full live API/worker workflow, run `python scripts/e2e_workflows.py` from the repository root. It uses disposable storage and saves a JSON result report in `tmp/`. See [VERIFICATION.md](VERIFICATION.md) for tested features and configuration limits.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Render and Railway service folders, build/start commands, PostgreSQL/S3 requirements, and environment variables. Deploy the frontend, API, and worker separately.
