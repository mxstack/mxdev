from ..vcs import common


def test_version_sorted():
    expected = ["version-1-0-1", "version-1-0-2", "version-1-0-10"]
    actual = common.version_sorted(["version-1-0-10", "version-1-0-2", "version-1-0-1"])
    assert expected == actual


def test_BaseWorkingCopy():
    bwc = common.BaseWorkingCopy(source=dict(url='https://tld.com/repo.git'))

    assert bwc._output == []
    bwc.output('foo')
    assert bwc._output == ['foo']

    assert bwc.should_update(offline=True) is False
