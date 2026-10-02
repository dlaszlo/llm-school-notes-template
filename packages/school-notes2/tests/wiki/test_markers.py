import pytest

from school_notes2.wiki import markers

TEXT = "kézi\n" + markers.wrap("a", "régi\n") + "köz\n" + markers.wrap("b", "") + "vége\n"


def test_read_replace_roundtrip():
    assert markers.names(TEXT) == ["a", "b"]
    assert markers.read(TEXT, "a") == "régi\n"
    new = markers.replace(TEXT, "b", "új")
    assert markers.read(new, "b") == "új\n" and new.startswith("kézi\n") and new.endswith("vége\n")


def test_empty_all_keeps_hand_written_text():
    empty = markers.empty_all(TEXT)
    assert markers.read(empty, "a") == "" and "köz\n" in empty


def test_strip_removes_marker_lines_only():
    assert markers.strip(TEXT) == "kézi\nrégi\nköz\nvége\n"


def test_check_rejects_unpaired_and_duplicate():
    with pytest.raises(markers.MarkerError):
        markers.check(markers.OPEN.format(name="a") + "\n")
    with pytest.raises(markers.MarkerError):
        markers.check(markers.wrap("a", "") + markers.wrap("a", ""))
    with pytest.raises(markers.MarkerError):
        markers.replace("x\n", "a", "y")
