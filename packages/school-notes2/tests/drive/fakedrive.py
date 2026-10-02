import hashlib
import io
import itertools
import urllib.parse
from datetime import datetime, timedelta, timezone

from school_notes2.drive.client import FOLDER
from school_notes2.state.errors import Transient

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


def stamp(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class FakeDrive:
    """In-process Drive v3: enough of files.list/get/update/alt=media for the tool."""

    def __init__(self, page_size: int = 2):
        self.items, self.content = {}, {}
        self.ids = itertools.count(1)
        self.page_size = page_size
        self.patches = []
        self.lose_patch_answer = False

    def folder(self, name, parent=None, minutes_ago=60):
        return self._add(name, parent, FOLDER, None, minutes_ago, minutes_ago)

    def file(self, name, parent, data=b"x", created_ago=60, modified_ago=None, mime="image/jpeg"):
        modified_ago = created_ago if modified_ago is None else modified_ago
        return self._add(name, parent, mime, data, created_ago, modified_ago)

    def _add(self, name, parent, mime, data, created_ago, modified_ago):
        fid = f"id{next(self.ids)}"
        meta = {"id": fid, "name": name, "mimeType": mime, "parents": [parent] if parent else [],
                "createdTime": stamp(created_ago), "modifiedTime": stamp(modified_ago)}
        if data is not None:
            meta.update(size=str(len(data)), md5Checksum=hashlib.md5(data).hexdigest())
            self.content[fid] = data
        self.items[fid] = meta
        return fid

    def request(self, method, url, payload=None, headers=None):
        parts = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(parts.query))
        path = parts.path.removeprefix("/drive/v3/files")
        if method == "GET" and path == "":
            return 200, {}, self._list(query)
        fid = urllib.parse.unquote(path.lstrip("/"))
        if method == "GET":
            return 200, {}, dict(self.items[fid])
        if method == "PATCH":
            meta = self.items[fid]
            meta["parents"] = [p for p in meta["parents"] if p != query["removeParents"]]
            meta["parents"].append(query["addParents"])
            self.patches.append(fid)
            if self.lose_patch_answer:
                self.lose_patch_answer = False
                raise Transient("simulated lost PATCH answer")
            return 200, {}, dict(meta)
        raise AssertionError((method, url))

    def _list(self, query):
        parent = query["q"].split("'")[1]
        kids = sorted((m for m in self.items.values() if parent in m["parents"]),
                      key=lambda m: m["name"])
        start = int(query.get("pageToken", 0))
        body = {"files": [dict(m) for m in kids[start:start + self.page_size]]}
        if start + self.page_size < len(kids):
            body["nextPageToken"] = str(start + self.page_size)
        return body

    def stream(self, url, timeout):
        fid = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[1])
        return io.BytesIO(self.content[fid])
