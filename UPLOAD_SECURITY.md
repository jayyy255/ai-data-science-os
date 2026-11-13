# Dataset upload approval

Uploads now follow: authenticated reservation -> private quarantine -> bounded download -> ClamAV -> isolated CSV validation/profile -> publish scanned bytes under a fresh datasets/ key -> consume reservation. Both direct API files and browser storage uploads take this path. Existing approved projects remain usable.

The frontend uses signed POST forms. S3 enforces an exact quarantine key, text/csv form content type, 1–50 MiB payload and 15-minute expiry. MIME is only a transport restriction; content is independently checked. Local fallback uses an authenticated bounded upload endpoint. Reservations are stored in dataset_uploads, scoped to the user, expire, are claimed atomically, and cannot be reused to create another project. Each user can issue at most 50 reservations per hour (best-effort application limit, not a distributed quota). Approved records retain SHA256, scanner type, timestamp and destination. A failed scan, scanner error, invalid CSV or excess row/column count cannot publish a dataset. Scanner failures return HTTP 503; retry by uploading again.

Only the exact in-memory bytes scanned are published. The approved key is never exposed through an upload signature. A signed POST remains reusable until expiry, but replay only affects quarantine; it cannot replace an approved dataset. No cloud credentials are sent to the browser or compute container.

## Start the scanner and app

```sh
docker build -f backend/Dockerfile.sandbox -t aidso-sandbox:local backend
docker compose -f docker-compose.yml -f compose.sandbox.yml -f compose.uploads.yml up --build
```

ClamAV downloads/updates signatures and can take several minutes to become healthy. Its TCP port is private and unauthenticated: never expose it publicly. The provided configuration rejects files exceeding engine limits and refuses databases older than seven days. Allow outbound signature updates; monitor updater/scanner health. Budget scanner memory separately from training. The compose overlay pins the verified scanner image digest. Update and retest that digest regularly.

For a native API, point these variables to a reachable private daemon:

```env
AIDSO_MALWARE_SCANNER=clamav
CLAMAV_HOST=your-private-scanner-host
CLAMAV_PORT=3310
```

Default mode in code is clamav in every environment. The current Render template explicitly selects bypass temporarily at the owner's request. Local tests explicitly use AIDSO_MALWARE_SCANNER=development; that EICAR-only stub is forbidden outside ENVIRONMENT=local. Do not deploy with ENVIRONMENT=local. The scanner does not need S3/database credentials. Docker sandbox execution is still required for parsing and profiling.

MinIO direct browser uploads require MINIO_PUBLIC_ENDPOINT to be browser-reachable; the compose overlay defaults to http://localhost:9000. Set the actual HTTPS endpoint for remote use. Native local fallback needs no object-store CORS.

## S3 configuration to apply before rollout

Keep Block Public Access enabled and bucket access private, require TLS, and enable server-side encryption. Give only the API broker the required PutObject/GetObject/DeleteObject permissions for quarantine/ and approved artifact prefixes; browsers get only the signed POST. Do not expose quarantine through public bucket policies, CDN origins or download endpoints.

Merge deploy/s3-quarantine-lifecycle.json into the bucket's existing lifecycle rules (do not replace unrelated rules). It deletes abandoned/replayed quarantine objects after one day, including old versions when versioning is enabled. Merge deploy/s3-cors.example.json after replacing the frontend origin. Allow POST for the new form upload flow. These files are templates, not automatically applied cloud changes.

Run `cd backend && python scripts/cleanup_uploads.py` hourly for local/MinIO cleanup and failed delete retries. Keep the S3 lifecycle as a backstop for client replays, crashes, and objects never finalized. Metadata records are retained as an audit trail; set your own retention policy. Schema initialization creates the new table at startup; deploy with database migration rights and backup first.

ClamAV and CSV checks reduce risk; they do not prove a dataset harmless, sanitize spreadsheet formulas on exports, or assess data quality/privacy. Containers remain the boundary for parsing untrusted content. New uploads require rescanning; old datasets are not retroactively rescanned.

## Verify

From backend, run `python -m unittest discover -s tests -p test_upload_security.py -v`. Set AIDSO_TEST_CLAMAV=1 and CLAMAV_HOST/PORT for a real daemon test (clean CSV plus harmless EICAR). Workflow tests also exercise reservation ownership, local upload, actual isolated profiling, promotion and replay rejection. Run frontend lint/build after UI changes.

Implementation references: [S3 POST policy constraints](https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html), [ClamAV stream protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html).

## Temporary scanner bypass (owner requested)

Set AIDSO_MALWARE_SCANNER=bypass on the API and restart/redeploy it to approve otherwise valid CSV uploads without contacting ClamAV. This works in production. CSV/file limits, ownership, quarantine reservations and Docker isolation remain enforced. Upload records retain scan_engine=bypass, EDA metadata explicitly says malware_scan=skipped, and /api/system reports the bypass. Files are not malware-scanned in this mode. There is no automatic fallback from clamav mode to bypass.

When a scanner is ready, change the variable back to clamav, configure CLAMAV_HOST/PORT and restart the API. Existing bypass-approved files are not automatically rescanned. Expired/rejected upload reservations require a fresh upload; this setting does not mass-promote arbitrary objects already in quarantine. The Render template currently uses bypass; manual services need the dashboard variable set explicitly.
