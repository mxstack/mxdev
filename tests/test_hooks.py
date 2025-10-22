from unittest.mock import MagicMock
from unittest.mock import patch


def test_hook_class_exists():
    """Test that Hook class is defined."""
    from mxdev.hooks import Hook

    assert Hook is not None
    assert hasattr(Hook, "read")
    assert hasattr(Hook, "write")
    # namespace is a type annotation, check it exists in annotations
    assert "namespace" in Hook.__annotations__


def test_hook_class_can_be_instantiated():
    """Test Hook class can be instantiated."""
    from mxdev.hooks import Hook

    hook = Hook()
    assert hook is not None
    assert callable(hook.read)
    assert callable(hook.write)


def test_hook_read_method():
    """Test Hook class has read method."""
    from mxdev.config import Configuration
    from mxdev.hooks import Hook
    from mxdev.state import State

    import pathlib

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))
    state = State(configuration=config)

    hook = Hook()
    # Should be callable without error (does nothing by default)
    result = hook.read(state)
    assert result is None


def test_hook_write_method():
    """Test Hook class has write method."""
    from mxdev.config import Configuration
    from mxdev.hooks import Hook
    from mxdev.state import State

    import pathlib

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))
    state = State(configuration=config)

    hook = Hook()
    # Should be callable without error (does nothing by default)
    result = hook.write(state)
    assert result is None


def test_load_hooks_no_hooks():
    """Test load_hooks returns empty list when no hooks registered."""
    from mxdev.hooks import load_hooks

    with patch("mxdev.hooks.load_eps_by_group", return_value=[]):
        hooks = load_hooks()
        assert hooks == []


def test_load_hooks_with_hooks():
    """Test load_hooks loads hooks from entry points."""
    from mxdev.hooks import load_hooks

    # Create mock entry point
    mock_ep = MagicMock()
    mock_ep.name = "hook"
    mock_hook_class = MagicMock()
    mock_hook_instance = MagicMock()
    mock_hook_class.return_value = mock_hook_instance
    mock_ep.load.return_value = mock_hook_class

    with patch("mxdev.hooks.load_eps_by_group", return_value=[mock_ep]):
        hooks = load_hooks()
        assert len(hooks) == 1
        assert hooks[0] == mock_hook_instance
        mock_ep.load.assert_called_once()


def test_load_hooks_filters_by_name():
    """Test load_hooks only loads entry points named 'hook'."""
    from mxdev.hooks import load_hooks

    # Create mock entry points with different names
    mock_ep_hook = MagicMock()
    mock_ep_hook.name = "hook"
    mock_hook_class = MagicMock()
    mock_hook_instance = MagicMock()
    mock_hook_class.return_value = mock_hook_instance
    mock_ep_hook.load.return_value = mock_hook_class

    mock_ep_other = MagicMock()
    mock_ep_other.name = "other"

    with patch("mxdev.hooks.load_eps_by_group", return_value=[mock_ep_hook, mock_ep_other]):
        hooks = load_hooks()
        assert len(hooks) == 1
        assert hooks[0] == mock_hook_instance
        mock_ep_hook.load.assert_called_once()
        mock_ep_other.load.assert_not_called()


def test_read_hooks():
    """Test read_hooks calls read on all hooks."""
    from mxdev.config import Configuration
    from mxdev.hooks import read_hooks
    from mxdev.state import State

    import pathlib

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))
    state = State(configuration=config)

    mock_hook1 = MagicMock()
    mock_hook2 = MagicMock()
    hooks = [mock_hook1, mock_hook2]

    read_hooks(state, hooks)

    mock_hook1.read.assert_called_once_with(state)
    mock_hook2.read.assert_called_once_with(state)


def test_read_hooks_empty_list():
    """Test read_hooks with empty hooks list."""
    from mxdev.config import Configuration
    from mxdev.hooks import read_hooks
    from mxdev.state import State

    import pathlib

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))
    state = State(configuration=config)

    # Should not raise error
    read_hooks(state, [])


def test_write_hooks():
    """Test write_hooks calls write on all hooks."""
    from mxdev.config import Configuration
    from mxdev.hooks import write_hooks
    from mxdev.state import State

    import pathlib

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))
    state = State(configuration=config)

    mock_hook1 = MagicMock()
    mock_hook2 = MagicMock()
    hooks = [mock_hook1, mock_hook2]

    write_hooks(state, hooks)

    mock_hook1.write.assert_called_once_with(state)
    mock_hook2.write.assert_called_once_with(state)


def test_write_hooks_empty_list():
    """Test write_hooks with empty hooks list."""
    from mxdev.config import Configuration
    from mxdev.hooks import write_hooks
    from mxdev.state import State

    import pathlib

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "basic_config.ini"))
    state = State(configuration=config)

    # Should not raise error
    write_hooks(state, [])


def test_has_importlib_entrypoints_constant():
    """Test HAS_IMPORTLIB_ENTRYPOINTS constant is defined."""
    from mxdev.hooks import HAS_IMPORTLIB_ENTRYPOINTS

    # Should be a boolean
    assert isinstance(HAS_IMPORTLIB_ENTRYPOINTS, bool)
