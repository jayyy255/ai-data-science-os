# Local verification - October 12, 2026

The core CSV-to-model workflow passes local checks. This report describes the tested scope; it does not certify a production deployment.

## Automated checks

- Ten isolated backend regression tests passed. They cover account isolation and revoked sessions, CSV validation and project IDs, reversible transformations, four imputation methods, classification and regression pipelines, saved model execution, predictions, explanations, champion selection, downloads, drift persistence, repeatable schema initialization, assistant provider failures, semantic date/text detection, and custom S3 bucket artifact paths.
- Frontend production build passed. Vite reports a large bundle warning; this does not prevent the build.
- Frontend lint passed with no warnings.
- Docker Compose configuration validation passed.

## Repeatable live-process E2E run

`python scripts/e2e_workflows.py` passed 95 checks in approximately 31 seconds. It starts a real HTTP API and background worker with disposable SQLite and artifact directories, and leaves the development database untouched. Machine-readable results are saved to `tmp/e2e-results.json`.

| Feature | Result |
| --- | --- |
| Signup, duplicate signup, invalid login, sessions and logout revocation | Passed |
| Private project, inference, training, chat, monitoring and download access | Passed |
| Classification/regression setup and date/text profiling | Passed |
| Transform, revert, recommendations and exported column changes | Passed |
| Median, Mean, Mode and KNN CSV exports | Passed; predictor missing values filled and targets preserved |
| Queue deduplication, training, four model candidates and five HPO trials per model | Passed |
| All model binaries and signed downloads | Passed; downloaded pipelines execute on raw rows and unknown categories |
| Predictions, probabilities, row explanations and invalid input handling | Passed |
| Champion changes, feature-change invalidation and retraining | Passed |
| Baseline/shifted drift and persistence | Passed |
| Assistant project context with Gemini absent | Passed |
| Failed worker job, API restart and existing session/project persistence | Passed |

The custom S3 bucket download path is also covered with a mocked storage provider in the regression suite; no live cloud credentials were used.

## Browser and runtime checks

- Local services start through `scripts/start-local.ps1`. API, worker, and frontend process IDs are recorded separately.
- Saved login, projects, model artifacts, and champion selection survive a service restart.
- Fresh browser project creation recovered from a missing-target error. Feature override, Save & Train, and monitoring-triggered retraining completed. The downloaded transformed CSV was read back and validated, and exported knowledge-card JSON was parsed and checked against the current project. Login rejection, recovery, logout redirection, project switching, malformed prediction JSON, and subsequent successful inference were checked in the UI.
- EDA distributions and correlation matrices render uploaded data.
- Baseline-versus-baseline monitoring reports HEALTHY, maximum PSI 0.0000, for 180 observations. The shifted CSV also triggered a browser warning with maximum PSI 8.2831 and exposed the working retrain action.
- Regression predictions and SHAP explanations return numeric results in the browser.
- A new browser-triggered regression job completed on the running worker with four trained models, recorded validation HPO trials, updated test metrics, and completed job history.
- System status shows the actual database, artifact storage, and worker heartbeat.
- Assistant provider rejection falls back to an explicitly labeled summary of current project records.

Interactive verification used the connected Codex in-app browser. Chrome was opened during the earlier run, but a Chrome automation connection was not available.

## Configuration still required

- Gemini connectivity is now verified with the configured local key. A disposable project containing only generated data received a live response through the application chat endpoint (HTTP 200, correct row count, no fallback). Existing project context was not sent in this check.
- Password recovery has no email/recovery provider configured and cannot reset passwords through an unauthenticated request.
- Live Docker containers and Render/Railway PostgreSQL/S3 deployments were not exercised. See `DEPLOYMENT.md` for configuration and post-deployment checks.

The app is available at `http://127.0.0.1:5176`, with its API at `http://127.0.0.1:8002/api/health` while the local services remain running.

## Additional fixes found during E2E testing

- Removed the misleading 100% upload indicator and stale validation banner during retries.
- Replaced hardcoded dataset column examples with actual names and implemented date/text profile counts.
- Named model downloads now use the stored artifact path, preserving custom production bucket names and rejecting nonexistent models.
- Transformation selectors have accessible labels.
- Knowledge-card exports use Blob downloads, shared with CSV/model downloads.
- Dashboard cards now show regression MSE and preserve zero-valued scores; overview accuracy uses percentages consistently.

## Gemini configuration verification

Local Gemini initialization now reads `backend/.env` through python-dotenv. Production service environment variables remain authoritative. `AIDSO_LOAD_ENV_FILE=0` isolates regression and E2E tests from the developer's real key. The API was restarted with the corrected loader, and `.env` remains Git-ignored and untracked.

## Public benchmark follow-up

See [PUBLIC_DATASET_RESULTS.md](PUBLIC_DATASET_RESULTS.md) for the three downloaded UCI datasets, EDA/feature engineering checks, optimized before/after metrics, and fixes. New runs perform 20 validation trials across four models; historical three-trial jobs remain recorded as originally executed.

### Liquid blue light and dark themes (2026-10-21)

- Added a header and sign-in appearance toggle with a saved local preference; the initial page uses that preference or the device colour scheme before the app renders.
- Applied the reference-inspired icy blue glass palette to surfaces, typography, inputs, tables, status colours and chart series; retained a midnight blue dark palette.
- Browser checks passed: both themes survive reload; EDA charts render in both palettes; switching themes preserves an uncommitted feature transformation selection (restored after checking).
- At 320px wide, the header fits without page overflow; the navigation drawer traps keyboard focus, closes with Escape and returns focus to its trigger.
- Frontend lint and production build passed. The build retains the existing large JavaScript chunk advisory.
- Visual previews: `tmp/liquid-light-mode.png` and `tmp/liquid-dark-mode.png`.

### Frosted glass and script type refinement (2026-10-21)

- Replaced decorative circles with a local SVG flowing gradient backdrop.
- Main panels now use translucent fills, 28px backdrop blur, saturation, subtle local SVG grain and reflective inset borders in both themes.
- Removed the page opacity animation that isolated panels from the backdrop and prevented the intended blur.
- Added locally hosted Style Script with its OFL license for usernames and project/dataset names across the overview, project cards, dataset page and chat context heading. Data values, forms and navigation keep readable UI fonts.
- Browser checks: light/dark overview and EDA rendering; script names wrap at 320px; header has no overflow at 640px. Reduced-transparency and unsupported-blur fallbacks remain opaque.

### Gemini response formatting (2026-10-21)

- Chat replies and EDA assessments now share a Markdown renderer for bold/emphasis, headings, lists, code, links and tables. User messages remain plain text.
- Raw HTML and remote images are disabled; unsafe link protocols are rejected by the renderer. Code blocks retain their literal formatting characters.
- Server-rendered checks passed for formatted content, code literals, tables, link attributes and unsafe HTML/URLs/images. Frontend lint and production build passed.
- Browser confirmed the chat page mounts the renderer for stored assistant content. No new Gemini request was needed for this change.

### Responsive layout pass (2026-10-28)

- Updated workspace sizing for dynamic mobile viewport heights; compact headers, stacked actions and grid breakpoints preserve usable card widths.
- Chat now has a collapsible project context on smaller screens, a bounded conversation with its own message scroll area, and a usable composer. New messages scroll their history instead of moving the whole workspace.
- Fixed tablet feature-transformation controls, responsive chart headers, mobile authentication padding, row-explanation inputs and wrapped milestone timestamps.
- Data tables, the correlation matrix and feature-importance chart scroll inside their panels. Table regions support keyboard focus. The mobile drawer traps focus, supports Escape and makes background content inert.
- New page navigation resets workspace scroll to the top.
- Browser audited 14 pages at 320, 390, 768, 1024 and 1440px (70 combinations); no body/header/main overflow after charts settled. Checked phone chat context, drawer keyboard focus and dark overview separately. Sign-in was exercised at 390px.
- Frontend lint and production build passed; the existing bundle-size advisory remains.
- Evidence: tmp/responsive-audit.json, tmp/responsive-mobile.png, tmp/responsive-desktop.png.
