"""Trusted Docker broker. No cloud/database credentials enter an execution container."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import threading
import time
import uuid

OPERATIONS = frozenset({'train', 'predict', 'explain', 'champion', 'profile', 'validate_csv', 'impute', 'transform', 'monitor', 'probe'})
MAX_INPUT = 72 * 1024 * 1024
MAX_OUTPUT = 96 * 1024 * 1024
MAX_LOG = 256 * 1024
_slots = threading.BoundedSemaphore(max(1, min(4, int(os.getenv('AIDSO_SANDBOX_CONCURRENCY', '1')))))


class SandboxError(RuntimeError):
    pass


def redact(text):
    text = str(text)
    for key, value in os.environ.items():
        if any(word in key for word in ('SECRET', 'TOKEN', 'PASSWORD', 'API_KEY', 'DATABASE_URL', 'AWS_ACCESS_KEY')) and len(value) >= 6:
            text = text.replace(value, '[REDACTED]')
    text = re.sub(r'(?i)(postgres(?:ql)?(?:\+\w+)?://)[^\s]+', r'\1[REDACTED]', text)
    text = re.sub(r'(AIza[\w-]{25,}|AKIA[A-Z0-9]{16}|sk-[\w-]{25,})', '[REDACTED]', text)
    text = re.sub(r'(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|authorization)\s*[:=]\s*(?:bearer\s+)?[^\s,;]+', r'\1=[REDACTED]', text)
    return text


def docker_environment():
    # Explicit Docker client allowlist, not a copy of the application environment.
    allowed = ('PATH', 'SystemRoot', 'WINDIR', 'USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA',
               'TEMP', 'TMP', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_CONFIG', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')
    return {key: os.environ[key] for key in allowed if key in os.environ}


def docker_command(name, timeout):
    image = os.getenv('AIDSO_SANDBOX_IMAGE', 'aidso-sandbox:local')
    memory = int(os.getenv('AIDSO_SANDBOX_MEMORY_MB', '1536'))
    cpu = float(os.getenv('AIDSO_SANDBOX_CPUS', '1'))
    if not 256 <= memory <= 8192 or not .1 <= cpu <= 8:
        raise SandboxError('Invalid sandbox resource limits')
    return ['docker', 'run', '--rm', '--init', '-i', '--pull=never', '--name', name,
            '--network=none', '--read-only', '--user=65532:65532', '--cap-drop=ALL',
            '--security-opt=no-new-privileges:true', '--pids-limit=64', f'--cpus={cpu}',
            f'--memory={memory}m', f'--memory-swap={memory}m',
            '--ulimit=nofile=128:128', '--ulimit=core=0:0', f'--ulimit=cpu={timeout}:{timeout + 1}',
            '--tmpfs=/work:rw,noexec,nosuid,nodev,size=256m,mode=1777',
            '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777',
            '--env=HOME=/work', '--env=TMPDIR=/work', '--env=NUMBA_CACHE_DIR=/work/numba',
            '--env=OMP_NUM_THREADS=1', '--env=OPENBLAS_NUM_THREADS=1', '--env=MKL_NUM_THREADS=1',
            '--env=NUMEXPR_NUM_THREADS=1', '--env=LOKY_MAX_CPU_COUNT=1',
            '--env=PYTHONUNBUFFERED=1', '--env=PYTHONDONTWRITEBYTECODE=1', image]


def _execute(command, request, name, timeout):
    env = docker_environment()
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    except OSError as error:
        raise SandboxError('Docker sandbox is unavailable. Configure a Docker execution host and build Dockerfile.sandbox.') from error
    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()

    def drain(stream, index, limit):
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            if len(buffers[index]) + len(chunk) > limit:
                exceeded.set()
                break
            buffers[index].extend(chunk)

    def feed():
        try:
            process.stdin.write(request)
            process.stdin.close()
        except (OSError, ValueError):
            pass

    threads = [threading.Thread(target=drain, args=(process.stdout, 0, MAX_OUTPUT), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, 1, MAX_LOG), daemon=True),
               threading.Thread(target=feed, daemon=True)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            if exceeded.is_set():
                raise SandboxError('Sandbox exceeded its output/log limit')
            if time.monotonic() > deadline:
                raise SandboxError('Sandbox execution exceeded its wall-clock time limit')
            exceeded.wait(.05)
        for thread in threads:
            thread.join(timeout=2)
        if exceeded.is_set():
            raise SandboxError('Sandbox exceeded its output/log limit')
        if process.returncode:
            # Do not expose Docker host details, credentials, or raw library logs to clients.
            raise SandboxError('Sandbox failed to start or exceeded its resource limits. Check the Docker host and sandbox image.')
        return bytes(buffers[0]), bytes(buffers[1])
    finally:
        # A killed CLI does not kill its container: always explicitly revoke the execution.
        try:
            subprocess.run(['docker', 'rm', '-f', name], env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=2)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def run_operation(operation, payload=None, files=None, with_audit=False):
    if not _slots.acquire(timeout=5):
        raise SandboxError('Sandbox is busy. Retry after the current operation finishes.')
    try:
        return _run_operation(operation, payload, files, with_audit)
    finally:
        _slots.release()


def _run_operation(operation, payload=None, files=None, with_audit=False):
    if operation not in OPERATIONS:
        raise ValueError('Unsupported sandbox operation')
    files = files or {}
    if sum(len(value) for value in files.values()) > MAX_INPUT:
        raise ValueError('Sandbox input exceeds its size limit')
    if any(not re.fullmatch(r'[a-z0-9_.-]{1,64}', key) for key in files):
        raise ValueError('Invalid sandbox input filename')
    timeout = int(os.getenv('AIDSO_SANDBOX_TRAIN_TIMEOUT', '900') if operation == 'train'
                  else os.getenv('AIDSO_SANDBOX_TIMEOUT', '120'))
    if not 1 <= timeout <= 3600:
        raise SandboxError('Invalid sandbox timeout')
    job_id = uuid.uuid4().hex
    credential = secrets.token_urlsafe(32)
    expires_at = time.time() + timeout
    body = {'job_id': job_id, 'operation': operation, 'payload': payload or {}, 'expires_at': expires_at,
            'files': {key: base64.b64encode(value).decode('ascii') for key, value in files.items()}}
    body_bytes = json.dumps(body, allow_nan=False, separators=(',', ':')).encode()
    digest = hashlib.sha256(body_bytes).hexdigest()
    request = json.dumps({'body': body, 'credential': credential, 'request_digest': digest}).encode()
    if len(request) > MAX_INPUT * 2:
        raise ValueError('Sandbox request exceeds its size limit')
    command = docker_command('aidso-job-' + job_id, timeout)
    started = time.monotonic()
    raw, logs = _execute(command, request, 'aidso-job-' + job_id, timeout)
    try:
        response = json.loads(raw)
        signature = response.pop('signature')
        expected = hmac.new(credential.encode(), json.dumps(response, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or response.get('job_id') != job_id or response.get('request_digest') != digest:
            raise ValueError('Invalid sandbox response binding')
        if time.time() > expires_at:
            raise ValueError('Sandbox credential expired')
    except (ValueError, KeyError, TypeError) as error:
        raise SandboxError('Sandbox returned an invalid or expired response') from error
    # Credential lives only for this invocation and is never persisted or returned.
    safe_log = redact(logs.decode('utf-8', errors='replace').replace(credential, '[REDACTED]'))[-12000:]
    credential = None
    audit = {'execution_id': job_id, 'operation': operation, 'backend': 'docker',
             'duration_seconds': round(time.monotonic() - started, 3), 'credential_revoked': True,
             'credential_expires_at': expires_at, 'network': 'none', 'read_only_root': True,
             'memory_mb': int(os.getenv('AIDSO_SANDBOX_MEMORY_MB', '1536')),
             'cpus': float(os.getenv('AIDSO_SANDBOX_CPUS', '1')),
             'log_tail': safe_log}
    if not response.get('ok'):
        if response.get('error_type') in ('ValueError', 'TypeError', 'KeyError'):
            error = ValueError(redact(response.get('error', 'Invalid input'))[:1000])
        else:
            error = SandboxError('Isolated computation failed: ' + redact(response.get('error', 'Execution failed'))[:1000])
        error.audit = audit
        raise error
    result = response['result']
    artifacts = {}
    for key, value in response.get('artifacts', {}).items():
        if not re.fullmatch(r'[a-z0-9_.-]{1,64}', key):
            raise SandboxError('Invalid sandbox artifact name')
        artifacts[key] = base64.b64decode(value, validate=True)
    return (result, artifacts, audit) if with_audit else result
