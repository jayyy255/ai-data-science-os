# AIDSO (AI Data Science OS)

AIDSO is a secure, end-to-end automated machine learning (AutoML) platform that turns raw CSV datasets into reproducible classification and regression projects. It provides automated exploratory data analysis (EDA), feature engineering and imputation, sandboxed multi-model training with Optuna hyperparameter optimization, global and local SHAP model explainability, downloadable production pipelines, data drift monitoring (PSI), and an AI assistant grounded in training evidence.

---

## Key Features

### 1. Isolated Zero-Trust Compute Sandbox
- **No In-Host Execution**: All untrusted computation—CSV parsing, profiling, missing value imputation, feature transformations, model training/HPO, inference, SHAP calculations, and drift monitoring—runs inside single-use, disposable Docker containers (`aidso-sandbox:local`).
- **Strict Hardening**: Containers run non-root (`user: 65532`), with all Linux capabilities dropped (`--cap-drop=ALL`), `no-new-privileges`, network disabled (`--network=none`), a read-only root filesystem, and transient in-memory tmpfs workspaces (`noexec,nosuid,nodev`).
- **Cryptographic Wire Protocol**: Jobs communicate over stdin/stdout with ephemeral HMAC-SHA256 signatures, single-use credentials, and request digests.
- **Zero Credential Leakage**: Database URLs, AWS credentials, Redis URLs, and Gemini API keys remain strictly in the trusted host broker and never enter the execution container.

### 2. Secure Upload Pipeline & Quarantine Architecture
- **Authenticated Reservation Flow**: Users request an upload reservation generating a scoped, expiring quarantine destination.
- **Signed Storage POST**: Direct browser-to-S3 uploads enforce exact quarantine keys, MIME types, 1–50 MiB bounds, and 15-minute expiry.
- **Antivirus Scanning**: Uploads pass through ClamAV virus scanning (`zINSTREAM` protocol) and magic-byte checks before processing. (An operator-controlled bypass `AIDSO_MALWARE_SCANNER=bypass` is available for environments without a running ClamAV daemon).
- **Atomic Promotion**: Only the exact scanned in-memory bytes are published to permanent `datasets/` storage; unapproved or malicious files never leave quarantine.

### 3. Automated EDA & Feature Engineering
- **Exploratory Data Analysis**: Automatically detects data types (numerical, categorical, datetime, text), missingness, skew, distribution histograms, and correlation matrices.
- **Missing Value Imputation**: Supports Mean, Median, Mode, and K-Nearest Neighbors (KNN) imputation, preserving targets.
- **Feature Transformations**: Log transforms, standardization, and one-hot encoding with automatic correlation comparison against targets.

### 4. AutoML Model Search & Champion Selection
- **Multi-Model Tournament**: Automatically trains and tunes Random Forest, XGBoost, LightGBM, and Neural Networks.
- **Hyperparameter Optimization**: Uses Optuna (`TPESampler`) to optimize hyperparameters per candidate model over validation splits.
- **Strict Leakage Prevention**: Champion selection evaluates validation metrics (Weighted F1 for classification, MSE for regression). Held-out test metrics are kept independent.
- **Complete Pipeline Export**: Downloadable `.pkl` artifacts contain end-to-end scikit-learn `Pipeline` objects bundling preprocessing and estimators, ready to accept raw feature rows.

### 5. Interpretability & Monitoring
- **Local & Global SHAP**: Computes global feature importance and row-level local SHAP explanations (TreeExplainer and Permutation SHAP).
- **Data Drift Detection**: Evaluates baseline vs. production dataset distributions using Population Stability Index (PSI) to alert on feature drift.
- **Interactive Inference**: Real-time single-row prediction and probability scoring directly in the web UI.

### 6. Grounded AI Assistant (Gemini)
- Integrated project assistant powered by Google Gemini (with graceful local fallback summaries if unconfigured).
- Contextually grounded with real project evidence: EDA metrics, candidate model results, HPO trial histories, selection rationale, and timeline events.
- Strict system prompt demarcation prevents prompt injection from untrusted dataset contents.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   React Web Frontend                   │
│         (Vite, Tailwind CSS, Responsive UI)            │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / REST / Cookies
                            ▼
┌────────────────────────────────────────────────────────┐
│              FastAPI Backend (Trusted Broker)          │
│    - Auth & Project Management                         │
│    - Quarantine & ClamAV Stream Inspection             │
│    - Staging Datasets & Discarding Sensitive Env       │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
      Database Queue (PostgreSQL)         │ Docker CLI (stdin/stdout pipe)
               │                          ▼
               ▼                ┌───────────────────────────────┐
┌──────────────────────────────┐│   aidso-sandbox Container     │
│   Background Worker Loop     ││  - Non-root, network: none    │
│ (worker.py / worker/web.py)  ││  - Read-only root + tmpfs     │
│                              ││  - Optuna HPO & ML Training   │
└──────────────┬───────────────┘│  - SHAP Explanations & Drift  │
               │                └───────────────────────────────┘
               ▼
   (Calls Sandbox Broker)
```

---

## Getting Started

### Prerequisites
- **Python**: 3.11 or 3.12
- **Node.js**: 20+ (Node 22 recommended)
- **Docker**: Docker Desktop (with Linux containers)

### Quickstart (Local Development)

1. **Clone and install dependencies**:
   ```powershell
   git clone https://github.com/your-username/ai-data-science-os.git
   cd ai-data-science-os

   # Backend dependencies
   python -m pip install -r backend/requirements.txt

   # Frontend dependencies
   cd frontend
   npm ci
   cd ..
   ```

2. **Build the Sandbox Image**:
   ```powershell
   docker build -f backend/Dockerfile.sandbox -t aidso-sandbox:local backend
   ```

3. **Launch the stack**:
   ```powershell
   ./scripts/start-local.ps1
   ```
   Open **http://127.0.0.1:5176** in your browser.
   * A demo account is automatically seeded in local mode: `dummy_user` / `password123`.

Alternatively, start services in separate terminals:
```powershell
# Terminal 1: Backend API
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# Terminal 2: Training Worker
cd backend
python worker/worker.py

# Terminal 3: Frontend Dev Server
cd frontend
$env:AIDSO_BACKEND_URL = 'http://127.0.0.1:8002'
npm run dev -- --port 5176
```

---

## Docker Compose Setup

Run the full local stack including PostgreSQL, MinIO (S3-compatible storage), ClamAV malware scanning, and isolated sandboxing:

```sh
# 1. Build the execution sandbox image
docker build -f backend/Dockerfile.sandbox -t aidso-sandbox:local backend

# 2. Run Compose with Sandbox and Upload Security overlays
docker compose -f docker-compose.yml -f compose.sandbox.yml -f compose.uploads.yml up --build
```

Access:
- Frontend: `http://localhost:8081`
- Backend API: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001` (user: `minioadmin` / password: `minioadmin`)

---

## Configuration & Environment Variables

Key settings in `backend/.env` (see [`backend/.env.example`](backend/.env.example) for defaults):

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL or SQLite database connection string | `sqlite:///./tmp/aidso_database.db` |
| `ENVIRONMENT` | Environment (`local`, `development`, `production`) | `local` |
| `AIDSO_SANDBOX_IMAGE` | Docker sandbox image tag | `aidso-sandbox:local` |
| `AIDSO_SANDBOX_CPUS` | Maximum CPU cores allocated per sandbox container | `1` |
| `AIDSO_SANDBOX_MEMORY_MB`| Memory limit in MB per container | `1536` |
| `AIDSO_SANDBOX_CONCURRENCY`| Maximum simultaneous container runs | `1` |
| `AIDSO_MALWARE_SCANNER` | Scanner mode (`clamav`, `development`, `bypass`) | `clamav` |
| `CLAMAV_HOST` / `CLAMAV_PORT` | ClamAV daemon connection details | `127.0.0.1` / `3310` |
| `GEMINI_API_KEY` | Optional Google Gemini API key for assistant chat | `""` |
| `S3_ENDPOINT_URL` | S3 / MinIO endpoint | `""` |
| `S3_BUCKET_NAME` | Storage bucket name | `aidso-datasets` |

---

## Testing & Verification

Run the comprehensive test suites:

```powershell
# Backend unit & security tests (from backend/)
cd backend
python -m unittest discover -s tests -v

# Frontend lint & production build (from frontend/)
cd frontend
npm run lint
npm run build
```

* For end-to-end validation, run `python scripts/e2e_workflows.py`.
* For in-depth security documentation and test checklists, refer to:
  * [`SANDBOXING.md`](SANDBOXING.md): Docker execution sandbox isolation boundaries and HMAC verification.
  * [`UPLOAD_SECURITY.md`](UPLOAD_SECURITY.md): Quarantine flow, S3 CORS/lifecycle policies, and ClamAV scanning.
  * [`WORKER_HOSTING.md`](WORKER_HOSTING.md): Web supervisor (`python worker/web.py`) with `/health` and `/ready` endpoints for hosted deployment.
  * [`VERIFICATION.md`](VERIFICATION.md): Audit logs and verification history.

---

## Deployment

Refer to [`DEPLOYMENT.md`](DEPLOYMENT.md) for production guidelines on Render, Railway, or Kubernetes:
- **API Service**: Run `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Worker Service**: Run `python worker/worker.py` (or `python worker/web.py` for cloud platforms requiring a bound HTTP port).
- **Frontend**: Deploy static assets from `frontend/dist` on Vercel, Netlify, or Render Static Sites.
- **Storage & DB**: Managed PostgreSQL and AWS S3 with bucket lifecycle rules (`deploy/s3-quarantine-lifecycle.json`).
