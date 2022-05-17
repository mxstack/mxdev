from ..vcs import common
from unittest import mock
import pytest
import typing


def test_print_stderr(mocker):
    write_ = mocker.patch("sys.stderr.write")
    flush_ = mocker.patch("sys.stderr.flush")
    common.print_stderr("message")
    assert write_.call_count == 2
    assert flush_.call_count == 1


def test_version_sorted():
    expected = ["version-1-0-1", "version-1-0-2", "version-1-0-10"]
    actual = common.version_sorted([
        "version-1-0-10",
        "version-1-0-2",
        "version-1-0-1"
    ])
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
    assert bwc.should_update(update="true") is True
    assert bwc.should_update(update="yes") is True
    assert bwc.should_update(update="false") is False
    assert bwc.should_update(update="no") is False
    with pytest.raises(ValueError):
        bwc.should_update(update="maybe")

    bwc = TestWorkingCopy(
        source=dict(
            url="https://tld.com/repo.git",
            update="false"
        )
    )
    assert bwc.should_update(update="true") is False


def test_yesno(mocker):
    class Input:
        question = ""
        answer = ""
        def __call__(self, question):
            self.question = question
            answer = self.answer
            if answer == "invalid":
                self.answer = "y"
            return answer

    input_ = mocker.patch("mxdev.vcs.common.input", new_callable=Input)
    print_stderr_ = mocker.patch("mxdev.vcs.common.print_stderr")

    common.yesno(question="Really?")
    assert input_.question == "Really? [Yes/no/all] "

    common.yesno(question="Really?", all=False)
    assert input_.question == "Really? [Yes/no] "

    assert common.yesno(question="") is True
    assert common.yesno(question="", default=False) is False

    input_.answer = "y"
    assert common.yesno(question="") is True
    input_.answer = "yes"
    assert common.yesno(question="") is True

    input_.answer = "n"
    assert common.yesno(question="") is False
    input_.answer = "no"
    assert common.yesno(question="") is False

    input_.answer = "a"
    assert common.yesno(question="") == "all"
    input_.answer = "all"
    assert common.yesno(question="") == "all"

    input_.answer = "invalid"
    common.yesno(question="")
    print_stderr_.assert_called_with(
        "You have to answer with y, yes, n, no, a or all."
    )

    input_.answer = "invalid"
    common.yesno(question="", all=False)
    print_stderr_.assert_called_with(
        "You have to answer with y, yes, n or no."
    )
