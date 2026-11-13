"""Single-use stdin/stdout protocol. This process has no application credentials."""
import base64
import contextlib
import hashlib
import hmac
import json
import os
import resource
import sys
import tempfile
import time


def main():
    wire = sys.stdout
    request = json.loads(sys.stdin.buffer.read(150 * 1024 * 1024))
    body = request['body']
    credential = request['credential']
    digest = hashlib.sha256(json.dumps(body, allow_nan=False, separators=(',', ':')).encode()).hexdigest()
    response = {'job_id': body['job_id'], 'request_digest': digest}
    try:
        if digest != request['request_digest'] or time.time() >= body['expires_at']:
            raise ValueError('Invalid or expired job credential')
        resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 * 1024, 128 * 1024 * 1024))
        # No mounts, services, database URL, cloud credentials, or code supplied by users.
        with tempfile.TemporaryDirectory(prefix='job-', dir='/work') as workspace:
            os.chdir(workspace)
            os.environ['HOME'] = workspace
            from sandbox.operations import execute
            files = {key: base64.b64decode(value, validate=True) for key, value in body['files'].items()}
            with contextlib.redirect_stdout(sys.stderr):
                result, artifacts = execute(body['operation'], body['payload'], files)
            response.update(ok=True, result=result, artifacts={key: base64.b64encode(value).decode('ascii') for key, value in artifacts.items()})
    except Exception as error:
        response.update(ok=False, error_type=type(error).__name__, error=str(error)[:1000])
    signature_bytes = json.dumps(response, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    response['signature'] = hmac.new(credential.encode(), signature_bytes, hashlib.sha256).hexdigest()
    credential = None
    wire.write(json.dumps(response, allow_nan=False))
    wire.flush()


if __name__ == '__main__':
    main()
