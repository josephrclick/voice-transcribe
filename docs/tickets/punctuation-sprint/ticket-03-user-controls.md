# Ticket #03: User Controls for Punctuation Settings

**Priority**: P3 - User Experience  
**Assignee**: @python-gtk-developer  
**Sprint**: Punctuation Sprint  
**Estimated Effort**: 3 days

## Problem Statement

Users currently have no control over punctuation behavior and cannot adjust sensitivity based on their speaking style, use case, or environment. Need intuitive UI controls integrated into the existing GTK interface.

## Technical Details

**Integration Points**:

- Main UI: Need settings panel or preferences dialog
- Configuration: `/home/joe/dev/projects/voice-transcribe-dev/config.json` schema updates
- Service Integration: Connect UI to `DeepgramService` and `PunctuationProcessor`

**Current Config Structure**:

```json
{
  "prompt_mode_enabled": false,
  "enhancement_style": "detailed",
  "history_enabled": true
  // Need to add punctuation controls here
}
```

## Solution Design

### 1. Punctuation Settings Panel

Add dedicated punctuation controls to the main interface:

```python
class PunctuationControlsWidget(Gtk.Box):
    """Widget for punctuation sensitivity controls"""

    def __init__(self, app_instance):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.app = app_instance

        # Punctuation sensitivity slider
        self.sensitivity_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 3, 1
        )
        self.sensitivity_scale.set_digits(0)
        self.sensitivity_scale.set_draw_value(True)
        self.sensitivity_scale.add_mark(0, Gtk.PositionType.BOTTOM, "Off")
        self.sensitivity_scale.add_mark(1, Gtk.PositionType.BOTTOM, "Minimal")
        self.sensitivity_scale.add_mark(2, Gtk.PositionType.BOTTOM, "Balanced")
        self.sensitivity_scale.add_mark(3, Gtk.PositionType.BOTTOM, "Aggressive")

        # Endpointing adjustment
        self.endpointing_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 100, 1000, 50
        )
        self.endpointing_scale.set_digits(0)
        self.endpointing_scale.set_value(400)  # Default 400ms

        # Smart merge toggle
        self.smart_merge_switch = Gtk.Switch()
        self.smart_merge_switch.set_active(True)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        """Build the punctuation controls UI"""
        # Sensitivity section
        sensitivity_frame = Gtk.Frame(label="Punctuation Sensitivity")
        sensitivity_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sensitivity_box.set_margin_top(6)
        sensitivity_box.set_margin_bottom(6)
        sensitivity_box.set_margin_start(12)
        sensitivity_box.set_margin_end(12)

        sensitivity_label = Gtk.Label(label="Controls how aggressively sentences are split")
        sensitivity_label.set_xalign(0)
        sensitivity_label.get_style_context().add_class("dim-label")

        sensitivity_box.pack_start(sensitivity_label, False, False, 0)
        sensitivity_box.pack_start(self.sensitivity_scale, False, False, 0)
        sensitivity_frame.add(sensitivity_box)

        # Advanced settings expander
        advanced_expander = Gtk.Expander(label="Advanced Settings")
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        advanced_box.set_margin_top(6)
        advanced_box.set_margin_bottom(6)
        advanced_box.set_margin_start(12)
        advanced_box.set_margin_end(12)

        # Endpointing control
        endpointing_label = Gtk.Label(label="Pause Detection Threshold (ms)")
        endpointing_label.set_xalign(0)
        advanced_box.pack_start(endpointing_label, False, False, 0)
        advanced_box.pack_start(self.endpointing_scale, False, False, 0)

        # Smart merge control
        merge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        merge_label = Gtk.Label(label="Smart Fragment Merging")
        merge_label.set_xalign(0)
        merge_box.pack_start(merge_label, True, True, 0)
        merge_box.pack_start(self.smart_merge_switch, False, False, 0)
        advanced_box.pack_start(merge_box, False, False, 0)

        advanced_expander.add(advanced_box)

        self.pack_start(sensitivity_frame, False, False, 0)
        self.pack_start(advanced_expander, False, False, 0)
```

### 2. Integration with Main Application

Modify main application to include punctuation controls:

```python
class VoiceTranscribeApp:
    def _build_ui(self):
        # ... existing UI building ...

        # Add punctuation controls to main layout
        self.punctuation_controls = PunctuationControlsWidget(self)

        # Add to settings panel or create dedicated tab
        if hasattr(self, 'settings_notebook'):
            # Add as new tab if tabbed interface exists
            self.settings_notebook.append_page(
                self.punctuation_controls,
                Gtk.Label(label="Punctuation")
            )
        else:
            # Add to main vertical box
            self.main_vbox.pack_start(self.punctuation_controls, False, False, 0)

    def _on_punctuation_setting_changed(self, widget, value):
        """Handle punctuation setting changes"""
        # Update configuration
        self.config['punctuation_sensitivity'] = value
        self._save_config()

        # Apply to active service if recording
        if hasattr(self, 'deepgram_service') and self.deepgram_service.is_connected():
            # Restart service with new settings
            self._restart_deepgram_service()

    def _restart_deepgram_service(self):
        """Restart Deepgram service with updated punctuation settings"""
        if self.recording:
            # Gracefully restart without interrupting user
            old_service = self.deepgram_service
            self._setup_deepgram_service()  # Create new service with current config

            # Finish old connection and start new one
            old_service.finalize()
            self.deepgram_service.start()
```

### 3. Configuration Management

Extend configuration schema and handling:

```python
class ConfigurationManager:
    """Manage punctuation-related configuration"""

    DEFAULT_PUNCTUATION_CONFIG = {
        "punctuation_sensitivity": 2,  # 0=off, 1=minimal, 2=balanced, 3=aggressive
        "endpointing_ms": 400,
        "smart_merge_enabled": True,
        "merge_threshold_ms": 800,
        "min_sentence_length": 3,
        "auto_adjust_enabled": False  # Future: learn from user corrections
    }

    def load_punctuation_config(self):
        """Load punctuation settings with migration support"""
        config = self.load_config()

        # Migrate old config if needed
        if 'punctuation_sensitivity' not in config:
            config.update(self.DEFAULT_PUNCTUATION_CONFIG)
            self.save_config(config)

        return config

    def get_punctuation_level_name(self, level: int) -> str:
        """Convert numeric level to string name"""
        return ["off", "minimal", "balanced", "aggressive"][level]
```

## Implementation Tasks

### Phase 1: UI Components (1.5 days)

- [ ] Create `PunctuationControlsWidget` class
- [ ] Design responsive layout with sensitivity slider
- [ ] Add advanced settings expander with endpointing control
- [ ] Implement smart merge toggle switch
- [ ] Add tooltips and help text

### Phase 2: Integration & Persistence (1 day)

- [ ] Integrate controls into main application window
- [ ] Connect UI events to configuration updates
- [ ] Implement configuration migration for existing users
- [ ] Add validation for setting ranges

### Phase 3: Real-time Updates (0.5 days)

- [ ] Enable live updates during recording sessions
- [ ] Implement graceful service restart when settings change
- [ ] Add visual feedback for setting changes
- [ ] Handle edge cases (rapid setting changes, connection errors)

## User Experience Design

### 1. Default Behavior

- Start with "Balanced" sensitivity (level 2)
- Smart merge enabled by default
- 400ms endpointing threshold
- Advanced settings collapsed initially

### 2. Visual Feedback

- Show current setting level in real-time
- Disable controls during critical recording moments
- Provide immediate visual feedback for changes
- Use tooltips to explain technical settings

### 3. Accessibility

- Keyboard navigation support
- Screen reader compatible labels
- High contrast support
- Reasonable tab order

## Testing Strategy

### Manual Testing Scenarios

1. **Setting Changes During Recording**: Change sensitivity while actively recording → Should apply gracefully
2. **Configuration Persistence**: Restart app → Settings should be preserved
3. **Migration Testing**: Test with old config.json → Should migrate seamlessly
4. **Edge Case Testing**: Try invalid values, rapid changes → Should handle gracefully

### Automated Tests

```python
def test_punctuation_controls_widget():
    """Test punctuation controls widget functionality"""
    app = MockVoiceTranscribeApp()
    controls = PunctuationControlsWidget(app)

    # Test sensitivity scale
    controls.sensitivity_scale.set_value(1)
    assert controls.get_punctuation_level() == "minimal"

    # Test endpointing adjustment
    controls.endpointing_scale.set_value(500)
    assert controls.get_endpointing_ms() == 500

def test_configuration_migration():
    """Test migration of old configuration files"""
    old_config = {"prompt_mode_enabled": False}
    manager = ConfigurationManager()

    migrated = manager.migrate_punctuation_config(old_config)
    assert "punctuation_sensitivity" in migrated
    assert migrated["punctuation_sensitivity"] == 2  # Default balanced
```

## Configuration Schema Updates

```json
{
  "prompt_mode_enabled": false,
  "enhancement_style": "detailed",
  "history_enabled": true,

  // New punctuation settings
  "punctuation_settings": {
    "sensitivity_level": 2,
    "endpointing_ms": 400,
    "smart_merge_enabled": true,
    "merge_threshold_ms": 800,
    "min_sentence_length": 3,
    "auto_adjust_enabled": false
  },

  // Migration marker
  "config_version": "3.4.0"
}
```

## Dependencies

- **Requires**: Ticket #01 (API Configuration) - Backend punctuation controls
- **Requires**: Ticket #02 (Post-processing) - Smart merge functionality
- **Integration**: GTK UI framework, configuration system

## Risks & Mitigations

1. **Risk**: UI changes affect existing user workflows
   - **Mitigation**: Make controls optional, preserve existing defaults

2. **Risk**: Real-time setting changes disrupt recording
   - **Mitigation**: Implement graceful service restart, user feedback

3. **Risk**: Configuration migration breaks existing setups
   - **Mitigation**: Thorough testing, rollback capability

## Definition of Done

- [ ] Punctuation controls widget implemented and integrated
- [ ] All sensitivity levels working with real-time updates
- [ ] Configuration persistence and migration working
- [ ] UI is responsive and accessible
- [ ] Manual testing confirms smooth user experience
- [ ] Automated tests cover all major functionality
- [ ] Documentation updated with new features
- [ ] Code review completed and approved
