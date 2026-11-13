# Worker HTTP port

The port-scan error occurs when the worker is configured as a Render Web Service but runs the queue loop without an HTTP listener.

For that existing Web Service, use:

- Root directory: backend
- Build command: pip install -r requirements.txt
- Start command: python worker/web.py
- Health check path: /health
- Port: leave Render's PORT variable as provided (typically 10000).

The supervisor binds 0.0.0.0:$PORT and starts exactly one database worker. It forwards termination and exits if the child exits. /health reports only whether that worker process is alive. /ready additionally checks Docker engine connectivity and the configured sandbox image, cached for 30 seconds. No secrets, job IDs or user data are exposed. Neither endpoint proves database/storage health or successful training. /ready does not launch a training job.

This solves port detection only. The current training code still requires a private Docker-capable execution host, the sandbox image, and configured PostgreSQL/S3. A native Render Python Web Service has no Docker engine merely because it exposes a port. Keep sandboxing enabled; do not treat a green /health as a successful end-to-end deployment. Host the broker/worker on a private Docker-capable host, or provide a properly secured supported Docker context with a compatible CLI and image. API uploads separately require the private ClamAV daemon.

Render free Web Services can spin down after 15 minutes without inbound traffic. Queue polling is outbound and does not keep one awake. This makes that service type unsuitable for reliable continuous background processing, even after the port issue is fixed. Do not use artificial keepalive traffic as a substitute for an appropriate execution host.

The existing render.yaml continues to describe a true Background Worker using python worker/worker.py, which does not need a web port. The web supervisor is an alternative for the manually configured Web Service, not a change of service type in that blueprint.

References: https://render.com/docs/web-services and https://render.com/docs/free
