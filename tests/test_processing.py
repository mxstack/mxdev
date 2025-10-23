from io import StringIO

import os
import pytest


def test_process_line_plain():
    """Test process_line with plain requirement lines."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "requests>=2.28.0",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )
    assert requirements == ["requests>=2.28.0"]
    assert constraints == []


def test_process_line_package_in_package_keys():
    """Test process_line comments out packages in package_keys."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "my.package==1.0.0",
        package_keys=["my.package"],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )
    assert requirements == ["# my.package==1.0.0 -> mxdev disabled (source)\n"]
    assert constraints == []


def test_process_line_package_in_override_keys():
    """Test process_line comments out packages in override_keys."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "my.package==1.0.0",
        package_keys=[],
        override_keys=["my.package"],
        ignore_keys=[],
        variety="r",
    )
    assert requirements == ["# my.package==1.0.0 -> mxdev disabled (version override)\n"]
    assert constraints == []


def test_process_line_package_in_ignore_keys():
    """Test process_line comments out packages in ignore_keys."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "my.package==1.0.0",
        package_keys=[],
        override_keys=[],
        ignore_keys=["my.package"],
        variety="r",
    )
    assert requirements == ["# my.package==1.0.0 -> mxdev disabled (ignore)\n"]
    assert constraints == []


def test_process_line_constraint():
    """Test process_line with constraint variety."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "requests==2.28.0",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="c",
    )
    assert constraints == ["requests==2.28.0"]
    assert requirements == []


def test_process_line_comments():
    """Test process_line passes through comments."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "# This is a comment",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )
    assert requirements == ["# This is a comment"]
    assert constraints == []


def test_process_line_blank():
    """Test process_line passes through blank lines."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )
    assert requirements == [""]
    assert constraints == []


def test_resolve_dependencies_missing_file(tmp_path):
    """Test resolve_dependencies with a missing requirements file."""
    from mxdev.processing import resolve_dependencies

    requirements, constraints = resolve_dependencies(
        "nonexistent.txt",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )
    # Should return empty lists when file doesn't exist
    assert requirements == []
    assert constraints == []


def test_resolve_dependencies_simple_file(tmp_path):
    """Test resolve_dependencies with a simple requirements file."""
    from mxdev.processing import resolve_dependencies

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("requests>=2.28.0\nurllib3==1.26.9\n")

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        requirements, constraints = resolve_dependencies(
            "requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
        )
        assert any("requests>=2.28.0" in line for line in requirements)
        assert any("urllib3==1.26.9" in line for line in requirements)
    finally:
        os.chdir(old_cwd)


def test_resolve_dependencies_with_constraints(tmp_path):
    """Test resolve_dependencies with -c constraint reference."""
    from mxdev.processing import resolve_dependencies

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("-c constraints.txt\nrequests>=2.28.0\n")

    const_file = tmp_path / "constraints.txt"
    const_file.write_text("urllib3==1.26.9\n")

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        requirements, constraints = resolve_dependencies(
            "requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
        )
        assert any("requests" in line for line in requirements)
        # Constraints from the -c file should be in constraints list
        assert any("urllib3" in line for line in constraints)
    finally:
        os.chdir(old_cwd)


def test_resolve_dependencies_nested(tmp_path):
    """Test resolve_dependencies with nested -r references."""
    from mxdev.processing import resolve_dependencies

    base_req = tmp_path / "base.txt"
    base_req.write_text("requests>=2.28.0\n")

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("-r base.txt\nurllib3==1.26.9\n")

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        requirements, constraints = resolve_dependencies(
            "requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
        )
        # Should include both base.txt and requirements.txt content
        assert any("requests" in line for line in requirements)
        assert any("urllib3" in line for line in requirements)
    finally:
        os.chdir(old_cwd)


def test_resolve_dependencies_http(tmp_path):
    """Test resolve_dependencies with HTTP URL."""
    from mxdev.processing import resolve_dependencies

    import httpretty

    # Mock HTTP response
    httpretty.enable()
    try:
        httpretty.register_uri(
            httpretty.GET,
            "http://example.com/requirements.txt",
            body="requests>=2.28.0\n",
        )

        requirements, constraints = resolve_dependencies(
            "http://example.com/requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
        )
        assert any("requests" in line for line in requirements)
    finally:
        httpretty.disable()
        httpretty.reset()


def test_write_dev_sources(tmp_path):
    """Test write_dev_sources writes development sources correctly."""
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create source directories so they exist
    (tmp_path / "sources" / "example.package").mkdir(parents=True)
    (tmp_path / "sources" / "extras.package" / "packages" / "core").mkdir(parents=True)

    # Create minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("[settings]\nrequirements-in = requirements.txt\n")
    config = Configuration(str(config_file))
    state = State(configuration=config)

    packages = {
        "example.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "example.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "skip.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "skip.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "skip",
        },
        "extras.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "extras.package"),
            "extras": "test,docs",
            "subdirectory": "packages/core",
            "install-mode": "editable",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages, state)

    content = outfile.read_text()
    assert "-e ./sources/example.package" in content
    assert "skip.package" not in content  # skip mode should not be written
    assert "-e ./sources/extras.package/packages/core[test,docs]" in content


def test_write_dev_sources_fixed_mode(tmp_path):
    """Test write_dev_sources with fixed install mode (no -e prefix)."""
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create source directories so they exist
    (tmp_path / "sources" / "fixed.package").mkdir(parents=True)
    (tmp_path / "sources" / "fixed.with.extras" / "packages" / "core").mkdir(parents=True)

    # Create minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("[settings]\nrequirements-in = requirements.txt\n")
    config = Configuration(str(config_file))
    state = State(configuration=config)

    packages = {
        "fixed.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "fixed.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "fixed",
        },
        "fixed.with.extras": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "fixed.with.extras"),
            "extras": "test",
            "subdirectory": "packages/core",
            "install-mode": "fixed",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages, state)

    content = outfile.read_text()
    # Fixed mode should NOT have -e prefix
    assert "./sources/fixed.package" in content
    assert "-e ./sources/fixed.package" not in content
    assert "./sources/fixed.with.extras/packages/core[test]" in content
    assert "-e ./sources/fixed.with.extras/packages/core[test]" not in content


def test_write_dev_sources_mixed_modes(tmp_path):
    """Test write_dev_sources with mixed install modes."""
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create source directories so they exist
    (tmp_path / "sources" / "editable.package").mkdir(parents=True)
    (tmp_path / "sources" / "fixed.package").mkdir(parents=True)

    # Create minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("[settings]\nrequirements-in = requirements.txt\n")
    config = Configuration(str(config_file))
    state = State(configuration=config)

    packages = {
        "editable.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "editable.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "fixed.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "fixed.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "fixed",
        },
        "skip.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "skip.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "skip",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages, state)

    content = outfile.read_text()
    # Editable should have -e
    assert "-e ./sources/editable.package" in content
    # Fixed should NOT have -e
    assert "./sources/fixed.package" in content
    assert "-e ./sources/fixed.package" not in content
    # Skip should not appear at all
    assert "skip.package" not in content


def test_write_dev_sources_empty(tmp_path):
    """Test write_dev_sources with no packages."""
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("[settings]\nrequirements-in = requirements.txt\n")
    config = Configuration(str(config_file))
    state = State(configuration=config)

    fio = StringIO()
    write_dev_sources(fio, {}, state)

    # Should not write anything for empty packages
    assert fio.getvalue() == ""


def test_write_dev_overrides(tmp_path):
    """Test write_dev_overrides writes overrides correctly."""
    from mxdev.processing import write_dev_overrides

    overrides = {
        "requests": "requests==2.28.0",
        "urllib3": "urllib3==1.26.9",
    }

    outfile = tmp_path / "constraints.txt"
    with open(outfile, "w") as fio:
        write_dev_overrides(fio, overrides, package_keys=[])

    content = outfile.read_text()
    assert "requests==2.28.0" in content
    assert "urllib3==1.26.9" in content


def test_write_dev_overrides_source_wins(tmp_path):
    """Test write_dev_overrides comments out overrides when source exists."""
    from mxdev.processing import write_dev_overrides

    overrides = {
        "my.package": "my.package==1.0.0",
        "other.package": "other.package==2.0.0",
    }

    outfile = tmp_path / "test_override_source_wins.txt"
    with open(outfile, "w") as fio:
        write_dev_overrides(fio, overrides, package_keys=["my.package"])

    content = outfile.read_text()
    assert "# my.package==1.0.0 IGNORE mxdev constraint override" in content


def test_write_main_package(tmp_path):
    """Test write_main_package writes main package correctly."""
    from mxdev.processing import write_main_package

    settings = {
        "main-package": "-e .[test]",
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_main_package(fio, settings)

    content = outfile.read_text()
    assert "-e .[test]" in content


def test_write_main_package_empty(tmp_path):
    """Test write_main_package with no main package."""
    from mxdev.processing import write_main_package

    settings = {}

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_main_package(fio, settings)

    content = outfile.read_text()
    assert content == ""


def test_write_output_with_overrides(tmp_path):
    """Test write() with version overrides."""
    from mxdev.config import Configuration
    from mxdev.processing import write
    from mxdev.state import State

    # Create a simple config
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
version-overrides =
    requests==2.28.0
"""
    )

    config = Configuration(str(config_file))
    state = State(configuration=config)
    state.requirements = ["requests\n"]
    state.constraints = ["urllib3==1.26.9\n"]

    # Change to tmp_path so output files go there
    import os

    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        write(state)

        # Check requirements file
        req_file = tmp_path / "requirements-out.txt"
        assert req_file.exists()
        req_content = req_file.read_text()
        assert "requests\n" in req_content

        # Check constraints file
        const_file = tmp_path / "constraints-out.txt"
        assert const_file.exists()
        const_content = const_file.read_text()
        assert "requests==2.28.0" in const_content  # Override applied
        assert "urllib3==1.26.9" in const_content
    finally:
        os.chdir(old_cwd)


def test_write_output_with_ignores(tmp_path):
    """Test write() with ignores."""
    from mxdev.config import Configuration
    from mxdev.processing import read
    from mxdev.processing import write
    from mxdev.state import State

    # Create requirements.txt with packages
    req_in = tmp_path / "requirements.txt"
    req_in.write_text("requests\nmy.mainpackage==1.0.0\n-c constraints.txt\n")

    # Create constraints.txt with packages
    const_in = tmp_path / "constraints.txt"
    const_in.write_text("urllib3==1.26.9\nmy.mainpackage==1.0.0\n")

    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
ignores =
    my.mainpackage
"""
    )

    config = Configuration(str(config_file))
    state = State(configuration=config)

    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        read(state)
        write(state)

        req_file = tmp_path / "requirements-out.txt"
        req_content = req_file.read_text()
        assert "requests\n" in req_content
        # Ignored package should be commented out
        assert "# my.mainpackage==1.0.0 -> mxdev disabled (ignore)" in req_content

        const_file = tmp_path / "constraints-out.txt"
        const_content = const_file.read_text()
        assert "urllib3==1.26.9" in const_content
        # Ignored package should be commented out in constraints too
        assert "# my.mainpackage==1.0.0 -> mxdev disabled (ignore)" in const_content
    finally:
        os.chdir(old_cwd)


def test_write_output_with_main_package(tmp_path):
    """Test write() with main-package setting."""
    from mxdev.config import Configuration
    from mxdev.processing import write
    from mxdev.state import State

    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
main-package = -e .[test]
"""
    )

    config = Configuration(str(config_file))
    state = State(configuration=config)
    state.requirements = ["requests\n"]
    state.constraints = []

    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        write(state)

        req_file = tmp_path / "requirements-out.txt"
        req_content = req_file.read_text()
        assert "-e .[test]" in req_content
        assert "requests\n" in req_content
    finally:
        os.chdir(old_cwd)


def test_write_relative_constraints_path_different_dirs(tmp_path):
    """Test write() generates correct relative path for constraints file.

    When requirements and constraints files are in different directories,
    the -c reference in requirements should use a relative path.
    """
    from mxdev.config import Configuration
    from mxdev.processing import read
    from mxdev.processing import write
    from mxdev.state import State

    # Create directory structure
    reqs_dir = tmp_path / "reqs"
    reqs_dir.mkdir()
    const_dir = tmp_path / "constraints"
    const_dir.mkdir()

    # Create config with files in different directories
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = reqs/requirements.txt
constraints-out = constraints/constraints.txt
"""
    )

    # Create requirements.txt with a constraint reference
    req_in = tmp_path / "requirements.txt"
    req_in.write_text("requests\n-c base-constraints.txt\n")

    # Create base constraints file with some content
    const_in = tmp_path / "base-constraints.txt"
    const_in.write_text("urllib3==1.26.9\n")

    config = Configuration(str(config_file))
    state = State(configuration=config)

    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        read(state)
        write(state)

        req_file = tmp_path / "reqs" / "requirements.txt"
        assert req_file.exists()
        req_content = req_file.read_text()

        # Should write path relative to reqs/ directory
        # From reqs/ to constraints/constraints.txt = ../constraints/constraints.txt
        assert "-c ../constraints/constraints.txt\n" in req_content, (
            f"Expected '-c ../constraints/constraints.txt' (relative path), " f"but got:\n{req_content}"
        )
    finally:
        os.chdir(old_cwd)


def test_write_dev_sources_missing_directories(tmp_path, caplog):
    """Test write_dev_sources with non-existing source directories in offline mode.

    When source directories don't exist in offline mode (expected behavior),
    packages should be written as comments with warnings.
    """
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create config WITH offline mode
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
offline = true
"""
    )
    config = Configuration(str(config_file))
    state = State(configuration=config)

    # Create one existing directory, leave others missing
    existing_pkg_path = tmp_path / "sources" / "existing.package"
    existing_pkg_path.mkdir(parents=True)

    packages = {
        "existing.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "existing.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "missing.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "missing.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "missing.fixed": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "missing.fixed"),
            "extras": "test",
            "subdirectory": "",
            "install-mode": "fixed",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages, state)

    content = outfile.read_text()

    # Existing package should be written normally
    assert "-e ./sources/existing.package\n" in content

    # Missing packages should be commented out
    assert "# -e ./sources/missing.package  # mxdev: source not checked out\n" in content
    assert "# ./sources/missing.fixed[test]  # mxdev: source not checked out\n" in content

    # Check warnings were logged (offline mode specific)
    assert "Source directory does not exist" in caplog.text
    assert "missing.package" in caplog.text
    assert "missing.fixed" in caplog.text
    assert "This is expected in offline mode" in caplog.text
    assert "Run mxdev without -n and --offline flags" in caplog.text


def test_write_dev_sources_missing_directories_raises_error(tmp_path, caplog):
    """Test write_dev_sources raises RuntimeError when sources missing in non-offline mode.

    When source directories don't exist and we're NOT in offline mode,
    this is a fatal error - something went wrong earlier in the workflow.
    """
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create config WITHOUT offline mode (non-offline mode)
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
"""
    )
    config = Configuration(str(config_file))
    state = State(configuration=config)

    # Define packages but DON'T create source directories
    packages = {
        "missing.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "missing.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "missing.fixed": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "missing.fixed"),
            "extras": "test",
            "subdirectory": "",
            "install-mode": "fixed",
        },
    }

    outfile = tmp_path / "requirements.txt"

    # Should raise RuntimeError for missing sources in non-offline mode
    with pytest.raises(RuntimeError) as exc_info:
        with open(outfile, "w") as fio:
            write_dev_sources(fio, packages, state)

    # Error message should contain package names
    error_msg = str(exc_info.value)
    assert "missing.package" in error_msg
    assert "missing.fixed" in error_msg
    assert "Source directories missing" in error_msg

    # Should log ERROR (not just WARNING)
    assert any(record.levelname == "ERROR" for record in caplog.records)
    assert "Source directory does not exist" in caplog.text


def test_write_dev_sources_missing_directories_offline_mode(tmp_path, caplog):
    """Test write_dev_sources warning message in offline mode.

    When in offline mode, the warning should mention offline mode specifically.
    """
    from mxdev.config import Configuration
    from mxdev.processing import write_dev_sources
    from mxdev.state import State

    # Create config WITH offline mode
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
offline = true
"""
    )
    config = Configuration(str(config_file))
    state = State(configuration=config)

    packages = {
        "missing.package": {
            "target": "sources",
            "path": str(tmp_path / "sources" / "missing.package"),
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages, state)

    content = outfile.read_text()

    # Missing package should be commented out
    assert "# -e ./sources/missing.package  # mxdev: source not checked out\n" in content

    # Check offline-specific warning was logged
    assert "Source directory does not exist" in caplog.text
    assert "This is expected in offline mode" in caplog.text
    assert "Run mxdev without -n and --offline flags" in caplog.text


def test_http_cache_online_mode(tmp_path):
    """Test HTTP URLs are cached in online mode."""
    from mxdev.processing import resolve_dependencies

    import httpretty

    cache_dir = tmp_path / ".mxdev-cache"

    # Mock HTTP response
    httpretty.enable()
    try:
        httpretty.register_uri(
            httpretty.GET,
            "http://example.com/requirements.txt",
            body="requests>=2.28.0\nurllib3==1.26.9\n",
        )

        requirements, constraints = resolve_dependencies(
            "http://example.com/requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
            offline=False,
            cache_dir=cache_dir,
        )

        # Should have requirements
        assert any("requests" in line for line in requirements)
        assert any("urllib3" in line for line in requirements)

        # Cache directory should be created
        assert cache_dir.exists()

        # Cache file should exist (check for any file in cache)
        cache_files = list(cache_dir.glob("*"))
        cache_content_files = [f for f in cache_files if not f.suffix]
        assert len(cache_content_files) >= 1, "Expected at least one cache file"

        # Read cache file and verify content
        cache_file = cache_content_files[0]
        cached_content = cache_file.read_text()
        assert "requests>=2.28.0" in cached_content
        assert "urllib3==1.26.9" in cached_content

        # Check .url metadata file exists
        url_files = list(cache_dir.glob("*.url"))
        assert len(url_files) >= 1, "Expected at least one .url metadata file"

    finally:
        httpretty.disable()
        httpretty.reset()


def test_http_cache_offline_mode_hit(tmp_path):
    """Test HTTP URLs are read from cache in offline mode (cache hit)."""
    from mxdev.processing import _get_cache_key
    from mxdev.processing import resolve_dependencies

    cache_dir = tmp_path / ".mxdev-cache"
    cache_dir.mkdir()

    url = "http://example.com/requirements.txt"
    cache_key = _get_cache_key(url)

    # Pre-populate cache
    cache_file = cache_dir / cache_key
    cache_file.write_text("cached-package>=1.0.0\n")

    # Also write .url metadata
    url_file = cache_dir / f"{cache_key}.url"
    url_file.write_text(url)

    # Don't enable httpretty - we shouldn't make any HTTP requests
    requirements, constraints = resolve_dependencies(
        url,
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
        offline=True,
        cache_dir=cache_dir,
    )

    # Should use cached content
    assert any("cached-package" in line for line in requirements)

    # Verify no HTTP request was made (httpretty would fail if one was attempted)


def test_http_cache_offline_mode_miss(tmp_path):
    """Test HTTP URLs error in offline mode when not cached (cache miss)."""
    from mxdev.processing import resolve_dependencies

    cache_dir = tmp_path / ".mxdev-cache"
    cache_dir.mkdir()

    # Cache is empty, should raise error
    with pytest.raises(RuntimeError) as exc_info:
        resolve_dependencies(
            "http://example.com/requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
            offline=True,
            cache_dir=cache_dir,
        )

    error_msg = str(exc_info.value)
    assert "offline mode" in error_msg.lower()
    assert "not found in cache" in error_msg.lower()
    assert "http://example.com/requirements.txt" in error_msg


def test_cache_key_generation():
    """Test cache key generation is deterministic and collision-resistant."""
    from mxdev.processing import _get_cache_key

    # Same URL should produce same cache key
    url1 = "http://example.com/requirements.txt"
    key1 = _get_cache_key(url1)
    key2 = _get_cache_key(url1)
    assert key1 == key2

    # Different URLs should produce different cache keys
    url2 = "http://example.com/constraints.txt"
    key3 = _get_cache_key(url2)
    assert key1 != key3

    # Cache key should be reasonable length (16 hex chars)
    assert len(key1) == 16
    assert all(c in "0123456789abcdef" for c in key1)


def test_http_cache_revalidates_in_online_mode(tmp_path):
    """Test HTTP cache is updated in online mode (not just read)."""
    from mxdev.processing import _get_cache_key
    from mxdev.processing import resolve_dependencies

    import httpretty

    cache_dir = tmp_path / ".mxdev-cache"
    cache_dir.mkdir()

    url = "http://example.com/requirements.txt"
    cache_key = _get_cache_key(url)

    # Pre-populate cache with old content
    cache_file = cache_dir / cache_key
    cache_file.write_text("old-package==1.0.0\n")

    # Mock HTTP response with new content
    httpretty.enable()
    try:
        httpretty.register_uri(
            httpretty.GET,
            url,
            body="new-package>=2.0.0\n",
        )

        requirements, constraints = resolve_dependencies(
            url,
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
            offline=False,
            cache_dir=cache_dir,
        )

        # Should use NEW content from HTTP, not old cache
        assert any("new-package" in line for line in requirements)
        assert not any("old-package" in line for line in requirements)

        # Cache should be updated
        cached_content = cache_file.read_text()
        assert "new-package>=2.0.0" in cached_content
        assert "old-package" not in cached_content

    finally:
        httpretty.disable()
        httpretty.reset()
