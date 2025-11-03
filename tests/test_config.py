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
    assert config.packages["example.package"]["url"] == "https://github.com/example/package.git"
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
    assert config.overrides["requests"] == "requests==2.32.4"
    assert "urllib3" in config.overrides
    assert config.overrides["urllib3"] == "urllib3==2.5.0"
    assert "requests" in config.override_keys
    assert "urllib3" in config.override_keys


def test_configuration_with_ignores():
    """Test Configuration with ignored packages."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_with_ignores.ini"))

    assert "ignored.package" in config.ignore_keys
    assert "another.ignored" in config.ignore_keys


def test_configuration_editable_install_mode():
    """Test Configuration with editable install mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_editable_mode.ini"))

    assert config.settings["default-install-mode"] == "editable"
    assert config.packages["example.package"]["install-mode"] == "editable"


def test_configuration_fixed_install_mode():
    """Test Configuration with fixed install mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_fixed_mode.ini"))

    assert config.settings["default-install-mode"] == "fixed"
    assert config.packages["example.package"]["install-mode"] == "fixed"


def test_configuration_direct_mode_deprecated(caplog):
    """Test Configuration with deprecated 'direct' mode logs warning."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_deprecated_direct.ini"))

    # Mode should be treated as 'editable' internally
    assert config.settings["default-install-mode"] == "editable"
    assert config.packages["example.package"]["install-mode"] == "editable"

    # Should have logged deprecation warning
    assert any("install-mode 'direct' is deprecated" in record.message for record in caplog.records)


def test_configuration_package_direct_mode_deprecated(caplog):
    """Test per-package 'direct' mode logs deprecation warning."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_package_direct.ini"))

    # Package mode should be treated as 'editable' internally
    assert config.packages["example.package"]["install-mode"] == "editable"

    # Should have logged deprecation warning
    assert any("install-mode 'direct' is deprecated" in record.message for record in caplog.records)


def test_configuration_invalid_default_install_mode():
    """Test Configuration with invalid default-install-mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(
        ValueError,
        match=r"default-install-mode must be one of 'editable', 'fixed', or 'skip'",
    ):
        Configuration(str(base / "config_invalid_mode.ini"))


def test_configuration_invalid_package_install_mode():
    """Test Configuration with invalid package install-mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(
        ValueError,
        match=r"install-mode in .* must be one of 'editable', 'fixed', or 'skip'",
    ):
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
    config = Configuration(str(base / "basic_config.ini"), override_args={"offline": True})

    assert config.settings["offline"] == "true"
    # Package should inherit offline setting
    assert config.packages["example.package"].get("offline") is True


def test_configuration_override_args_threads():
    """Test Configuration with threads override argument."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"), override_args={"threads": 16})

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
    assert pkg["install-mode"] == "editable"  # default mode changed from 'direct'
    assert pkg["vcs"] == "git"
    assert "path" in pkg


def test_per_package_target_override():
    """Test that per-package target setting overrides default-target.

    This test demonstrates issue #53: the target setting for individual
    packages should override the default-target setting.
    """
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_with_custom_target.ini"))

    # Package without custom target should use default-target
    pkg_default = config.packages["package.with.default.target"]
    assert pkg_default["target"] == "./sources"
    # Normalize paths for comparison (handles both Unix / and Windows \)
    assert (
        pathlib.Path(pkg_default["path"]).as_posix()
        == pathlib.Path(pkg_default["target"]).joinpath("package.with.default.target").as_posix()
    )

    # Package with custom target should use its own target
    pkg_custom = config.packages["package.with.custom.target"]
    assert pkg_custom["target"] == "custom-dir"
    assert (
        pathlib.Path(pkg_custom["path"]).as_posix()
        == pathlib.Path(pkg_custom["target"]).joinpath("package.with.custom.target").as_posix()
    )

    # Package with interpolated target should use the interpolated value
    pkg_interpolated = config.packages["package.with.interpolated.target"]
    assert pkg_interpolated["target"] == "documentation"
    assert (
        pathlib.Path(pkg_interpolated["path"]).as_posix()
        == pathlib.Path(pkg_interpolated["target"]).joinpath("package.with.interpolated.target").as_posix()
    )


def test_config_parse_multiple_pushurls(tmp_path):
    """Test configuration parsing of multiple pushurls."""
    from mxdev.config import Configuration

    config_content = """
[settings]
requirements-in = requirements.txt

[package1]
url = https://github.com/test/repo.git
pushurl =
    git@github.com:test/repo.git
    git@gitlab.com:test/repo.git
    git@bitbucket.org:test/repo.git

[package2]
url = https://github.com/test/repo2.git
pushurl = git@github.com:test/repo2.git
"""

    config_file = tmp_path / "mx.ini"
    config_file.write_text(config_content)

    config = Configuration(str(config_file))

    # package1 should have multiple pushurls
    assert "pushurls" in config.packages["package1"]
    assert len(config.packages["package1"]["pushurls"]) == 3
    assert config.packages["package1"]["pushurls"][0] == "git@github.com:test/repo.git"
    assert config.packages["package1"]["pushurls"][1] == "git@gitlab.com:test/repo.git"
    assert config.packages["package1"]["pushurls"][2] == "git@bitbucket.org:test/repo.git"
    # First pushurl should be kept for backward compatibility
    assert config.packages["package1"]["pushurl"] == "git@github.com:test/repo.git"

    # package2 should have single pushurl (no pushurls list)
    assert "pushurls" not in config.packages["package2"]
    assert config.packages["package2"]["pushurl"] == "git@github.com:test/repo2.git"
