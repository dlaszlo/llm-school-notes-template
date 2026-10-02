"""Download one package into the task folder (plan 5.2/3, 8.2 `downloading`)."""

from pathlib import Path

from .client import DriveClient
from .inventory import Package


def download_package(client: DriveClient, pkg: Package, dest: Path) -> list[dict]:
    """Download every usable file of `pkg` below `dest`; return one record per file.

    A crash leaves only `.part` files or complete verified files; the orchestrator clears the
    folder before a repeated download (8.2), so no resume logic is needed here.
    """
    records = []
    for f in pkg.files:
        target = dest / f.rel
        if not target.resolve().is_relative_to(dest.resolve()):
            raise ValueError(f"unsafe path in package: {f.rel!r}")
        sha = client.download(f.as_item(), target)
        records.append({"drive_id": f.id, "rel": f.rel, "path": str(target), "size": f.size,
                        "md5": f.md5, "sha256": sha})
    return records
