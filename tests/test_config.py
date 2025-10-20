import pathlib
import pytest


def test_to_bool():
    """Test the to_bool helper function."""
    from mxdev.config import to_bool

    # String values
    assert to_bool("true") is True
    assert to_bool("True") is True
    assert to_bool("TRUE") is True
    assert to_bool("on") is True
    assert to_bool("ON") is True
    assert to_bool("yes") is True
    assert to_bool("YES") is True
    assert to_bool("1") is True

    assert to_bool("false") is False
    assert to_bool("False") is False
    assert to_bool("no") is False
    assert to_bool("0") is False
    assert to_bool("anything") is False

    # Non-string values
    assert to_bool(True) is True
    assert to_bool(False) is False
    assert to_bool(1) is True
    assert to_bool(0) is False
    assert to_bool([1, 2]) is True
    assert to_bool([]) is False


def test_configuration_basic():
    """Test basic Configuration initialization."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))

    assert config.settings["requirements-in"] == "requirements.txt"
    assert config.settings["requirements-out"] == "requirements-mxdev.txt"
    assert config.settings["constraints-out"] == "constraints-mxdev.txt"
    assert "example.package" in config.packages
    assert (
        config.packages["example.package"]["url"]
        == "https://github.com/example/package.git"
    )
    assert config.packages["example.package"]["branch"] == "main"


def test_configuration_properties():
    """Test Configuration property methods."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))

    assert config.infile == "requirements.txt"
    assert config.out_requirements == "requirements-mxdev.txt"
    assert config.out_constraints == "constraints-mxdev.txt"
    assert "example.package" in config.package_keys
    assert config.override_keys == []


def test_configuration_with_overrides():
    """Test Configuration with version overrides."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_with_overrides.ini"))

    assert "requests" in config.overrides
    assert config.overrides["requests"] == "requests==2.28.0"
    assert "urllib3" in config.overrides
    assert config.overrides["urllib3"] == "urllib3==1.26.9"
    assert "requests" in config.override_keys
    assert "urllib3" in config.override_keys


def test_configuration_with_ignores():
    """Test Configuration with ignored packages."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_with_ignores.ini"))

    assert "ignored.package" in config.ignore_keys
    assert "another.ignored" in config.ignore_keys


def test_configuration_invalid_default_install_mode():
    """Test Configuration with invalid default-install-mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(ValueError, match="default-install-mode must be one of"):
        Configuration(str(base / "config_invalid_mode.ini"))


def test_configuration_invalid_package_install_mode():
    """Test Configuration with invalid package install-mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(ValueError, match="install-mode in .* must be one of"):
        Configuration(str(base / "config_package_invalid_mode.ini"))


def test_configuration_no_url():
    """Test Configuration with package missing URL."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(ValueError, match="has no URL set"):
        Configuration(str(base / "config_no_url.ini"))


def test_configuration_with_extras():
    """Test Configuration with extras and subdirectory."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_with_extras.ini"))

    pkg = config.packages["example.package"]
    assert pkg["extras"] == "test,docs"
    assert pkg["subdirectory"] == "packages/core"
    assert pkg["install-mode"] == "skip"
    assert config.settings.get("main-package") == "-e .[test]"
    assert config.settings.get("default-target") == "./sources"
    # threads from INI is ignored, always defaults to 4 or override_args
    assert config.settings.get("threads") == "4"


def test_configuration_override_args_offline():
    """Test Configuration with offline override argument."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(
        str(base / "basic_config.ini"), override_args={"offline": True}
    )

    assert config.settings["offline"] == "true"
    # Package should inherit offline setting
    assert config.packages["example.package"].get("offline") is True


def test_configuration_override_args_threads():
    """Test Configuration with threads override argument."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(
        str(base / "basic_config.ini"), override_args={"threads": 16}
    )

    assert config.settings["threads"] == "16"


def test_configuration_default_threads():
    """Test Configuration default threads value."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))

    # Should default to 4 if not specified
    assert config.settings["threads"] == "4"


def test_configuration_package_defaults():
    """Test that Configuration applies package defaults correctly."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))

    pkg = config.packages["example.package"]
    assert pkg["branch"] == "main"
    assert pkg["extras"] == ""
    assert pkg["subdirectory"] == ""
    assert pkg["target"] == "sources"  # default-target not set, should be "sources"
    assert pkg["install-mode"] == "direct"  # default mode
    assert pkg["vcs"] == "git"
    assert "path" in pkg
