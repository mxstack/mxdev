import pathlib
import pytest
from io import StringIO


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
            "install-mode": "direct",
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
            "install-mode": "direct",
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages)

    content = outfile.read_text()
    assert "-e ./sources/example.package" in content
    assert "skip.package" not in content  # skip mode should not be written
    assert "-e ./sources/extras.package/packages/core[test,docs]" in content


def test_write_dev_sources_empty():
    """Test write_dev_sources with no packages."""
    from mxdev.processing import write_dev_sources
    from io import StringIO

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


def test_write_dev_overrides_source_wins():
    """Test write_dev_overrides comments out override when package is in sources."""
    from mxdev.processing import write_dev_overrides

    overrides = {
        "my.package": "my.package==1.0.0",
    }

    outfile = pathlib.Path("/tmp/test_override_source_wins.txt")
    with open(outfile, "w") as fio:
        write_dev_overrides(fio, overrides, package_keys=["my.package"])

    content = outfile.read_text()
    assert "# my.package==1.0.0 IGNORE mxdev constraint override" in content
    outfile.unlink()


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
    from mxdev.processing import write_main_package
    from io import StringIO

    settings = {}
    fio = StringIO()
    write_main_package(fio, settings)

    # Should not write anything when main-package not set
    assert fio.getvalue() == ""


def test_write(tmp_path):
    """Test write function creates output files correctly."""
    from mxdev.processing import write
    from mxdev.state import State
    from mxdev.config import Configuration

    # Create a simple config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
version-overrides =
    requests==2.28.0
""")

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
    from mxdev.processing import write
    from mxdev.state import State
    from mxdev.config import Configuration

    # Create a simple config without constraints
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
""")

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
