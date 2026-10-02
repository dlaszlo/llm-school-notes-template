import pytest

from fakedrive import FakeDrive
from school_notes2.drive.client import DriveClient


@pytest.fixture
def fake():
    return FakeDrive()


@pytest.fixture
def client(fake):
    return DriveClient(fake)


@pytest.fixture
def tree(fake):
    """A learner root with Füzet/Matek/{Feltöltés, Feltöltés_Kész, Feldolgozva}."""
    root = fake.folder("Benedek")
    fuzet = fake.folder("Füzet", root)
    matek = fake.folder("Matek", fuzet)
    ids = {"root": root, "fuzet": fuzet, "matek": matek,
           "upload": fake.folder("Feltöltés", matek),
           "ready": fake.folder("Feltöltés_Kész", matek),
           "done": fake.folder("Feldolgozva", matek)}
    return ids
