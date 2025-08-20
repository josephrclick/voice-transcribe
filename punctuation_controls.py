#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import logging

logger = logging.getLogger(__name__)


class PunctuationControlsWidget(Gtk.Box):
    """Widget for punctuation sensitivity controls"""

    def __init__(self, app_instance):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.app = app_instance
        
        # Punctuation sensitivity slider (0=off, 1=minimal, 2=balanced, 3=aggressive)
        sensitivity_adjustment = Gtk.Adjustment(
            value=2,  # Default to balanced
            lower=0,
            upper=3,
            step_increment=1,
            page_increment=1,
            page_size=0
        )
        self.sensitivity_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=sensitivity_adjustment
        )
        self.sensitivity_scale.set_digits(0)
        self.sensitivity_scale.set_draw_value(False)
        self.sensitivity_scale.set_hexpand(True)
        
        # Add marks for each sensitivity level
        self.sensitivity_scale.add_mark(0, Gtk.PositionType.BOTTOM, "Off")
        self.sensitivity_scale.add_mark(1, Gtk.PositionType.BOTTOM, "Minimal")
        self.sensitivity_scale.add_mark(2, Gtk.PositionType.BOTTOM, "Balanced")
        self.sensitivity_scale.add_mark(3, Gtk.PositionType.BOTTOM, "Aggressive")
        
        # Endpointing adjustment (100-1000ms)
        endpointing_adjustment = Gtk.Adjustment(
            value=400,  # Default 400ms
            lower=100,
            upper=1000,
            step_increment=50,
            page_increment=100,
            page_size=0
        )
        self.endpointing_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=endpointing_adjustment
        )
        self.endpointing_scale.set_digits(0)
        self.endpointing_scale.set_draw_value(True)
        self.endpointing_scale.set_hexpand(True)
        
        # Smart merge toggle switch
        self.smart_merge_switch = Gtk.Switch()
        self.smart_merge_switch.set_active(True)  # Default enabled
        
        # Build the UI
        self._build_ui()
        self._connect_signals()
        
        # Load initial values from config if available
        self._load_config_values()

    def _build_ui(self):
        """Build the punctuation controls UI"""
        # Main container with padding
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(6)
        main_box.set_margin_bottom(6)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        
        # Sensitivity section
        sensitivity_frame = Gtk.Frame()
        sensitivity_frame.set_label("Punctuation Sensitivity")
        sensitivity_frame.set_shadow_type(Gtk.ShadowType.NONE)
        
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
        endpointing_help = Gtk.Label(label="Lower values split sentences more frequently")
        endpointing_help.set_xalign(0)
        endpointing_help.get_style_context().add_class("dim-label")
        
        advanced_box.pack_start(endpointing_label, False, False, 0)
        advanced_box.pack_start(endpointing_help, False, False, 0)
        advanced_box.pack_start(self.endpointing_scale, False, False, 0)
        
        # Smart merge control
        merge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        merge_label = Gtk.Label(label="Smart Fragment Merging")
        merge_label.set_xalign(0)
        merge_label.set_hexpand(True)
        
        merge_help = Gtk.Label(label="Automatically combine short fragments")
        merge_help.set_xalign(0)
        merge_help.get_style_context().add_class("dim-label")
        
        merge_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        merge_vbox.pack_start(merge_label, False, False, 0)
        merge_vbox.pack_start(merge_help, False, False, 0)
        merge_vbox.set_hexpand(True)
        
        merge_box.pack_start(merge_vbox, True, True, 0)
        merge_box.pack_start(self.smart_merge_switch, False, False, 0)
        
        advanced_box.pack_start(merge_box, False, False, 0)
        advanced_expander.add(advanced_box)
        
        # Add all sections to main box
        main_box.pack_start(sensitivity_frame, False, False, 0)
        main_box.pack_start(advanced_expander, False, False, 0)
        
        self.pack_start(main_box, False, False, 0)

    def _connect_signals(self):
        """Connect widget signals to handlers"""
        self.sensitivity_scale.connect("value-changed", self._on_sensitivity_changed)
        self.endpointing_scale.connect("value-changed", self._on_endpointing_changed)
        self.smart_merge_switch.connect("notify::active", self._on_smart_merge_toggled)

    def _load_config_values(self):
        """Load initial values from app configuration"""
        try:
            if hasattr(self.app, 'config'):
                config = self.app.config
                
                # Load Deepgram config
                deepgram_config = config.get('deepgram_config', {})
                sensitivity_map = {
                    'off': 0,
                    'minimal': 1,
                    'balanced': 2,
                    'aggressive': 3
                }
                sensitivity_str = deepgram_config.get('punctuation_sensitivity', 'balanced')
                sensitivity_value = sensitivity_map.get(sensitivity_str, 2)
                self.sensitivity_scale.set_value(sensitivity_value)
                
                endpointing = deepgram_config.get('endpointing_ms', 400)
                self.endpointing_scale.set_value(endpointing)
                
                # Load punctuation processing config
                punct_config = config.get('punctuation_processing', {})
                smart_merge = punct_config.get('enabled', True)
                self.smart_merge_switch.set_active(smart_merge)
                
        except Exception as e:
            logger.warning(f"Could not load config values: {e}")

    def _on_sensitivity_changed(self, widget):
        """Handle punctuation sensitivity changes"""
        value = int(round(widget.get_value()))
        widget.set_value(value)  # Ensure snapping to integer
        
        sensitivity_names = ['off', 'minimal', 'balanced', 'aggressive']
        sensitivity_str = sensitivity_names[value]
        
        logger.info(f"Punctuation sensitivity changed to: {sensitivity_str}")
        
        # Update app configuration
        if hasattr(self.app, 'config'):
            if 'deepgram_config' not in self.app.config:
                self.app.config['deepgram_config'] = {}
            self.app.config['deepgram_config']['punctuation_sensitivity'] = sensitivity_str
            
            # Save configuration
            if hasattr(self.app, 'save_preferences'):
                self.app.save_preferences()
            
            # Apply changes if recording
            self._apply_deepgram_changes()

    def _on_endpointing_changed(self, widget):
        """Handle endpointing threshold changes"""
        value = int(widget.get_value())
        
        logger.info(f"Endpointing threshold changed to: {value}ms")
        
        # Update app configuration
        if hasattr(self.app, 'config'):
            if 'deepgram_config' not in self.app.config:
                self.app.config['deepgram_config'] = {}
            self.app.config['deepgram_config']['endpointing_ms'] = value
            
            # Save configuration
            if hasattr(self.app, 'save_preferences'):
                self.app.save_preferences()
            
            # Apply changes if recording
            self._apply_deepgram_changes()

    def _on_smart_merge_toggled(self, widget, param):
        """Handle smart merge toggle changes"""
        active = widget.get_active()
        
        logger.info(f"Smart merge toggled to: {active}")
        
        # Update app configuration
        if hasattr(self.app, 'config'):
            if 'punctuation_processing' not in self.app.config:
                self.app.config['punctuation_processing'] = {}
            self.app.config['punctuation_processing']['enabled'] = active
            
            # Save configuration
            if hasattr(self.app, 'save_preferences'):
                self.app.save_preferences()
            
            # Apply changes to punctuation processor
            self._apply_processing_changes()

    def _apply_deepgram_changes(self):
        """Apply Deepgram configuration changes during recording"""
        try:
            if hasattr(self.app, 'recording') and self.app.recording:
                if hasattr(self.app, 'deepgram_service') and self.app.deepgram_service:
                    # Check if service is connected
                    if hasattr(self.app.deepgram_service, 'is_connected') and self.app.deepgram_service.is_connected():
                        logger.info("Restarting Deepgram service with new settings...")
                        
                        # Schedule restart in idle callback to avoid threading issues
                        GLib.idle_add(self._restart_deepgram_service)
        except Exception as e:
            logger.error(f"Error applying Deepgram changes: {e}")

    def _restart_deepgram_service(self):
        """Restart Deepgram service with new settings (runs in main thread)"""
        try:
            if hasattr(self.app, '_restart_deepgram_service'):
                self.app._restart_deepgram_service()
            else:
                # Fallback: recreate the service
                logger.info("Recreating Deepgram service...")
                if hasattr(self.app, 'setup_deepgram_service'):
                    self.app.setup_deepgram_service()
        except Exception as e:
            logger.error(f"Error restarting Deepgram service: {e}")
        return False  # Remove idle callback

    def _apply_processing_changes(self):
        """Apply punctuation processing configuration changes"""
        try:
            if hasattr(self.app, 'punctuation_processor'):
                # Update processor configuration
                enabled = self.smart_merge_switch.get_active()
                if hasattr(self.app.punctuation_processor, 'set_enabled'):
                    self.app.punctuation_processor.set_enabled(enabled)
                    logger.info(f"Punctuation processor enabled: {enabled}")
        except Exception as e:
            logger.error(f"Error applying processing changes: {e}")

    def get_punctuation_level(self):
        """Get the current punctuation sensitivity level as a string"""
        value = int(round(self.sensitivity_scale.get_value()))
        levels = ['off', 'minimal', 'balanced', 'aggressive']
        return levels[value]

    def get_endpointing_ms(self):
        """Get the current endpointing threshold in milliseconds"""
        return int(self.endpointing_scale.get_value())

    def get_smart_merge_enabled(self):
        """Get whether smart merge is enabled"""
        return self.smart_merge_switch.get_active()