import json
import threading
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import Mock, patch
from worker.web import WorkerState, make_server, main


class WorkerWebTests(unittest.TestCase):
    def setUp(self):
        self.state = WorkerState()
        self.state.child = Mock()
        self.state.child.poll.return_value = None
        self.server = make_server(0, self.state, host='127.0.0.1')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def get(self, path):
        try:
            response = urlopen(f'http://127.0.0.1:{self.server.server_port}{path}', timeout=10)
        except HTTPError as error:
            response = error
        return response.status, json.loads(response.read())

    def test_liveness_tracks_worker_and_shutdown(self):
        self.assertEqual(self.get('/health')[0], 200)
        self.state.child.poll.return_value = 1
        self.assertEqual(self.get('/health')[0], 503)
        self.state.child.poll.return_value = None
        self.state.stopping = True
        self.assertEqual(self.get('/health')[0], 503)

    def test_ready_requires_docker_and_image_but_liveness_does_not(self):
        with patch('worker.web.subprocess.run', side_effect=FileNotFoundError) as docker:
            code, body = self.get('/ready')
            self.assertEqual(code, 503)
            self.assertFalse(body['ready'])
            self.get('/ready')
            self.assertEqual(docker.call_count, 1)
        self.assertEqual(self.get('/health')[0], 200)

    def test_ready_success_is_cached_and_child_exit_overrides_cache(self):
        with patch('worker.web.subprocess.run', return_value=Mock(returncode=0)) as docker:
            self.assertEqual(self.get('/ready')[0], 200)
            self.assertEqual(self.get('/ready')[0], 200)
            self.assertEqual(docker.call_count, 1)
            self.state.child.poll.return_value = 2
            self.assertEqual(self.get('/ready')[0], 503)


class SupervisorTests(unittest.TestCase):
    def test_child_exit_stops_health_server_and_preserves_exit_code(self):
        server = Mock()
        server.server_port = 12345
        child = Mock()
        child.poll.side_effect = [7, 7]
        child.returncode = 7
        with patch('worker.web.make_server', return_value=server), patch('worker.web.signal.signal'), patch('worker.web.subprocess.Popen', return_value=child) as launch:
            self.assertEqual(main(), 7)
        self.assertTrue(launch.call_args.args[0][-1].endswith('worker.py'))
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()

    def test_startup_failure_closes_listener(self):
        server = Mock()
        with patch('worker.web.make_server', return_value=server), patch('worker.web.signal.signal'), patch('worker.web.subprocess.Popen', side_effect=OSError):
            with self.assertRaises(OSError):
                main()
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()
