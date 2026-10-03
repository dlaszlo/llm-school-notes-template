"""Drive API client for v2 (plan 4.1): full `drive` scope, built on tools/drive_media.Drive.

Errors map to plan 8.1: a rejected refresh token is a missing prerequisite, 429/5xx/403 and
network failures are transient, other 4xx need the owner.
"""

import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Protocol

from ..sources.toolload import load_tool
from ..state.errors import NeedsOwner, Prerequisite, Transient

FULL_SCOPE = "https://www.googleapis.com/auth/drive"
API = "https://www.googleapis.com/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
FIELDS = "id,name,mimeType,parents,size,md5Checksum,createdTime,modifiedTime,description,trashed"
CHUNK = 1024 * 1024


class FileChanged(Transient):
    """A listed file no longer matches Drive (size/MD5 differ, or it is gone): the package
    changed after the listing. The run drops only this package; it waits on Drive (4.1)."""


class Transport(Protocol):
    """What the client needs from the wire; the fake Drive in the tests implements it too."""

    def request(self, method: str, url: str, payload=None, headers=None) -> tuple: ...

    def stream(self, url: str, timeout: float): ...


class DriveMediaTransport:
    """Production transport: drive_media.Drive does the token refresh and the requests."""

    def __init__(self, secrets_dir: Path, timeout_s: float, token_name: str = "drive-token.json",
                 tools_dir: Path | None = None):
        dm = load_tool("drive_media", tools_dir)
        self.dm = dm
        try:
            self.drive = dm.Drive(Path(secrets_dir), scope=FULL_SCOPE, token_name=token_name,
                                  timeout=timeout_s)
        except dm.ApiError as exc:
            # The token endpoint answers 400/401 (invalid_grant) for a revoked or expired grant.
            if exc.status in (400, 401):
                raise Prerequisite("the Drive token was rejected (invalid_grant)",
                                   todo="renew the Drive token (owner consent)") from None
            raise _mapped(exc.status) from None
        except FileNotFoundError:
            raise Prerequisite("the Drive token is missing", todo="create the Drive token") from None
        except dm.Refused as exc:
            if "credentials" in str(exc) or "Private configuration" in str(exc):
                raise Prerequisite(f"Drive token unusable: {exc}",
                                   todo="renew the Drive token with the full drive scope") from None
            raise Transient(f"Drive token refresh: {exc}") from None

    def request(self, method, url, payload=None, headers=None):
        try:
            return self.drive.request(method, url, payload, headers)
        except self.dm.ApiError as exc:
            raise _mapped(exc.status) from None
        except self.dm.Refused as exc:
            raise Transient(f"Drive connection: {exc}") from None

    def stream(self, url, timeout):
        self.dm.allowed_url(url)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.drive.token})
        try:
            return self.drive.opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise _mapped(exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Transient("Drive download connection failed") from None


def _mapped(status: int) -> Exception:
    if status == 429 or status >= 500 or status == 403:
        # Drive reports rate limits as 403 too; the bounded retry turns a real 403 into
        # needs-owner after three runs anyway.
        return Transient(f"Drive HTTP {status}")
    if status == 401:
        return Prerequisite("the Drive token was rejected (HTTP 401)", todo="renew the Drive token")
    return NeedsOwner(f"Drive HTTP {status}", todo="check the Drive folder structure")


class DriveClient:
    def __init__(self, transport: Transport, download_timeout_s: float = 1200):
        self.t = transport
        self.download_timeout_s = download_timeout_s

    def get(self, file_id: str) -> dict:
        url = f"{API}/files/{_q(file_id)}?" + urllib.parse.urlencode({"fields": FIELDS})
        return self.t.request("GET", url)[2]

    def list_children(self, folder_id: str) -> list[dict]:
        items, token = [], None
        while True:
            params = {"q": f"'{folder_id}' in parents and trashed = false",
                      "fields": f"nextPageToken,files({FIELDS})", "pageSize": "1000",
                      "orderBy": "name"}
            if token:
                params["pageToken"] = token
            body = self.t.request("GET", f"{API}/files?" + urllib.parse.urlencode(params))[2]
            items += body.get("files", [])
            token = body.get("nextPageToken")
            if not token:
                return items

    def download(self, item: dict, dest: Path, deadline: float | None = None) -> str:
        """Download to `dest` (via a .part file); verify size and MD5; return the SHA-256.

        `deadline` (time.monotonic) bounds the whole package, not just one read (8.5)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
        url = f"{API}/files/{_q(item['id'])}?alt=media"
        try:
            response = self.t.stream(url, self.download_timeout_s)
        except NeedsOwner as exc:
            if "404" in str(exc):
                raise FileChanged(f"{item['name']!r} is no longer on Drive") from None
            raise
        with response, open(part, "wb") as out:
            while block := response.read(CHUNK):
                if deadline is not None and time.monotonic() > deadline:
                    raise Transient("the package download ran out of time")
                size += len(block)
                sha.update(block)
                md5.update(block)
                out.write(block)
        if str(size) != str(item.get("size")) or md5.hexdigest() != item.get("md5Checksum"):
            part.unlink()
            raise FileChanged(f"download of {item['name']!r} does not match Drive size/MD5")
        part.replace(dest)
        return sha.hexdigest()

    def move(self, file_id: str, add_parent: str, remove_parent: str) -> dict:
        params = {"addParents": add_parent, "removeParents": remove_parent, "fields": FIELDS}
        url = f"{API}/files/{_q(file_id)}?" + urllib.parse.urlencode(params)
        return self.t.request("PATCH", url, {})[2]


def _q(file_id: str) -> str:
    return urllib.parse.quote(file_id, safe="")
