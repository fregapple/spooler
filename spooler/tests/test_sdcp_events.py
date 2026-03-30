"""Unit tests for SDCP event helpers."""
from unittest.mock import MagicMock, patch

from sdcp.events import _refresh_pending_job_from_file, _resolve_pending_job


def test_resolve_pending_job_supports_basename_lookup():
    """Should match pending jobs when SDCP sends path-prefixed filenames."""
    jobs = {"print.gcode": {"filament_presets": ["PLA"], "filament_g_list": [20.0]}}

    with patch("sdcp.events.pending_jobs", jobs):
        result = _resolve_pending_job("/mnt/printer/jobs/print.gcode")

    assert result == jobs["print.gcode"]


def test_refresh_pending_job_from_file_updates_pending_jobs(temp_dir):
    """Should parse metadata directly from watch folder when needed."""
    gcode_file = temp_dir / "job.gcode"
    gcode_file.write_text("G28")

    mock_meta = {
        "filament_presets": ["Test"],
        "filament_g_list": [12.3],
        "path": str(gcode_file),
    }

    logger = MagicMock()

    with patch("sdcp.events.pending_jobs", {}):
        with patch("sdcp.events.parse_gcode_metadata", return_value=mock_meta):
            result = _refresh_pending_job_from_file("job.gcode", str(temp_dir), logger)

    assert result == mock_meta


def test_refresh_pending_job_from_file_returns_none_when_missing(temp_dir):
    """Should return None if watch folder file does not exist yet."""
    logger = MagicMock()

    with patch("sdcp.events.pending_jobs", {}):
        result = _refresh_pending_job_from_file("missing.gcode", str(temp_dir), logger)

    assert result is None
