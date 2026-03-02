"""Unit tests for watchers and file handlers."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGcodeHandler:
    """Tests for G-code file watcher handler."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_logger, temp_dir):
        """Create a GcodeHandler instance."""
        from watchers.gcode_handler import GcodeHandler
        return GcodeHandler(mock_logger, str(temp_dir))

    def test_ignores_directories(self, handler, temp_dir):
        """Should ignore directory creation events."""
        from watchdog.events import FileCreatedEvent
        
        event = FileCreatedEvent(str(temp_dir / "subdir"))
        event.is_directory = True
        
        with patch('watchers.gcode_handler.wait_for_file_complete'):
            with patch('watchers.gcode_handler.parse_gcode_metadata'):
                handler.on_created(event)
        
        # Should not log anything for directory
        handler.log.info.assert_not_called()

    def test_ignores_non_gcode_files(self, handler, temp_dir):
        """Should ignore non-gcode files."""
        from watchdog.events import FileCreatedEvent
        
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("not gcode")
        event = FileCreatedEvent(str(txt_file))
        event.is_directory = False
        
        with patch('watchers.gcode_handler.wait_for_file_complete'):
            with patch('watchers.gcode_handler.parse_gcode_metadata'):
                handler.on_created(event)
        
        # Should not process non-gcode files
        handler.log.info.assert_not_called()

    def test_processes_gcode_file(self, handler, temp_dir):
        """Should process .gcode files."""
        from watchdog.events import FileCreatedEvent
        
        gcode_file = temp_dir / "test.gcode"
        gcode_file.write_text("; filament_settings_id = \"Test\"\n; filament used [g] = 100.0\n")
        event = FileCreatedEvent(str(gcode_file))
        event.is_directory = False
        
        with patch('watchers.gcode_handler.wait_for_file_complete'):
            with patch('watchers.gcode_handler.parse_gcode_metadata') as mock_parse:
                mock_parse.return_value = {
                    'filament_presets': ['Test'],
                    'filament_g_list': [100.0],
                    'path': str(gcode_file)
                }
                with patch('watchers.gcode_handler.pending_jobs', {}):
                    handler.on_created(event)
        
        # Should log file detection
        handler.log.info.assert_called()

    def test_case_insensitive_extension(self, handler, temp_dir):
        """Should handle .GCODE, .GCode, etc."""
        from watchdog.events import FileCreatedEvent
        
        for ext in ['.GCODE', '.GCode', '.gcode', '.Gcode']:
            gcode_file = temp_dir / f"test{ext}"
            gcode_file.write_text("G28")
            event = FileCreatedEvent(str(gcode_file))
            event.is_directory = False
            
            with patch('watchers.gcode_handler.wait_for_file_complete'):
                with patch('watchers.gcode_handler.parse_gcode_metadata') as mock_parse:
                    mock_parse.return_value = {'filament_presets': [], 'filament_g_list': [], 'path': str(gcode_file)}
                    with patch('watchers.gcode_handler.pending_jobs', {}):
                        handler.on_created(event)
            
            # Should process all variations
            assert handler.log.info.called

    def test_waits_for_file_complete(self, handler, temp_dir):
        """Should wait for file to finish writing."""
        from watchdog.events import FileCreatedEvent
        
        gcode_file = temp_dir / "large.gcode"
        gcode_file.write_text("G28")
        event = FileCreatedEvent(str(gcode_file))
        event.is_directory = False
        
        with patch('watchers.gcode_handler.wait_for_file_complete') as mock_wait:
            with patch('watchers.gcode_handler.parse_gcode_metadata') as mock_parse:
                mock_parse.return_value = {'filament_presets': [], 'filament_g_list': [], 'path': str(gcode_file)}
                with patch('watchers.gcode_handler.pending_jobs', {}):
                    handler.on_created(event)
            
            # Should call wait_for_file_complete
            mock_wait.assert_called_once_with(str(gcode_file))

    def test_adds_to_pending_jobs(self, handler, temp_dir):
        """Should add parsed metadata to pending_jobs dict."""
        from watchdog.events import FileCreatedEvent
        
        gcode_file = temp_dir / "test.gcode"
        gcode_file.write_text("G28")
        event = FileCreatedEvent(str(gcode_file))
        event.is_directory = False
        
        mock_metadata = {
            'filament_presets': ['Test Filament'],
            'filament_g_list': [50.0],
            'path': str(gcode_file)
        }
        
        with patch('watchers.gcode_handler.wait_for_file_complete'):
            with patch('watchers.gcode_handler.parse_gcode_metadata', return_value=mock_metadata):
                with patch('watchers.gcode_handler.pending_jobs', {}) as mock_jobs:
                    handler.on_created(event)
                    
                    # Should add to pending_jobs with filename as key
                    assert 'test.gcode' in mock_jobs
                    assert mock_jobs['test.gcode'] == mock_metadata
