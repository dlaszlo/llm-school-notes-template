"""Move a downloaded package to `Feldolgozva` (plan 4.1, 5.2/4): the tool's only Drive write.

Before moving, the package is listed again and must equal the snapshot taken at download
time; the folder must sit under this learner's root. The move is one PATCH, so it is atomic.
"""

from .client import DriveClient
from .inventory import FOLDER, PROCESSED, READY, nfc, snapshot_entry, walk
from ..state.errors import NeedsOwner, Transient

MAX_DEPTH = 8


def move_to_processed(client: DriveClient, package_id: str, snapshot: list, root_id: str) -> str:
    """Return "moved", "already" (an earlier attempt succeeded) or "changed" (not moved)."""
    folder = client.get(package_id)
    parent_id = _single_parent(folder)
    parent = client.get(parent_id)
    if nfc(parent["name"]) == PROCESSED:
        return "already"
    if nfc(parent["name"]) != READY:
        raise NeedsOwner(f"package {folder['name']!r} is no longer in {READY}",
                         todo="check where the package folder went on Drive")
    subject_id = _single_parent(parent)
    ensure_under_root(client, subject_id, root_id)
    if current_snapshot(client, package_id) != [list(x) for x in snapshot]:
        return "changed"
    processed = _processed_folder(client, subject_id)
    try:
        client.move(package_id, processed, parent_id)
    except Transient:
        # The PATCH may have been applied although the answer was lost: look before retrying.
        if processed in client.get(package_id).get("parents", []):
            return "moved"
        raise
    return "moved"


def current_snapshot(client: DriveClient, package_id: str) -> list:
    return sorted(snapshot_entry(rel, i) for rel, i in walk(client, package_id)
                  if i["mimeType"] != FOLDER)


def ensure_under_root(client: DriveClient, folder_id: str, root_id: str) -> None:
    current = folder_id
    for _ in range(MAX_DEPTH):
        if current == root_id:
            return
        parents = client.get(current).get("parents") or []
        if not parents:
            break
        current = parents[0]
    raise NeedsOwner("the package folder is not under this learner's Drive root",
                     todo="check the Drive folder structure; the tool moves nothing outside it")


def _single_parent(item: dict) -> str:
    parents = item.get("parents") or []
    if len(parents) != 1:
        raise NeedsOwner(f"{item.get('name')!r} has {len(parents)} parents",
                         todo="give the Drive folder exactly one parent")
    return parents[0]


def _processed_folder(client: DriveClient, subject_id: str) -> str:
    for item in client.list_children(subject_id):
        if item["mimeType"] == FOLDER and nfc(item["name"]) == PROCESSED:
            return item["id"]
    raise NeedsOwner(f"the subject folder has no {PROCESSED} folder",
                     todo=f"create the {PROCESSED} folder next to {READY} on Drive")
