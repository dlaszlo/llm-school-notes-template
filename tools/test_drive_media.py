import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import drive_media as dm

PNG = b'\x89PNG\r\n\x1a\nsynthetic-test-payload'


class FakeDrive:
    def __init__(self):
        self.files = {}; self.content = {}; self.allocations = 0
        self.fail_create = False; self.fail_put = False; self.puts = 0
        self.partial = b''; self.fail_after_chunk = None

    def metadata(self, file_id):
        if file_id not in self.files:
            raise dm.ApiError(404)
        result = copy.deepcopy(self.files[file_id]); data = self.content.get(file_id, b'')
        result.update(size=str(len(data)), md5Checksum=hashlib.md5(data).hexdigest())
        return result

    def download_hash(self, file_id):
        data = self.content[file_id]
        return hashlib.sha256(data).hexdigest(), len(data)

    def request(self, method, url, payload=None, headers=None):
        if 'generateIds' in url:
            self.allocations += 1
            return 200, {}, {'ids': ['file-1']}
        if method == 'POST':
            self.files[payload['id']] = copy.deepcopy(payload)
            if self.fail_create:
                self.fail_create = False
                raise dm.Refused('simulated lost create response')
            return 200, {}, self.metadata(payload['id'])
        if method == 'PATCH':
            return 200, {'Location': dm.UPLOAD + '/files/file-1?upload_id=private-session'}, {}
        if method == 'PUT':
            if headers['Content-Range'].startswith('bytes */'):
                return 308, ({'Range': f'bytes=0-{len(self.partial)-1}'} if self.partial else {}), {}
            self.puts += 1
            start, end, total = map(int, re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', headers['Content-Range']).groups())
            assert start == len(self.partial)
            self.partial += payload
            if end + 1 == total:
                self.content['file-1'] = self.partial
            if self.puts == self.fail_after_chunk:
                raise dm.Refused('simulated interrupted chunk')
            if self.fail_put:
                self.fail_put = False
                raise dm.Refused('simulated lost final upload response')
            if end + 1 == total:
                return 200, {}, self.metadata('file-1')
            return 308, {'Range': f'bytes=0-{end}'}, {}
        raise AssertionError((method, url))


class DriveMediaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.outbox = self.root / 'learner-a'; self.outbox.mkdir()
        self.file = self.outbox / 'test.png'; self.file.write_bytes(PNG)
        self.dest = {'folder_id': 'folder-a', 'outbox': str(self.outbox)}
        self.drive = FakeDrive(); self.ledger = self.root / 'ledger'

    def upload(self):
        return dm.upload(self.drive, self.dest, self.ledger, 'learner-a', 'test-v1', self.file)

    def test_upload_and_repeat_have_same_remote_id(self):
        a, b = self.upload(), self.upload()
        self.assertEqual(a, b); self.assertEqual(self.drive.allocations, 1)
        self.assertEqual(self.drive.puts, 1)
        self.assertEqual(a['sha256'], hashlib.sha256(PNG).hexdigest())

    def test_lost_create_response_does_not_duplicate(self):
        self.drive.fail_create = True
        with self.assertRaises(dm.Refused): self.upload()
        self.assertTrue(self.upload()['verified'])
        self.assertEqual(self.drive.allocations, 1)

    def test_lost_final_response_does_not_repeat_upload(self):
        self.drive.fail_put = True
        with self.assertRaises(dm.Refused): self.upload()
        self.assertTrue(self.upload()['verified'])
        self.assertEqual(self.drive.puts, 1)

    def test_changed_content_cannot_reuse_request(self):
        self.upload(); self.file.write_bytes(PNG + b'changed')
        with self.assertRaises(dm.Refused): self.upload()
        self.assertEqual(self.drive.puts, 1)

    def test_partial_upload_resumes_at_server_offset(self):
        self.drive.fail_after_chunk = 2
        with patch.object(dm, 'CHUNK', 8):
            with self.assertRaises(dm.Refused): self.upload()
            self.assertEqual(len(self.drive.partial), 16)
            self.assertTrue(self.upload()['verified'])
        self.assertEqual(self.drive.content['file-1'], PNG)
        self.assertEqual(self.drive.allocations, 1)

    def test_outside_and_cross_learner_and_symlink_inputs_rejected(self):
        outside = self.root / 'other.png'; outside.write_bytes(PNG)
        with self.assertRaises(dm.Refused): dm.input_bytes(self.dest, outside)
        link = self.outbox / 'link.png'; link.symlink_to(outside)
        with self.assertRaises(dm.Refused): dm.input_bytes(self.dest, link)
        with self.assertRaises(dm.Refused): dm.target({'destinations': {'learner-a': self.dest}}, 'learner-b')

    def test_wrong_remote_parent_or_learner_refused(self):
        self.upload()
        self.drive.files['file-1']['parents'] = ['folder-b']
        with self.assertRaises(dm.Refused): self.upload()
        self.drive.files['file-1']['parents'] = ['folder-a']
        self.drive.files['file-1']['appProperties']['learner'] = 'learner-b'
        with self.assertRaises(dm.Refused): self.upload()

    def test_remote_tampering_fails_full_readback(self):
        self.upload(); self.drive.content['file-1'] = b'corrupted'
        with self.assertRaises(dm.Refused): self.upload()

    def test_upload_session_cannot_send_token_to_other_host(self):
        for url in ['https://evil.example/upload', 'https://www.googleapis.com.evil.example/upload/drive/v3/files', 'http://www.googleapis.com/drive/v3/files']:
            with self.assertRaises(dm.Refused): dm.allowed_url(url)

    def test_range_parser_and_secret_file_permissions(self):
        self.assertEqual(dm.offset_of({'Range':'bytes=0-7'}, 16), 8)
        with self.assertRaises(dm.Refused): dm.offset_of({'Range':'bytes=0-18'}, 16)
        p = self.root / 'state.json'; dm.atomic_json(p, {'safe': True})
        self.assertEqual(p.stat().st_mode & 0o777, 0o600)
        self.assertTrue(dm.private_json(p)['safe'])


if __name__ == '__main__':
    unittest.main()
