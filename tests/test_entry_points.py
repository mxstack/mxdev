from unittest.mock import MagicMock
from unittest.mock import patch


def test_has_importlib_entrypoints_constant():
    """Test HAS_IMPORTLIB_ENTRYPOINTS constant is defined."""
    from mxdev.entry_points import HAS_IMPORTLIB_ENTRYPOINTS

    # Should be a boolean
    assert isinstance(HAS_IMPORTLIB_ENTRYPOINTS, bool)


def test_load_eps_by_group_with_python312():
    """Test load_eps_by_group with Python 3.12+ API (group parameter)."""
    from mxdev.entry_points import load_eps_by_group

    # Mock entry points for Python 3.12+ API
    mock_ep1 = MagicMock()
    mock_ep1.name = "test-ep1"
    mock_ep2 = MagicMock()
    mock_ep2.name = "test-ep2"
    mock_eps = [mock_ep1, mock_ep2]

    with patch("mxdev.entry_points.HAS_IMPORTLIB_ENTRYPOINTS", True):
        with patch("mxdev.entry_points.entry_points", return_value=mock_eps) as mock_entry_points:
            result = load_eps_by_group("test-group")

            # Should call entry_points with group parameter
            mock_entry_points.assert_called_once_with(group="test-group")
            # Should return unique list
            assert len(result) == 2
            assert mock_ep1 in result
            assert mock_ep2 in result


def test_load_eps_by_group_with_old_python():
    """Test load_eps_by_group with Python <3.12 API (no group parameter)."""
    from mxdev.entry_points import load_eps_by_group

    # Mock entry points for older Python API
    mock_ep1 = MagicMock()
    mock_ep1.name = "test-ep1"
    mock_ep2 = MagicMock()
    mock_ep2.name = "test-ep2"

    mock_eps_dict = {"test-group": [mock_ep1, mock_ep2], "other-group": []}

    with patch("mxdev.entry_points.HAS_IMPORTLIB_ENTRYPOINTS", False):
        with patch("mxdev.entry_points.entry_points", return_value=mock_eps_dict) as mock_entry_points:
            result = load_eps_by_group("test-group")

            # Should call entry_points without parameters
            mock_entry_points.assert_called_once_with()
            # Should return unique list from the group
            assert len(result) == 2
            assert mock_ep1 in result
            assert mock_ep2 in result


def test_load_eps_by_group_group_not_found():
    """Test load_eps_by_group when group doesn't exist (old Python API)."""
    from mxdev.entry_points import load_eps_by_group

    mock_eps_dict = {"other-group": []}

    with patch("mxdev.entry_points.HAS_IMPORTLIB_ENTRYPOINTS", False):
        with patch("mxdev.entry_points.entry_points", return_value=mock_eps_dict):
            result = load_eps_by_group("nonexistent-group")

            # Should return empty list when group not found
            assert result == []


def test_load_eps_by_group_deduplicates():
    """Test load_eps_by_group removes duplicates using set()."""
    from mxdev.entry_points import load_eps_by_group

    # Create mock entry points - same object twice to test deduplication
    mock_ep = MagicMock()
    mock_ep.name = "test-ep"
    # Make it hashable for set()
    mock_ep.__hash__ = lambda self: hash("test-ep")
    mock_eps = [mock_ep, mock_ep]  # Duplicate

    with patch("mxdev.entry_points.HAS_IMPORTLIB_ENTRYPOINTS", True):
        with patch("mxdev.entry_points.entry_points", return_value=mock_eps):
            result = load_eps_by_group("test-group")

            # Should deduplicate - only one entry
            assert len(result) == 1
            assert mock_ep in result


def test_load_eps_by_group_empty_group():
    """Test load_eps_by_group with empty group results."""
    from mxdev.entry_points import load_eps_by_group

    with patch("mxdev.entry_points.HAS_IMPORTLIB_ENTRYPOINTS", True):
        with patch("mxdev.entry_points.entry_points", return_value=[]):
            result = load_eps_by_group("empty-group")

            # Should return empty list
            assert result == []


def test_load_eps_by_group_old_python_empty_group():
    """Test load_eps_by_group with empty group on old Python API."""
    from mxdev.entry_points import load_eps_by_group

    mock_eps_dict = {"test-group": []}

    with patch("mxdev.entry_points.HAS_IMPORTLIB_ENTRYPOINTS", False):
        with patch("mxdev.entry_points.entry_points", return_value=mock_eps_dict):
            result = load_eps_by_group("test-group")

            # Should return empty list
            assert result == []
