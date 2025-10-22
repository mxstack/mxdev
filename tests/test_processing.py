from io import StringIO

import os
import pathlib


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
    assert "# my.package==1.0.0 -> mxdev disabled (source)" in requirements[0]


def test_process_line_constraint_in_override_keys():
    """Test process_line comments out constraints in override_keys."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "requests==2.28.0",
        package_keys=[],
        override_keys=["requests"],
        ignore_keys=[],
        variety="c",
    )
    assert "# requests==2.28.0 -> mxdev disabled (override)" in constraints[0]


def test_process_line_constraint_in_ignore_keys():
    """Test process_line comments out constraints in ignore_keys."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        "ignored.package==1.0.0",
        package_keys=[],
        override_keys=[],
        ignore_keys=["ignored.package"],
        variety="c",
    )
    assert "# ignored.package==1.0.0 -> mxdev disabled (ignore)" in constraints[0]


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
    assert requirements == []
    assert constraints == ["requests==2.28.0"]


def test_process_line_bytes():
    """Test process_line handles bytes input."""
    from mxdev.processing import process_line

    requirements, constraints = process_line(
        b"requests>=2.28.0",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )
    assert requirements == ["requests>=2.28.0"]


def test_process_io():
    """Test process_io reads and processes lines from IO."""
    from mxdev.processing import process_io

    fio = StringIO("requests>=2.28.0\nurllib3>=1.26.9\n")
    requirements = []
    constraints = []

    process_io(fio, requirements, constraints, [], [], [], "r")

    assert len(requirements) == 2
    assert "requests>=2.28.0" in requirements[0]
    assert "urllib3>=1.26.9" in requirements[1]


def test_resolve_dependencies_file():
    """Test resolve_dependencies with a file."""
    from mxdev.processing import resolve_dependencies

    base = pathlib.Path(__file__).parent / "data" / "requirements"
    requirements, constraints = resolve_dependencies(
        str(base / "basic_requirements.txt"),
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
        variety="r",
    )

    # Should have header/footer and requirements
    assert len(requirements) > 3
    assert any("requests" in line for line in requirements)
    assert any("urllib3" in line for line in requirements)
    assert any("packaging" in line for line in requirements)


def test_resolve_dependencies_empty():
    """Test resolve_dependencies with empty file_or_url."""
    from mxdev.processing import resolve_dependencies

    requirements, constraints = resolve_dependencies(
        "",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
    )

    assert requirements == []
    assert constraints == []


def test_resolve_dependencies_file_not_found():
    """Test resolve_dependencies with non-existent file."""
    from mxdev.processing import resolve_dependencies

    requirements, constraints = resolve_dependencies(
        "/tmp/does_not_exist_at_all_hopefully.txt",
        package_keys=[],
        override_keys=[],
        ignore_keys=[],
    )

    # Should return empty and log info
    assert len(requirements) == 0
    assert len(constraints) == 0


def test_resolve_dependencies_with_constraints():
    """Test resolve_dependencies with -c constraint reference."""
    from mxdev.processing import resolve_dependencies

    import os

    base = pathlib.Path(__file__).parent / "data" / "requirements"
    old_cwd = os.getcwd()
    os.chdir(base)  # Change to requirements dir so relative -c works

    try:
        requirements, constraints = resolve_dependencies(
            "requirements_with_constraints.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
        )

        # Should have processed constraints file
        assert len(constraints) > 0
        assert any("requests" in line for line in constraints)
    finally:
        os.chdir(old_cwd)


def test_resolve_dependencies_nested():
    """Test resolve_dependencies with -r nested requirements."""
    from mxdev.processing import resolve_dependencies

    import os

    base = pathlib.Path(__file__).parent / "data" / "requirements"
    old_cwd = os.getcwd()
    os.chdir(base)  # Change to requirements dir so relative -r works

    try:
        requirements, constraints = resolve_dependencies(
            "nested_requirements.txt",
            package_keys=[],
            override_keys=[],
            ignore_keys=[],
            variety="r",
        )

        # Should have processed nested file
        assert len(requirements) > 0
        assert any("urllib3" in line for line in requirements)
        assert any("requests" in line for line in requirements)
    finally:
        os.chdir(old_cwd)


def test_write_dev_sources(tmp_path):
    """Test write_dev_sources writes development sources correctly."""
    from mxdev.processing import write_dev_sources

    packages = {
        "example.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "skip.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "skip",
        },
        "extras.package": {
            "target": "sources",
            "extras": "test,docs",
            "subdirectory": "packages/core",
            "install-mode": "editable",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages)

    content = outfile.read_text()
    assert "-e ./sources/example.package" in content
    assert "skip.package" not in content  # skip mode should not be written
    assert "-e ./sources/extras.package/packages/core[test,docs]" in content


def test_write_dev_sources_fixed_mode(tmp_path):
    """Test write_dev_sources with fixed install mode (no -e prefix)."""
    from mxdev.processing import write_dev_sources

    packages = {
        "fixed.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "fixed",
        },
        "fixed.with.extras": {
            "target": "sources",
            "extras": "test",
            "subdirectory": "packages/core",
            "install-mode": "fixed",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages)

    content = outfile.read_text()
    # Fixed mode should NOT have -e prefix
    assert "./sources/fixed.package" in content
    assert "-e ./sources/fixed.package" not in content
    assert "./sources/fixed.with.extras/packages/core[test]" in content
    assert "-e ./sources/fixed.with.extras/packages/core[test]" not in content


def test_write_dev_sources_mixed_modes(tmp_path):
    """Test write_dev_sources with mixed install modes."""
    from mxdev.processing import write_dev_sources

    packages = {
        "editable.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",
        },
        "fixed.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "fixed",
        },
        "skip.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "skip",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages)

    content = outfile.read_text()
    # Editable should have -e prefix
    assert "-e ./sources/editable.package" in content
    # Fixed should NOT have -e prefix
    assert "./sources/fixed.package" in content
    assert "-e ./sources/fixed.package" not in content
    # Skip should not appear at all
    assert "skip.package" not in content


def test_write_dev_sources_empty():
    """Test write_dev_sources with no packages."""
    from io import StringIO
    from mxdev.processing import write_dev_sources

    fio = StringIO()
    write_dev_sources(fio, {})

    # Should not write anything for empty packages
    assert fio.getvalue() == ""


def test_write_dev_overrides(tmp_path):
    """Test write_dev_overrides writes overrides correctly."""
    from mxdev.processing import write_dev_overrides

    overrides = {
        "requests": "requests==2.28.0",
        "urllib3": "urllib3==1.26.9",
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_overrides(fio, overrides, package_keys=[])

    content = outfile.read_text()
    assert "requests==2.28.0" in content
    assert "urllib3==1.26.9" in content


def test_write_dev_overrides_source_wins(tmp_path):
    """Test write_dev_overrides comments out override when package is in sources."""
    from mxdev.processing import write_dev_overrides

    overrides = {
        "my.package": "my.package==1.0.0",
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


def test_write_main_package_not_set():
    """Test write_main_package when main-package not set."""
    from io import StringIO
    from mxdev.processing import write_main_package

    settings = {}
    fio = StringIO()
    write_main_package(fio, settings)

    # Should not write anything when main-package not set
    assert fio.getvalue() == ""


def test_write(tmp_path):
    """Test write function creates output files correctly."""
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

        # Check requirements file was created
        req_file = tmp_path / "requirements-out.txt"
        assert req_file.exists()
        req_content = req_file.read_text()
        assert "requests" in req_content
        assert "-c constraints-out.txt" in req_content

        # Check constraints file was created
        const_file = tmp_path / "constraints-out.txt"
        assert const_file.exists()
        const_content = const_file.read_text()
        assert "urllib3==1.26.9" in const_content
        assert "requests==2.28.0" in const_content
    finally:
        os.chdir(old_cwd)


def test_write_no_constraints(tmp_path):
    """Test write function when there are no constraints."""
    from mxdev.config import Configuration
    from mxdev.processing import write
    from mxdev.state import State

    # Create a simple config without constraints
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
"""
    )

    config = Configuration(str(config_file))
    state = State(configuration=config)
    state.requirements = ["requests\n"]
    state.constraints = []

    # Change to tmp_path so output files go there
    import os

    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        write(state)

        # Check requirements file was created
        req_file = tmp_path / "requirements-out.txt"
        assert req_file.exists()
        req_content = req_file.read_text()
        assert "requests" in req_content
        assert "-c constraints-out.txt" not in req_content  # No constraints reference

        # Check constraints file was NOT created
        const_file = tmp_path / "constraints-out.txt"
        assert not const_file.exists()
    finally:
        os.chdir(old_cwd)


def test_relative_constraints_path_in_subdirectory(tmp_path):
    """Test that constraints path in requirements-out is relative to requirements file location.

    This reproduces issue #22: when requirements-out and constraints-out are in subdirectories,
    the constraints reference should be relative to the requirements file's directory.
    """
    from mxdev.config import Configuration
    from mxdev.processing import read
    from mxdev.processing import write
    from mxdev.state import State

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create subdirectory for output files
        (tmp_path / "requirements").mkdir()

        # Create input constraints file
        constraints_in = tmp_path / "constraints.txt"
        constraints_in.write_text("requests==2.28.0\nurllib3==1.26.9\n")

        # Create input requirements file with a constraint reference
        requirements_in = tmp_path / "requirements.txt"
        requirements_in.write_text("-c constraints.txt\nrequests\n")

        # Create config with both output files in subdirectory
        config_file = tmp_path / "mx.ini"
        config_file.write_text(
            """[settings]
requirements-in = requirements.txt
requirements-out = requirements/plone.txt
constraints-out = requirements/constraints.txt
"""
        )

        config = Configuration(str(config_file))
        state = State(configuration=config)

        # Read and write
        read(state)
        write(state)

        # Check requirements file contains relative path to constraints
        req_file = tmp_path / "requirements" / "plone.txt"
        assert req_file.exists()
        req_content = req_file.read_text()

        # Bug: Currently writes "-c requirements/constraints.txt"
        # Expected: Should write "-c constraints.txt" (relative to requirements file's directory)
        assert "-c constraints.txt\n" in req_content, (
            f"Expected '-c constraints.txt' (relative path), " f"but got:\n{req_content}"
        )

        # Should NOT contain the full path from config file's perspective
        assert "-c requirements/constraints.txt" not in req_content
    finally:
        os.chdir(old_cwd)


def test_relative_constraints_path_different_directories(tmp_path):
    """Test constraints path when requirements and constraints are in different directories."""
    from mxdev.config import Configuration
    from mxdev.processing import read
    from mxdev.processing import write
    from mxdev.state import State

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create different subdirectories
        (tmp_path / "reqs").mkdir()
        (tmp_path / "constraints").mkdir()

        # Create input constraints file
        constraints_in = tmp_path / "constraints.txt"
        constraints_in.write_text("requests==2.28.0\nurllib3==1.26.9\n")

        # Create input requirements file with a constraint reference
        requirements_in = tmp_path / "requirements.txt"
        requirements_in.write_text("-c constraints.txt\nrequests\n")

        config_file = tmp_path / "mx.ini"
        config_file.write_text(
            """[settings]
requirements-in = requirements.txt
requirements-out = reqs/requirements.txt
constraints-out = constraints/constraints.txt
"""
        )

        config = Configuration(str(config_file))
        state = State(configuration=config)

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
