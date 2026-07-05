# AIDSO (AI Data Science OS)

AIDSO is a memory-driven, local-first Operating System for Data Scientists designed to automate data profiling, transformation overrides, hyperparameter optimization (HPO), model registry logging, explainability mapping, and AI assistant grounding.

---

## 1. Current Local Implementation

In the local development environment, the system runs as a multi-service containerized architecture orchestrated via Docker Compose.

### Local Infrastructure Topology
```mermaid
graph TD
    User([Developer / Browser]) -->|HTTP / port 8081| Gateway[Nginx API Gateway & Load Balancer]
    
    Gateway -->|Static Files / /| Frontend[React Client Container]
    Gateway -->|API Routing / /api| Backend[FastAPI Server - Port 8000]
    
    Backend -->|Store Experiments| MLflow[MLflow Server - port 5000]
    Backend -->|Cache & Audits| Redis[(Redis Session Cache)]
    Backend -->|Store Models & CSVs| MinIO[(MinIO S3 Bucket)]
    Backend -->|Write DB Records| Postgres[(PostgreSQL DB)]
    Backend -->|Enqueue HPO Job| Kafka[Kafka Broker - port 9092]
    
    Kafka -->|Poll Job Queue| Worker1[Kafka Worker Thread - Tree Models]
    Kafka -->|Poll Job Queue| Worker2[Kafka Worker Thread - DL/Transformer]
    
    Worker1 -->|Compute Scikit-Learn/Optuna| MLflow
    Worker2 -->|Compute NN/Transformer| MLflow
    Worker1 -->|Update Metrics| Postgres
    Worker2 -->|Update Metrics| Postgres
```

### Local Component Directory
1.  **API Gateway (Nginx)**: Entry point at `http://localhost:8081`. Distributes API requests (`/api/*`) to FastAPI and routes web views.
2.  **React Frontend**: Single Page Application (SPA) built with Vite and Zustand. Polls training statuses and displays benchmarks.
3.  **FastAPI Backend**: Hosts project registration, EDA calculations, transformation overrides, and model downloaders.
4.  **Kafka Message Broker**: Distributes event triggers to the parallel training workers.
5.  **Training Workers**:
    *   **Worker 1**: Trains tree models (XGBoost, LightGBM, Random Forest).
    *   **Worker 2**: Trains neural networks and tabular attention models (Tabular Transformer).
6.  **PostgreSQL**: Stores project definitions, feature choices, timeline audits, user authentication credentials, and refresh tokens.
7.  **Redis**: Handles state locks and caches dataset EDA profiles.
8.  **MinIO**: Local S3 mock storing uploaded datasets and generated pickle binaries.
9.  **MLflow**: Logs parallel runs metrics and architectural parameters.

### How to Run Locally
Ensure Docker Desktop is running, then execute the following commands in the project root:

```bash
# Build and run the entire development stack in the background
docker compose up --build -d

# Check status of all containers
docker compose ps

# (Optional) Scale backend instances to test Gateway Load Balancing
docker compose up --scale backend=3 -d
```

---

## 2. Production MVP Blueprint (Senior Engineer Review)

To transition from the local development setup to a stable, highly affordable (< $10/month) production MVP, we bypass over-engineered cloud clusters and deploy a lean, serverless-aligned stack.

```text
React Client (Vercel)
        ↓
FastAPI Server (Railway)
        ↓
Supabase PostgreSQL  <--->  AWS S3 (datasets/models)
        ↓
Background Worker (Db Polling Queue)
```

### Step 1: Separate Frontend & Backend Deployments
*   **Frontend**: Build the React application using static site generators and deploy it to **Vercel** or Netlify ($0/month).
    *   URL: `https://aidso.vercel.app`
*   **Backend**: Deploy the FastAPI server to **Railway** or Render ($5-$7/month), mapping environment variables to production targets.

### Step 2: Database Migration (PostgreSQL)
*   Remove the local PostgreSQL container.
*   Provision a free-tier **Supabase PostgreSQL** instance.
*   Update the backend connection string in your environment variables:
    ```env
    DATABASE_URL=postgresql://postgres:[password]@db.supabase.co:5432/postgres
    ```

### Step 3: Object Storage Migration (AWS S3)
*   Replace local MinIO with **AWS S3** in production (`keep MinIO locally for development`).
*   Create a production bucket named `aidso-prod` and organize assets into structured directories:
    *   `datasets/` -> Uploaded raw CSV files (e.g. `datasets/project123.csv`).
    *   `models/` -> Trained model pickle binaries (e.g. `models/project123/model.pkl`).
    *   `reports/` -> Text-based training outputs and performance summaries.
    *   `shap/` -> SHAP global and local values.

### Step 4: Database-Backed Training Queue (Killing Kafka in Prod)
To reduce RAM usage, simplify debugging, and eliminate Kafka infrastructure fees in production, replace the Kafka brokers with a database-backed task queue.

1.  **Define Training Jobs Table**:
    ```sql
    CREATE TABLE training_jobs (
        id SERIAL PRIMARY KEY,
        project_id VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        status VARCHAR NOT NULL DEFAULT 'queued', -- queued, running, completed, failed
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        model_type VARCHAR NOT NULL,
        metrics_json JSON,
        artifact_path VARCHAR
    );
    ```
2.  **Define Lightweight Background Worker**:
    Create a separate python script `worker.py` running in a container or background thread that polls for pending jobs:
    ```sql
    -- Atomically select and lock the next pending job in queue
    SELECT * FROM training_jobs 
    WHERE status = 'queued' 
    ORDER BY created_at ASC 
    LIMIT 1;
    ```
3.  **Resume Resumé Note**: Keep your Kafka worker configurations branch separate so you can showcase it as part of your architecture:
    > "Development architecture utilizes a Kafka-based event-driven HPO training pipeline, while production uses a database-backed polling worker to maintain a zero-cost footprint."

### Step 5: Native Metrics Storage (Killing MLflow in Prod)
Instead of running a separate MLflow server 24/7 in production:
*   Log model metrics, hyperparameters, and parameters directly into the PostgreSQL database (`metrics_json` in the `training_jobs` table).
*   Store output metrics charts and feature importance plots as JSON artifacts in **AWS S3**.
*   This keeps tracking metadata fully persistent while avoiding server hosting overhead.

### Step 6: Cost Protection Safeguards
To prevent API token exhaustion and server runtime crashes, enforce strict quotas on the API endpoints:
*   **Max Dataset Size**: Limit file uploads to **50 MB**, **100,000 rows**, and **200 columns** max.
*   **HPO Limits**: Restrict Optuna trials to a maximum of **20 trials** (down from 500) to keep training duration short.
*   **Concurrent Jobs**: Maximize concurrent training executions to **2 concurrent jobs** to prevent memory exhaustion on single-core backend hosts.

### Step 7: Simplified Monitoring Dashboard
Skip Prometheus and Grafana. Instead, log telemetry directly to a `system_metrics` table inside PostgreSQL:
```sql
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_utilization FLOAT,
    ram_usage_mb FLOAT,
    training_duration_seconds FLOAT,
    prediction_latency_ms FLOAT
);
```
Query these rows directly to render health state indicators in the admin panel.

### Step 8: Production Security Setup
*   **JWT Session Lifespan**: Set short-lived `access_token` lifetimes (15 minutes) and longer-lived `refresh_token` lifespans (7 days).
*   **Bcrypt Hashing**: Hash all passwords securely with Bcrypt prior to storage.
*   **Upload Filtering**: Validate that file extensions and MIME headers are strictly `text/csv` before processing.

### Step 9: Gemini API Token Optimization
To minimize LLM billing costs, do not generate the Knowledge Card dynamically on every user page request.
*   **Memoize Output**: Calculate the Knowledge Card ONLY on three events:
    1.  **Dataset Uploaded** (initial feature analysis).
    2.  **Training Finished** (champion selection and model metrics update).
    3.  **User Override Applied** (decision strategy update).
*   **Reuse Cached Records**: Write the output JSON to the `knowledge_cards` table in PostgreSQL and reuse it for all subsequent views, avoiding redundant Generative Language API calls.

### Step 10: Serverless Transitions (AWS Lambda)
Once the production MVP is stable, offload event-driven operations to AWS Lambda to reduce background host load:
*   **S3 Triggers**: Trigger a Lambda function on S3 dataset uploads to validate structure, run null check statistics, and save data health metadata to the database.
*   **Post-Training Triggers**: Trigger a Lambda function on model artifact saves to compile explainability metrics and format reports.
*   **Cron Cleanup**: Run daily Lambdas to delete expired temporary report files and purge inactive guest sessions.
