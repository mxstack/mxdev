from ..vcs.common import version_sorted

def test_version_sorted():
    expected = ["version-1-0-1", "version-1-0-2", "version-1-0-10"]
    actual = version_sorted(["version-1-0-10", "version-1-0-2", "version-1-0-1"])
    assert expected == actual
