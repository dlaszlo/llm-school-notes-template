#!/usr/bin/env python3
"""Upload checked artifacts to configured Drive folders; no sharing/delete API.

Requires Python 3.10+, Linux, and private configured {token,uploader}.json.
This CLI constrains its own operations, not an agent with unrestricted shell access.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

SCOPE = 'https://www.googleapis.com/auth/drive.file'
API = 'https://www.googleapis.com/drive/v3'
UPLOAD = 'https://www.googleapis.com/upload/drive/v3'
CHUNK = 8 * 1024 * 1024
MAX_BYTES = 128 * 1024 * 1024
TAG = 'school-notes-media-v1'
FIELDS = 'id,name,mimeType,parents,size,md5Checksum,webViewLink,trashed,appProperties,shared'


class Refused(Exception):
    pass


class ApiError(Refused):
    def __init__(self, status):
        self.status = status
        super().__init__(f'Google HTTP {status}; credentials and response body omitted. Retry the SAME request ID after resolving the error.')


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.save-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def private_json(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise Refused('Private configuration must be an ordinary mode-0600 file.')
    return json.loads(path.read_text(encoding='utf-8'))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def allowed_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.netloc != 'www.googleapis.com' or not p.path.startswith(('/drive/v3/', '/upload/drive/v3/')):
        raise Refused('Unexpected Google API address.')


class Drive:
    def __init__(self, home):
        self.home = home
        self.opener = urllib.request.build_opener(NoRedirect)
        saved = private_json(home / 'token.json')
        if saved.get('scopes') != [SCOPE]:
            raise Refused('Only drive.file credentials are accepted.')
        form = urllib.parse.urlencode(dict(client_id=saved['client_id'], client_secret=saved['client_secret'], refresh_token=saved['refresh_token'], grant_type='refresh_token')).encode()
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=form)
        try:
            with self.opener.open(req, timeout=60) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code) from None
        except (urllib.error.URLError, TimeoutError):
            raise Refused('Token refresh connection failed.') from None
        if result.get('scope', SCOPE).split() != [SCOPE]:
            raise Refused('Unexpected refreshed scope.')
        self.token = result['access_token']
        saved.update(token=self.token, refresh_token=result.get('refresh_token', saved['refresh_token']), expiry=(dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=result['expires_in'])).strftime('%Y-%m-%dT%H:%M:%SZ'))
        atomic_json(home / 'token.json', saved)

    def request(self, method, url, payload=None, headers=None):
        allowed_url(url)
        h = {'Authorization': 'Bearer ' + self.token}
        h.update(headers or {})
        if isinstance(payload, dict):
            payload = json.dumps(payload).encode()
            h['Content-Type'] = 'application/json; charset=UTF-8'
        req = urllib.request.Request(url, data=payload, headers=h, method=method)
        try:
            response = self.opener.open(req, timeout=90)
        except urllib.error.HTTPError as exc:
            if exc.code != 308:
                raise ApiError(exc.code) from None
            response = exc
        except (urllib.error.URLError, TimeoutError):
            raise Refused('Connection interrupted; keep the SAME request ID to resume.') from None
        with response:
            body = response.read()
            return response.status, response.headers, json.loads(body) if body else {}

    def metadata(self, file_id):
        return self.request('GET', API + '/files/' + urllib.parse.quote(file_id, safe='') + '?' + urllib.parse.urlencode({'fields': FIELDS}))[2]

    def download_hash(self, file_id):
        url = API + '/files/' + urllib.parse.quote(file_id, safe='') + '?alt=media'
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + self.token})
        digest, size = hashlib.sha256(), 0
        try:
            with self.opener.open(req, timeout=90) as response:
                while block := response.read(CHUNK):
                    size += len(block)
                    if size > MAX_BYTES:
                        raise Refused('Remote file exceeds the verified size limit.')
                    digest.update(block)
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code) from None
        except (urllib.error.URLError, TimeoutError):
            raise Refused('Download verification interrupted; retry the SAME request ID.') from None
        return digest.hexdigest(), size


def target(config, learner):
    if learner not in config.get('destinations', {}):
        raise Refused('Unknown learner; no destination selected.')
    dest = config['destinations'][learner]
    if not isinstance(dest, dict) or not re.fullmatch(r'[A-Za-z0-9_-]+', dest.get('folder_id', '')):
        raise Refused('Invalid destination configuration.')
    return dest


def input_bytes(dest, path):
    root = Path(dest['outbox']).expanduser()
    path = path.expanduser().absolute()
    if not root.is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise Refused('Input must be inside this learner\'s configured outbox.')
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise Refused('Symlink input paths are not accepted.')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BYTES:
            raise Refused('Input must be an ordinary, nonempty file of at most 128 MiB.')
        content = stream.read(MAX_BYTES + 1)
    if len(content) != info.st_size:
        raise Refused('Input changed during reading or exceeds the size limit.')
    ext = path.suffix.lower()
    checks = {
        '.png': ('image/png', content.startswith(b'\x89PNG\r\n\x1a\n')),
        '.jpg': ('image/jpeg', content.startswith(b'\xff\xd8\xff')),
        '.jpeg': ('image/jpeg', content.startswith(b'\xff\xd8\xff')),
        '.pdf': ('application/pdf', content.startswith(b'%PDF-')),
        '.mp3': ('audio/mpeg', content.startswith(b'ID3') or (len(content) > 1 and content[0] == 255 and content[1] & 0xe0 == 0xe0)),
        '.wav': ('audio/wav', content.startswith(b'RIFF') and content[8:12] == b'WAVE'),
    }
    if ext not in checks or not checks[ext][1]:
        raise Refused('Only recognizable PNG, JPEG, PDF, MP3 or WAV artifacts are accepted.')
    return content, checks[ext][0]


def folder_check(drive, config, dest):
    folder = drive.metadata(dest['folder_id'])
    if folder.get('trashed') or folder.get('mimeType') != 'application/vnd.google-apps.folder' or folder.get('parents') != [config['parent_id']]:
        raise Refused('Destination moved, trashed or no longer matches the configured parent.')


def owned(meta, record, dest):
    expected = {'managed_by': TAG, 'learner': record['learner'], 'request': record['key'], 'sha256': record['sha256']}
    if meta.get('id') != record['file_id'] or meta.get('parents') != [dest['folder_id']] or meta.get('appProperties') != expected or meta.get('trashed'):
        raise Refused('File does not match this learner\'s managed upload record.')


def receipt(meta, record):
    return {'learner': record['learner'], 'request_id': record['request_id'], 'file_id': record['file_id'], 'name': record['name'], 'url': meta.get('webViewLink') or 'https://drive.google.com/file/d/' + record['file_id'] + '/view', 'sha256': record['sha256'], 'bytes': record['bytes'], 'verified': True, 'shared': meta.get('shared', False), 'sharing_changed': False}


def verify(drive, dest, record):
    meta = drive.metadata(record['file_id']); owned(meta, record, dest)
    digest, size = drive.download_hash(record['file_id'])
    if (digest, size) != (record['sha256'], record['bytes']):
        raise Refused('Remote bytes do not match the recorded artifact.')
    return receipt(meta, record)


def offset_of(headers, total):
    value = headers.get('Range')
    if not value:
        return 0
    match = re.fullmatch(r'bytes=0-(\d+)', value)
    if not match or not 0 < int(match[1]) + 1 <= total:
        raise Refused('Unexpected resumable upload range.')
    return int(match[1]) + 1


def upload(drive, dest, ledger, learner, request_id, path):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,119}', request_id):
        raise Refused('Use a stable ASCII request ID, at most 120 characters.')
    content, mime = input_bytes(dest, path)
    key = hashlib.sha256((learner + '\n' + request_id).encode()).hexdigest()
    record_path = ledger / (key + '.json')
    identity = dict(learner=learner, request_id=request_id, key=key, name=path.name, sha256=hashlib.sha256(content).hexdigest(), bytes=len(content), mime=mime, folder_id=dest['folder_id'])
    if record_path.exists():
        record = private_json(record_path)
        if any(record.get(k) != v for k, v in identity.items()):
            raise Refused('Request ID already belongs to different content or destination. Use a new version ID.')
    else:
        file_id = drive.request('GET', API + '/files/generateIds?count=1&space=drive&type=files')[2]['ids'][0]
        record = dict(identity, file_id=file_id, state='allocated')
        atomic_json(record_path, record)
    if record['state'] == 'verified':
        return verify(drive, dest, record)
    try:
        meta = drive.metadata(record['file_id'])
    except ApiError as exc:
        if exc.status != 404 or record['state'] != 'allocated':
            raise
        props = {'managed_by': TAG, 'learner': learner, 'request': key, 'sha256': record['sha256']}
        meta = drive.request('POST', API + '/files?' + urllib.parse.urlencode({'fields': FIELDS}), {'id': record['file_id'], 'name': path.name, 'mimeType': mime, 'parents': [dest['folder_id']], 'appProperties': props})[2]
    owned(meta, record, dest)
    if int(meta.get('size', 0)) == len(content) and meta.get('md5Checksum') == hashlib.md5(content).hexdigest():
        result = verify(drive, dest, record)
        record.update(state='verified', receipt=result); record.pop('session', None); atomic_json(record_path, record)
        return result
    if int(meta.get('size', 0)) != 0:
        raise Refused('Existing managed file has unexpected content; refusing to overwrite it.')
    record['state'] = 'created'; atomic_json(record_path, record)
    offset = 0
    if record.get('session'):
        try:
            status, headers, _ = drive.request('PUT', record['session'], b'', {'Content-Range': f'bytes */{len(content)}'})
            if status in (200, 201):
                result = verify(drive, dest, record)
                record.update(state='verified', receipt=result); record.pop('session', None); atomic_json(record_path, record)
                return result
            offset = offset_of(headers, len(content))
        except ApiError as exc:
            if exc.status not in (404, 410):
                raise
            record.pop('session', None); atomic_json(record_path, record)
    if not record.get('session'):
        _, headers, _ = drive.request('PATCH', UPLOAD + '/files/' + record['file_id'] + '?uploadType=resumable', {}, {'X-Upload-Content-Type': mime, 'X-Upload-Content-Length': str(len(content))})
        session = headers.get('Location', ''); allowed_url(session)
        record.update(session=session, state='uploading'); atomic_json(record_path, record)
    while offset < len(content):
        end = min(offset + CHUNK, len(content))
        status, headers, _ = drive.request('PUT', record['session'], content[offset:end], {'Content-Type': mime, 'Content-Range': f'bytes {offset}-{end-1}/{len(content)}'})
        if status in (200, 201):
            break
        next_offset = offset_of(headers, len(content))
        if not offset < next_offset <= end:
            raise Refused('Upload did not advance; retry the SAME request ID.')
        offset = next_offset
    result = verify(drive, dest, record)
    record.update(state='verified', receipt=result); record.pop('session', None); atomic_json(record_path, record)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'upload', 'verify'])
    parser.add_argument('--learner', required=True)
    parser.add_argument('--request-id')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--config-dir', type=Path, default=Path(__file__).resolve().parent.parent / '.drive-state', help='Private config/state directory; no global skill required')
    args = parser.parse_args()
    os.umask(0o077)
    home = args.config_dir.expanduser().resolve()
    try:
        config = private_json(home / 'uploader.json')
        dest = target(config, args.learner)
        if args.action in ('upload', 'verify') and not args.request_id:
            raise Refused('--request-id is required.')
        if args.action == 'upload' and not args.file:
            raise Refused('--file is required.')
        if args.action == 'upload':
            input_bytes(dest, args.file)  # Reject outside paths before any Google request.
        with (home / 'uploader.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            drive = Drive(home); folder_check(drive, config, dest)
            ledger = home / 'uploads'
            if args.action == 'upload':
                result = upload(drive, dest, ledger, args.learner, args.request_id, args.file)
            elif args.action == 'verify':
                key = hashlib.sha256((args.learner + '\n' + args.request_id).encode()).hexdigest()
                record = private_json(ledger / (key + '.json'))
                if record.get('learner') != args.learner or record.get('request_id') != args.request_id:
                    raise Refused('Request identity mismatch.')
                result = verify(drive, dest, record)
            else:
                result = {'learner': args.learner, 'folder_id': dest['folder_id'], 'scope': 'drive.file', 'refresh': 'ok', 'parent': 'verified'}
        print(json.dumps(result, ensure_ascii=False))
    except (Refused, OSError, ValueError, KeyError) as exc:
        # Do not leak credential files, resumable-session URLs or provider responses.
        message = str(exc) if isinstance(exc, Refused) else 'Local configuration, state or input is missing or invalid.'
        print(json.dumps({'error': message}), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
