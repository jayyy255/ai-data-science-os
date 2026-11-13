"""Security contract tests, plus real Docker isolation/cleanup probes."""
import hashlib
import hmac
import json
import os
import subprocess
import unittest
from unittest.mock import patch
from services.sandbox import SandboxError, docker_command, docker_environment, run_operation


class SandboxProtocolTests(unittest.TestCase):
    def test_command_enforces_boundaries_and_inherits_no_app_secrets(self):
        command = docker_command('aidso-job-test', 120)
        for flag in ('--network=none', '--read-only', '--user=65532:65532', '--cap-drop=ALL',
                     '--security-opt=no-new-privileges:true', '--pids-limit=64', '--pull=never'):
            self.assertIn(flag, command)
        self.assertFalse(any('mount' in argument or 'volume' in argument for argument in command))
        with patch.dict(os.environ, {'DATABASE_URL': 'test-secret', 'AWS_SECRET_ACCESS_KEY': 'test-secret', 'GEMINI_API_KEY': 'test-secret'}):
            self.assertNotIn('DATABASE_URL', docker_environment())
            self.assertNotIn('AWS_SECRET_ACCESS_KEY', docker_environment())
            self.assertNotIn('GEMINI_API_KEY', docker_environment())

    def test_single_use_credentials_and_response_binding(self):
        credentials, job_ids = [], []
        def execute(command, raw, name, timeout):
            request = json.loads(raw)
            credentials.append(request['credential'])
            job_ids.append(request['body']['job_id'])
            response = {'job_id': job_ids[-1], 'request_digest': request['request_digest'], 'ok': True, 'result': {'valid': True}, 'artifacts': {}}
            response['signature'] = hmac.new(credentials[-1].encode(), json.dumps(response, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
            return json.dumps(response).encode(), credentials[-1].encode()
        with patch('services.sandbox._execute', side_effect=execute):
            for _ in range(2):
                result, _, audit = run_operation('validate_csv', files={'dataset.csv': b'x\n1'}, with_audit=True)
                self.assertTrue(result['valid'])
                self.assertNotIn(credentials[-1], json.dumps(audit))
                self.assertTrue(audit['credential_revoked'])
        self.assertEqual(len(set(credentials)), 2)
        self.assertEqual(len(set(job_ids)), 2)

    def test_invalid_output_and_unsupported_execution_fail_closed(self):
        with self.assertRaises(ValueError):
            run_operation('shell', {'command': 'whoami'})
        with self.assertRaises(ValueError):
            run_operation('predict', files={'../outside': b'data'})
        with patch('services.sandbox._execute', return_value=(b'{"signature":"forged"}', b'')):
            with self.assertRaises(SandboxError):
                run_operation('probe')

    def test_expired_and_cross_job_responses_are_rejected(self):
        def response_for(raw, change_job=False):
            request = json.loads(raw)
            response = {'job_id': 'different-job' if change_job else request['body']['job_id'],
                        'request_digest': request['request_digest'], 'ok': True, 'result': {}, 'artifacts': {}}
            response['signature'] = hmac.new(request['credential'].encode(), json.dumps(response, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
            return json.dumps(response).encode(), b''
        with patch('services.sandbox._execute', side_effect=lambda command, raw, name, timeout: response_for(raw, True)):
            with self.assertRaises(SandboxError):
                run_operation('probe')
        with patch('services.sandbox._execute', side_effect=lambda command, raw, name, timeout: response_for(raw)), patch('services.sandbox.time.time', side_effect=[100, 10000]):
            with self.assertRaises(SandboxError):
                run_operation('probe')
        with patch('services.sandbox.subprocess.Popen', side_effect=FileNotFoundError):
            with self.assertRaises(SandboxError):
                run_operation('probe')


@unittest.skipUnless(os.getenv('AIDSO_TEST_DOCKER') == '1', 'Set AIDSO_TEST_DOCKER=1 to run real container security tests')
class DockerSandboxTests(unittest.TestCase):
    def test_network_filesystem_identity_and_temporary_environment(self):
        with patch.dict(os.environ, {'AWS_SECRET_ACCESS_KEY': 'must-not-leak', 'DATABASE_URL': 'must-not-leak', 'GEMINI_API_KEY': 'must-not-leak'}):
            first = run_operation('probe')
            second = run_operation('probe')
        for result in (first, second):
            self.assertEqual(result['uid'], 65532)
            self.assertTrue(result['network_blocked'])
            self.assertTrue(result['read_only_root'])
            self.assertFalse(result['prior_marker'])
            self.assertNotIn('AWS_SECRET_ACCESS_KEY', result['environment_keys'])
            self.assertNotIn('DATABASE_URL', result['environment_keys'])
            self.assertIn('NoNewPrivs:\t1', result['status'])
            self.assertIn('CapEff:\t0000000000000000', result['status'])
        self.assertNotEqual(first['working_directory'], second['working_directory'])

    def test_timeout_removes_the_container(self):
        names = []
        original = docker_command
        def capture(name, timeout):
            names.append(name)
            return original(name, timeout)
        with patch('services.sandbox.docker_command', side_effect=capture), patch.dict(os.environ, {'AIDSO_SANDBOX_TIMEOUT': '1'}):
            with self.assertRaisesRegex(SandboxError, 'time limit'):
                run_operation('probe', {'sleep_seconds': 5})
        inspection = subprocess.run(['docker', 'inspect', names[0]], capture_output=True, env=docker_environment())
        self.assertNotEqual(inspection.returncode, 0)
