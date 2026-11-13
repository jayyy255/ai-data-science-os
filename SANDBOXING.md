# Isolated execution

All dataset parsing/profiling, imputation, feature transformation, training/HPO, model loading, prediction, SHAP, champion inspection and drift computation now run in disposable Docker containers. The API and queue worker are trusted brokers: they check ownership, fetch the required files, request a fixed computation, and persist the result. They never unpickle a model or run a fitted pipeline themselves.

## Start locally

Start Docker Desktop using Linux containers, then run from the repository root:

```powershell
docker build -f backend/Dockerfile.sandbox -t aidso-sandbox:local backend
./scripts/start-local.ps1
```

No environment variables are needed for the default local sandbox image. Rebuild that image after changing compute code or dependencies. API/worker processes need the Docker CLI and permission to use the selected Docker context. The image is not downloaded automatically during a request.

For the Docker Compose development stack:

```sh
docker build -f backend/Dockerfile.sandbox -t aidso-sandbox:local backend
docker compose -f docker-compose.yml -f compose.sandbox.yml up --build
```

The overlay explicitly gives only the trusted API/queue broker access to the Docker socket. Docker control is powerful host access: use a dedicated private execution host (preferably rootless Docker), never expose an unauthenticated Docker daemon, and never mount its socket in execution containers. The sandbox runtime has no host bind mounts at all.

## Per-execution isolation

- Fresh non-root container, user/group 65532, dropped Linux capabilities and `no-new-privileges`.
- Network disabled; default Docker seccomp restrictions retained.
- Read-only image filesystem; bounded, temporary `/work` and `/tmp` filesystems, both `noexec`, `nosuid` and `nodev`.
- Default 1 CPU, 1536 MB memory with no extra swap, 64 PIDs, 128 file descriptors and bounded file sizes. Budget the number of broker processes/services as well as the per-broker concurrency limit.
- Wall timeout: 900 seconds for training, 120 seconds for other operations. CPU time is also limited. Timeout/output violations trigger forced container removal; normal runs use Docker's automatic removal.
- Bounded input, output and logs. Containers receive data over stdin and return JSON plus base64 artifacts; no shared filesystem, cloud URL or general execution command is accepted.
- Only predefined operations are supported. There is no arbitrary Python/shell execution endpoint, including for Gemini output.

## Temporary credentials and environment

Each invocation receives a fresh random job ID, 256-bit random job credential and expiry, delivered over stdin rather than command-line arguments. The result is HMAC-bound to that credential, request digest and job ID. Tokens are not stored in PostgreSQL, artifacts, logs or client responses; they have no reuse endpoint and are discarded after the response is accepted. Failed/expired/badly signed results are rejected.

These are scoped execution credentials, **not AWS STS keys or temporary PostgreSQL accounts**. Jobs need neither: the broker stages the authorized bytes and publishes the resulting artifacts. AWS, database, Redis, Gemini and user-session credentials remain outside the sandbox. This avoids giving model code any cloud/database authority.

The container filesystem and environment are recreated for each operation. Installed dependencies come from an immutable image rather than an internet-enabled per-job `pip install`. Pin the deployed image by digest and keep it updated. Model artifacts are version-sensitive: retain the compatible image or retrain older models after dependency upgrades.

## Deployment configuration

```env
AIDSO_SANDBOX_IMAGE=aidso-sandbox:local
AIDSO_SANDBOX_MEMORY_MB=1536
AIDSO_SANDBOX_CPUS=1
AIDSO_SANDBOX_CONCURRENCY=1
AIDSO_SANDBOX_TRAIN_TIMEOUT=900
AIDSO_SANDBOX_TIMEOUT=120
```

Both the API and queue worker need a Docker-capable execution host with this image installed. A normal Render/Railway application service without access to a Docker engine is insufficient for this execution architecture. Installing a Docker CLI or deploying the API in Docker does not itself provide an engine. Use a private Docker-capable VM/host, or deploy the trusted brokers there. Unsupported/unavailable sandboxes fail closed; there is no in-process fallback.

PostgreSQL/S3 remain the durable control/data stores. Sandboxing does not replace project authorization, host maintenance or backup. Containers share a host kernel, so this is container isolation rather than a microVM boundary. Dataset approval requires ClamAV by default; see UPLOAD_SECURITY.md for quarantine and scanner deployment.

## Assistant evidence

Training persists structured candidate progress, validation/test metrics, HPO trials, selection criteria, bounded redacted process logs and sandbox metadata in the project's training-job record. Automatic selection records the best validation F1 or MSE; test scores do not select the winner. Manual champion selection accepts an optional user reason in the registry and stores it in the timeline.

The assistant receives the current Knowledge Card, candidate comparison, 30 recent timeline entries and up to three recent job histories. Older evidence is trimmed to a bounded prompt budget. Credential values and sensitive fields are redacted, unrelated project/server logs are excluded, and the cache key includes an evidence digest. Log contents are marked as untrusted data in Gemini's system instruction. If older runs lack a reason, the assistant must say so instead of guessing. Gemini still only returns text; no response is executed.

## Verification

```powershell
cd backend
$env:AIDSO_TEST_DOCKER='1'
python -m unittest discover -s tests -v
```

The Docker tests exercise network denial, read-only root, non-root identity, capability removal, environment isolation, fresh temporary filesystems and timeout cleanup. Protocol tests cover unique credentials, signatures and unavailable-backend rejection. Workflow tests cover real sandboxed classification/regression, transformations, predictions, SHAP and drift, plus project-scoped assistant evidence/redaction/cache changes.
