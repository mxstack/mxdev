from ..vcs import common
import pytest
import typing


def test_version_sorted():
    expected = ["version-1-0-1", "version-1-0-2", "version-1-0-10"]
    actual = common.version_sorted(["version-1-0-10", "version-1-0-2", "version-1-0-1"])
    assert expected == actual


def test_BaseWorkingCopy():
    with pytest.raises(TypeError):
        common.BaseWorkingCopy(source={})

    class TestWorkingCopy(common.BaseWorkingCopy):
        def checkout(self, **kwargs) -> typing.Union[str, None]:
            pass
        def status(self, **kwargs) -> typing.Union[typing.Tuple[str, str], str]:
            pass
        def matches(self) -> bool:
            pass
        def update(self, **kwargs) -> typing.Union[str, None]:
            pass

    bwc = TestWorkingCopy(source=dict(url="https://tld.com/repo.git"))

    assert bwc._output == []
    bwc.output("foo")
    assert bwc._output == ["foo"]

    assert bwc.should_update(offline=True) is False
    assert bwc.should_update(update='true') is True
    assert bwc.should_update(update='yes') is True
    assert bwc.should_update(update='false') is False
    assert bwc.should_update(update='no') is False
    with pytest.raises(ValueError):
        bwc.should_update(update='maybe')

    bwc = TestWorkingCopy(source=dict(
        url="https://tld.com/repo.git",
        update="false"
    ))
    assert bwc.should_update(update='true') is False
