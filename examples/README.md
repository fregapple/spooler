# Examples

This folder contains manual testing scripts and demos. These are **not** automated tests.

## Files

### `device_test.py`
Manual script to test AirPurifier device connection and status.
- **Purpose**: Verify device communication with real hardware
- **Usage**: Update device credentials and run `python examples/device_test.py`

### `sdcp_test.py`
Manual WebSocket client for testing SDCP protocol commands.
- **Purpose**: Interactive testing of printer WebSocket commands (list files, delete files, etc.)
- **Usage**: Update `SDCP_URL` and `MACHINE_ID`, then run `python examples/sdcp_test.py`
- **Requirements**: Live printer connection

### `ui_demo.py` (186 lines)
Textual TUI application demo showing dashboard interface.
- **Purpose**: Visual demonstration of the dashboard UI
- **Usage**: Run `python examples/ui_demo.py` to see the interface
- **Note**: This is a UI mockup, not connected to real data

## Automated Tests

For automated unit tests, see `/spooler/tests/` which contains pytest-based tests.
