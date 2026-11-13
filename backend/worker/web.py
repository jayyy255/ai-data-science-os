"""Optional worker supervisor with an HTTP port for web-service hosting."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class WorkerState:
    def __init__(self):
        self.child = None
        self.stopping = False
        self.lock = threading.Lock()
        self.checked_at = 0
        self.execution_ready = False

    def alive(self):
        return not self.stopping and self.child is not None and self.child.poll() is None

    def ready(self):
        if not self.alive():
            return False
        # Cache both success and failure to bound work on this public endpoint.
        with self.lock:
            if time.monotonic() - self.checked_at >= 30:
                from services.sandbox import docker_environment
                try:
                    result = subprocess.run(['docker', 'image', 'inspect',
                        os.getenv('AIDSO_SANDBOX_IMAGE', 'aidso-sandbox:local')],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=5, env=docker_environment())
                    self.execution_ready = result.returncode == 0
                except (OSError, subprocess.TimeoutExpired):
                    self.execution_ready = False
                self.checked_at = time.monotonic()
        return self.alive() and self.execution_ready


def make_server(port, state, host='0.0.0.0'):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ('/', '/health'):
                ok = state.alive()
                body = {'worker_process': 'running' if ok else 'unavailable',
                        'check': 'liveness', 'execution_checked': False}
            elif self.path == '/ready':
                ok = state.ready()
                body = {'check': 'execution_prerequisites', 'ready': ok,
                        'worker_process': 'running' if state.alive() else 'unavailable',
                        'docker_engine_and_image': 'available' if state.execution_ready else 'unavailable',
                        'note': 'Database, storage access and successful training are not verified by this endpoint.'}
            else:
                self.send_error(404)
                return
            encoded = json.dumps(body).encode()
            self.send_response(200 if ok else 503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)


def main():
    state = WorkerState()
    server = make_server(int(os.getenv('PORT', '10000')), state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f'Worker health endpoint listening on 0.0.0.0:{server.server_port}', flush=True)

    def shutdown(signum, frame):
        state.stopping = True
        if state.child is not None and state.child.poll() is None:
            state.child.terminate()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        if state.stopping:
            return 0
        state.child = subprocess.Popen([sys.executable, '-u', str(ROOT / 'worker' / 'worker.py')], cwd=str(ROOT))
        while state.child.poll() is None:
            if state.stopping:
                try:
                    state.child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    state.child.kill()
                    state.child.wait()
            else:
                time.sleep(.25)
        return 0 if state.stopping else (state.child.returncode or 0)
    finally:
        state.stopping = True
        if state.child is not None and state.child.poll() is None:
            state.child.terminate()
            try:
                state.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                state.child.kill()
                state.child.wait()
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
