# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ADB GUI Tool** - A modern Windows desktop application for Android Debug Bridge (ADB) operations built with **PySide6** (PyQt6 compatible). Features plugin architecture, MVP pattern, and event-driven design.

**Tech Stack**: Python 3.8+, PySide6 (PyQt6), ADB, Scrcpy

## Architecture

### Layered Architecture

```
├── Core Layer        # ADB/Scrcpy managers
├── Framework Layer   # Plugin system, Event Bus, MVP
├── UI Layer          # Themes, Dialogs, Widgets
├── Utils Layer       # Config, Logcat, Helpers
└── Plugins           # Extensible plugin modules
```

### Key Patterns

**MVP (Model-View-Presenter)**:
- Models: `framework/mvp/models.py` (DeviceModel, ADBModel, AppModel, FileModel)
- Views: Implement `MainViewInterface` from `framework/mvp/presenter.py`
- Presenters: Coordinate Model ↔ View interactions

**Plugin System**:
- Interface: `framework/plugin/plugin_interface.py` - All plugins must implement `PluginInterface`
- Manager: `framework/plugin/plugin_manager.py` - Handles lifecycle (load/unload/discover)
- API: `framework/plugin/plugin_api.py` - Main program capabilities exposed to plugins
- Plugins in: `plugins/` directory

**Event Bus**:
- Location: `framework/event/event_bus.py`
- Pattern: Pub/Sub for decoupled communication between components
- Event types defined in `EventTypes` enum
- Plugins subscribe to events via `event_bus.subscribe(EventTypes.*, callback)`

### Directory Structure

```
├── core/                    # Core ADB/Scrcpy managers
├── framework/
│   ├── event/              # Event bus system
│   ├── mvp/                # MVP architecture components
│   └── plugin/             # Plugin infrastructure
├── ui/                     # Theme manager, markdown renderer
├── dialogs/                # Feature-specific dialog windows
├── plugins/                # Plugin implementations
├── utils/                  # Config manager, logcat, helpers
├── config/                 # JSON config files
├── scripts/                # Build, release, version management
├── tests/                  # Unit and integration tests
└── extensions/             # External tools (jadx, Ghost Downloader)
```

## Common Development Tasks

### Running the Application

```bash
# Development mode (console output visible)
python adb_gui.py

# Check version
python scripts/version.py --version
```

### Building & Release

**Version Management**:
```bash
cd scripts

# View current version
python version.py --version

# Bump version (major.minor.patch)
python version.py --bump patch   # 2.0.0 → 2.0.1
python version.py --bump minor   # 2.0.1 → 2.1.0
python version.py --bump major   # 2.1.0 → 3.0.0
```

**Build EXE**:
```bash
cd scripts

# Directory mode (faster startup, multiple files)
python build.py

# Single-file mode (easier distribution)
python build.py --onefile

# With console window (for debugging)
python build.py --console

# Clean build artifacts
python build.py --clean
```

**Complete Release**:
```bash
cd scripts

# Standard release (directory mode)
python release.py

# Single-file release
python release.py --onefile

# Auto-bump version before release
python release.py --bump patch

# Quick release (using batch script)
release_quick.bat
```

Build output: `scripts/dist/`
Release output: `release/v{version}_{date}/`

See `scripts/README_RELEASE.md` for complete release workflow.

### Testing

```bash
# Run all tests
python -m pytest tests/

# Unit tests only
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# Single test file
python -m pytest tests/unit/test_plugin_system.py

# Quick test (for rapid iteration)
python tests/quick_test.py
```

### Plugin Development

**Create a new plugin**:

1. Create file in `plugins/` directory (e.g., `my_plugin.py`)
2. Implement `PluginInterface`:

```python
from framework.plugin import PluginInterface, PluginMetadata
from framework.event import EventTypes

class MyPlugin(PluginInterface):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my_plugin",
            name="My Plugin",
            version="1.0.0",
            author="Your Name",
            description="Plugin description",
            dependencies=[],  # Other plugin IDs
            api_version="1.0"
        )

    def on_load(self, api, event_bus) -> bool:
        self._api = api
        self._event_bus = event_bus
        # Subscribe to events
        event_bus.subscribe(EventTypes.DEVICE_CONNECTED, self._on_device_connected)
        return True

    def on_unload(self) -> bool:
        # Cleanup resources
        return True

    def _on_device_connected(self, event):
        self._api.log_info(f"Device connected: {event.data}")
```

3. Plugin auto-loaded on startup (if `config/config.json` → `extensions.plugins.auto_load = true`)

**Plugin API capabilities** (via `api` parameter):
- `api.log_info(msg, source)` - Log info message
- `api.log_error(msg, source)` - Log error message
- `api.show_message(msg, type)` - Show UI message
- `api.get_current_device()` - Get selected device
- `api.run_adb_command(cmd)` - Execute ADB command
- See `framework/plugin/plugin_api.py` for full API

**Event types** (subscribe via event_bus):
- `EventTypes.DEVICE_CONNECTED` - New device connected
- `EventTypes.DEVICE_DISCONNECTED` - Device disconnected
- `EventTypes.DEVICE_LIST_UPDATED` - Device list changed
- `EventTypes.DEVICE_SELECTED` - User selected device
- See `framework/event/event_bus.py` for all event types

Reference: `docs/PLUGIN_DEVELOPMENT_GUIDE.md`

## Configuration

**Main config**: `config/config.json`
- App settings (name, version, dark_mode)
- ADB settings (refresh interval)
- Extensions paths (adb.exe, scrcpy.exe, jadx)
- Plugin settings (auto_load, enabled/disabled)

**Custom buttons**: `config/buttons_cmd.json`
- User-defined command buttons with drag-drop reordering

**Plugin config**: `plugins/plugins_config.json`
- Plugin-specific settings

## Critical Files

**Entry point**: `adb_gui.py` - Main window and application bootstrap

**Core managers**:
- `core/adb_manager.py` - ADB operations wrapper
- `core/scrcpy_manager.py` - Screen mirroring integration

**Plugin infrastructure**:
- `framework/plugin/plugin_manager.py` - Plugin lifecycle
- `framework/plugin/plugin_interface.py` - Base interface
- `framework/plugin/plugin_api.py` - API contract

**Event system**:
- `framework/event/event_bus.py` - Pub/Sub implementation

**MVP components**:
- `framework/mvp/models.py` - Data models
- `framework/mvp/presenter.py` - Presenter layer

**Version & Build**:
- `scripts/version.py` - Version management
- `scripts/build.py` - PyInstaller packaging
- `scripts/release.py` - Release automation

## Development Notes

### Qt Compatibility

The codebase uses **PySide6** by default but maintains **PyQt6** compatibility:
- Signal/Slot aliases: `pyqtSignal = Signal`, `pyqtSlot = Slot`
- Compatible imports in `utils/qt_compat.py`

### PySide6 vs PyQt6

Both are supported. To switch:
1. Update imports in `adb_gui.py`
2. Update `requirements.txt`
3. Rebuild

### Logging

Logs automatically saved to: `logs/adb_gui_{timestamp}.log`

Config in `adb_gui.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(...)]
)
```

### Extension Tools

External tools in `extensions/`:
- `android-tools-win-v34/` - ADB binaries
- `scrcpy-win64-*/` - Screen mirroring tool
- `jadx_decompiler/` - APK decompiler
- `Ghost-Downloader-3/` - Download manager (embedded as plugin)

Paths configured in `config/config.json` → `extensions.items`

### Adding New Features

**Plugin approach (recommended)**:
1. Implement as plugin in `plugins/`
2. Subscribe to relevant events
3. Use Plugin API for UI/ADB interactions

**Direct integration**:
1. Add dialog in `dialogs/`
2. Add model in `framework/mvp/models.py`
3. Update presenter in `framework/mvp/presenter.py`
4. Wire up UI in `adb_gui.py`

## Known Issues

- **Logcat streaming**: May not work on some devices due to ADB version/device compatibility
  - Workaround: Use shell command `logcat -d` for one-time dump

## Build Configuration

PyInstaller spec in `scripts/build.py`:
- Console mode: `--console` flag (shows terminal for debugging)
- Windowed mode: Default (no console window)
- Single-file: `--onefile` flag
- Directory mode: Default (faster startup)

Hidden imports and data files managed in `build.py` → `Builder.build()` method.
