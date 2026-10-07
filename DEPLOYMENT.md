# Render and Railway deployment

Deploy the frontend, API, and training worker as separate services from this repository. The worker and API must share PostgreSQL and the same S3 bucket. SQLite and local artifact folders are for local development.

## Service folders and commands

| Service | Root directory | Build | Start / publish |
| --- | --- | --- | --- |
| Render static frontend | `frontend` | `npm ci && npm run build` | Publish directory: `dist` |
| Render API web service | `backend` | `pip install -r requirements.txt` | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Render background worker | `backend` | `pip install -r requirements.txt` | `python worker/worker.py` |
| Railway frontend | `/frontend` | Existing Dockerfile | Nginx; set `PORT=80`, domain target port `80` |
| Railway API | `/backend` | Existing Dockerfile | Override: `/bin/sh -c 'exec uvicorn main:app --host 0.0.0.0 --port "$PORT"'` |
| Railway worker | `/backend` | Existing Dockerfile | Override: `python worker/worker.py`; no public domain |

Use `/api/health` as the API health check. Use Python 3.11 or 3.12 for native Python builds; the Dockerfile supplies its own Python runtime. Use Node 22 for native frontend builds. Do not launch the Vite development server in production.

## API and worker environment

Set the following on both services:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
AWS_REGION=YOUR_BUCKET_REGION
S3_BUCKET=YOUR_EXISTING_PRIVATE_BUCKET
```

Optional shared configuration:

```env
GEMINI_API_KEY=YOUR_GEMINI_KEY
REDIS_URL=redis://USER:PASSWORD@HOST:6379/0
```

Set the following on the API:

```env
CORS_ORIGINS=https://YOUR_FRONTEND_DOMAIN
```

Multiple frontend origins can be comma-separated, without trailing slashes. Production cookies use Secure and SameSite=None. The frontend also sends its stored session token in the Authorization header, supporting environments that block third-party cookies.

On Railway, if your PostgreSQL service is named `Postgres`, set `DATABASE_URL` to `${{Postgres.DATABASE_URL}}` on the API and worker. On Render, use the database's internal connection URL when the services share a region/network.

Create the private S3 bucket first. Its credentials need object read/write/delete access under `datasets/`, `models/`, and `reports/`. The application performs upload/download through its API, so the main UI does not require public S3 access or browser S3 CORS. Leave `MINIO_ENDPOINT` unset in production. Redis and Gemini are optional; database persistence and S3 are required for independent production services.

## Frontend environment

```env
VITE_API_BASE_URL=https://YOUR_API_DOMAIN/api
```

This is a public API URL, not a secret. Vite embeds it at build time, so rebuild the frontend when it changes. The frontend Dockerfile declares the corresponding build ARG for Railway builds. Do not put AWS or Gemini credentials in frontend variables.

The `gateway/` folder and `docker-compose.yml` are for the local Docker stack; they are not additional services required by these deployments. The training queue uses PostgreSQL, and results are stored in PostgreSQL/S3. Kafka and MLflow are not runtime dependencies of the repaired workflow.

## Verification after deployment

1. Check the API's `/api/health` endpoint.
2. Create an account and upload a small CSV containing a valid target column.
3. Start training and confirm it finishes in the training history. A job that remains queued usually means the worker is stopped or uses a different database.
4. Download a trained pipeline and run predictions with the original predictor columns.
5. Verify a second account cannot access the first account's projects.

The API and worker initialize/upgrade the schema on startup. Deploy one API and one worker initially. Password recovery requires an administrator workflow; an unauthenticated email request does not reset a password. Gemini responses use local project summaries when its API key is absent.

Official references: [Render monorepo support](https://render.com/docs/monorepo-support), [Render background workers](https://render.com/docs/background-workers), [Railway monorepos](https://docs.railway.com/guides/deploying-a-monorepo), [Railway start commands](https://docs.railway.com/deployments/start-command).
