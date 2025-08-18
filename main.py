#!/usr/bin/env python3
import os
import sys
import threading
import io
import wave
import tempfile
import time
import subprocess
import json
import logging
import argparse
import numpy as np
import sounddevice as sd
import pyperclip
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
)
from deepgram_service import DeepgramService
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Import our enhancement module
try:
    from enhance import (
        enhance_prompt, 
        get_enhancement_styles, 
        get_models_by_tier, 
        get_usage_statistics, 
        estimate_enhancement_cost
    )
    ENHANCEMENT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: enhance.py not found or incomplete. Prompt Mode will be disabled. Error: {e}")
    ENHANCEMENT_AVAILABLE = False

# Import model configuration
try:
    from model_config import model_registry
    MODEL_CONFIG_AVAILABLE = True
except ImportError:
    print("Warning: model_config.py not found. Model selection will be disabled.")
    MODEL_CONFIG_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
    
# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    print("Error: DEEPGRAM_API_KEY is not set. Please set the environment variable and restart.")
    sys.exit(1)

# Audio Configuration
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.1  # 100ms chunks

# History configuration
HISTORY_FILE = os.path.expanduser("~/.local/share/voice-transcribe/history.jsonl")

# Colors
COLORS = {
    'bg': '#1e1e2e',              # Dark background
    'button_idle': '#45475a',      # Gray
    'button_recording': '#f38ba8', # Red/Pink
    'button_hover': '#89b4fa',     # Blue
    'text': '#cdd6f4',            # Light text
    'accent': '#89b4fa',          # Blue accent
    'success': '#a6e3a1',         # Green
    'danger': '#f38ba8',          # Red
    'enhanced_bg': '#313244',     # Slightly lighter for enhanced panel
    'warning': '#f9e2af',         # Yellow for warnings
}

# Application
APP_TITLE = "Voice Transcribe v3.2"

class VoiceTranscribeApp:
    def __init__(self):
        self.recording = False
        self.audio_stream = None
        self.wav_writer = None
        self.total_frames = 0
        self.start_time = None
        self.transcript_text = ""
        self.enhanced_text = ""
        self.enhancement_error = None
        
        # Prompt Mode settings
        self.prompt_mode_enabled = False
        self.enhancement_style = "balanced"
        
        # Performance and cost tracking
        self.session_cost = 0.0
        self.session_enhancements = 0
        self.performance_window = None

        # History settings
        self.history_enabled = True
        self.history_limit = 500
        
        # Initialize config dictionary
        self.config = {}

        # Load saved preferences
        self.load_preferences()

        # Streaming configuration
        self.use_live = True
        self.confirmed_text = ""
        self.partial_mark = None
        self.partial_tag = None
        self.max_retries = 5

        # Setup Deepgram client and service
        self.deepgram_client = None
        self.deepgram_service = None
        if DEEPGRAM_API_KEY:
            self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
            self.deepgram_service = DeepgramService(
                self.deepgram_client,
                on_transcript=lambda text, is_final: GLib.idle_add(
                    self._update_live_transcript, text, is_final
                ),
                on_reconnect=lambda attempt: GLib.idle_add(
                    self.status_label.set_text,
                    f"Reconnecting... ({attempt}/{self.max_retries})",
                ),
                max_retries=self.max_retries,
            )

        # Create window
        self.window = Gtk.Window()
        self.window.set_title(APP_TITLE)
        self.window.set_default_size(700, 500)  # Wider for side-by-side
        self.window.set_keep_above(True)
        self.window.connect("destroy", self.on_destroy)
        
        # Apply CSS styling
        self.apply_css()
        
        # Create UI
        self.create_ui()
        
        # Set up keyboard accelerators
        self.setup_accelerators()

        # Threading controls for background audio monitoring
        self.stop_audio = threading.Event()
        self.input_stream = None
        self.monitor_thread = threading.Thread(target=self._monitor_audio, daemon=True)
        self.monitor_thread.start()
        
        # Start elapsed time updater
        GLib.timeout_add(100, self._update_elapsed_time)
    
    def apply_css(self):
        """Apply custom CSS styling"""
        css = f"""
        window {{
            background-color: {COLORS['bg']};
        }}
        
        .main-button {{
            background-color: {COLORS['button_idle']};
            color: {COLORS['text']};
            border: none;
            border-radius: 12px;
            padding: 20px;
            font-size: 18px;
            font-weight: bold;
            min-height: 80px;
        }}
        
        .main-button:hover {{
            background-color: {COLORS['button_hover']};
        }}
        
        .recording {{
            background-color: {COLORS['button_recording']};
        }}
        
        .prompt-mode-active {{
            background-color: {COLORS['accent']};
        }}
        
        .status-label {{
            color: {COLORS['text']};
            font-size: 14px;
            padding: 5px;
        }}
        
        .stats-label {{
            color: {COLORS['accent']};
            font-size: 12px;
            font-family: monospace;
            padding: 3px;
        }}
        
        .transcript-view {{
            background-color: rgba(69, 71, 90, 0.5);
            color: {COLORS['text']};
            border-radius: 8px;
            padding: 10px;
            font-family: monospace;
            font-size: 14px;
        }}
        
        .enhanced-view {{
            background-color: {COLORS['enhanced_bg']};
            color: {COLORS['text']};
            border-radius: 8px;
            padding: 10px;
            font-family: monospace;
            font-size: 14px;
        }}
        
        .enhancement-preview {{
            color: {COLORS['accent']};
            font-style: italic;
        }}
        
        .clipboard-status {{
            color: {COLORS['success']};
            font-size: 13px;
            font-weight: bold;
            padding: 5px;
        }}
        
        .enhancement-error {{
            color: {COLORS['warning']};
            font-size: 13px;
            font-weight: bold;
            padding: 5px;
        }}
        
        .action-button {{
            background-color: {COLORS['button_idle']};
            color: {COLORS['text']};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
            margin: 0 5px;
        }}
        
        .action-button:hover {{
            background-color: {COLORS['accent']};
        }}
        
        .clear-button {{
            background-color: {COLORS['danger']};
        }}
        
        .clear-button:hover {{
            background-color: #dc3545;
        }}
        
        .header-box {{
            background-color: rgba(69, 71, 90, 0.3);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
        }}
        
        .panel-header {{
            color: {COLORS['text']};
            font-size: 13px;
            font-weight: bold;
            padding: 5px 0;
        }}
        
        .prompt-controls {{
            padding: 5px;
        }}
        
        .tier-badge {{
            background-color: rgba(0, 0, 0, 0.1);
            border-radius: 3px;
            padding: 2px 5px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 5px;
        }}
        
        .tier-economy {{
            color: #28a745;
        }}
        
        .tier-standard {{
            color: #007bff;
        }}
        
        .tier-premium {{
            color: #6f42c1;
        }}
        
        .new-badge {{
            background-color: #fd7e14;
            color: white;
            border-radius: 3px;
            padding: 1px 3px;
            font-size: 9px;
            font-weight: bold;
            margin-left: 3px;
        }}
        """
        
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def setup_accelerators(self):
        """Set up keyboard shortcuts"""
        accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(accel_group)

        # Ctrl+H to open history window
        key, modifier = Gtk.accelerator_parse("<Control>h")
        accel_group.connect(key, modifier, Gtk.AccelFlags.VISIBLE,
                            self.show_history_accelerator)

        # Ctrl+Shift+Q for Prompt Mode toggle
        if ENHANCEMENT_AVAILABLE:
            key, modifier = Gtk.accelerator_parse("<Control><Shift>q")
            accel_group.connect(key, modifier, Gtk.AccelFlags.VISIBLE,
                              self.toggle_prompt_mode_accelerator)
        
        # Ctrl+D for Performance Dashboard
        if ENHANCEMENT_AVAILABLE and MODEL_CONFIG_AVAILABLE:
            key, modifier = Gtk.accelerator_parse("<Control>d")
            accel_group.connect(key, modifier, Gtk.AccelFlags.VISIBLE,
                              self.show_performance_dashboard_accelerator)
    
    def create_ui(self):
        """Create the user interface"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # Header box with stats on left, prompt controls on right
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.get_style_context().add_class("header-box")
        
        # Left side: Status and stats
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Status label
        self.status_label = Gtk.Label(label="Ready to transcribe")
        self.status_label.get_style_context().add_class("status-label")
        left_box.pack_start(self.status_label, False, False, 0)
        
        # Stats box
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        
        # Elapsed time
        self.elapsed_label = Gtk.Label(label="Time: 0:00")
        self.elapsed_label.get_style_context().add_class("stats-label")
        stats_box.pack_start(self.elapsed_label, False, False, 0)
        
        # Word count
        self.word_count_label = Gtk.Label(label="Words: 0")
        self.word_count_label.get_style_context().add_class("stats-label")
        stats_box.pack_start(self.word_count_label, False, False, 0)
        
        # Session cost and usage
        self.cost_label = Gtk.Label(label="Cost: $0.00")
        self.cost_label.get_style_context().add_class("stats-label")
        stats_box.pack_start(self.cost_label, False, False, 0)
        
        # Enhancement counter
        self.usage_label = Gtk.Label(label="Enhanced: 0")
        self.usage_label.get_style_context().add_class("stats-label")
        stats_box.pack_start(self.usage_label, False, False, 0)
        
        left_box.pack_start(stats_box, False, False, 0)
        header_box.pack_start(left_box, False, False, 0)
        
        # Center spacer
        header_box.pack_start(Gtk.Label(), True, True, 0)
        
        # Right side: Prompt Mode controls
        if ENHANCEMENT_AVAILABLE:
            prompt_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            prompt_controls.get_style_context().add_class("prompt-controls")
            
            # Prompt Mode checkbox
            self.prompt_mode_check = Gtk.CheckButton(label="Prompt Mode")
            self.prompt_mode_check.set_active(self.prompt_mode_enabled)
            self.prompt_mode_check.connect("toggled", self.on_prompt_mode_toggled)
            prompt_controls.pack_start(self.prompt_mode_check, False, False, 0)
            
            # Style label
            style_label = Gtk.Label(label="Style:")
            prompt_controls.pack_start(style_label, False, False, 0)
            
            # Style dropdown
            self.style_combo = Gtk.ComboBoxText()
            for style in get_enhancement_styles():
                self.style_combo.append_text(style.capitalize())
            self.style_combo.set_active(get_enhancement_styles().index(self.enhancement_style))
            self.style_combo.connect("changed", self.on_style_changed)
            prompt_controls.pack_start(self.style_combo, False, False, 0)
            
            # Model selector with tiered display
            model_label = Gtk.Label(label="Model:")
            model_label.set_margin_start(10)
            prompt_controls.pack_start(model_label, False, False, 0)
            
            self.model_combo = Gtk.ComboBoxText()
            
            # Populate available models if model config is available
            if MODEL_CONFIG_AVAILABLE:
                self._populate_tiered_model_selector()
                self.model_combo.set_sensitive(True)
                self.model_combo.connect("changed", self.on_model_changed)
                self._setup_model_tooltips()
            else:
                # Fallback if model config not available
                self.model_combo.append_text("GPT-4o Mini")
                self.model_combo.set_active(0)
                self.model_combo.set_sensitive(False)
                self.model_combo.set_tooltip_text("Model configuration not available")
            
            prompt_controls.pack_start(self.model_combo, False, False, 0)
            
            # Performance dashboard button
            dashboard_button = Gtk.Button(label="📊")
            dashboard_button.connect("clicked", self.show_performance_dashboard)
            dashboard_button.get_style_context().add_class("action-button")
            dashboard_button.set_tooltip_text("Open Performance Dashboard")
            prompt_controls.pack_start(dashboard_button, False, False, 0)
            
            header_box.pack_end(prompt_controls, False, False, 0)
        
        main_box.pack_start(header_box, False, False, 0)
        
        # Main button with shortcut hint
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        self.button = Gtk.Button(label="Start Recording")
        self.button.connect("clicked", self.toggle_recording)
        self.button.get_style_context().add_class("main-button")
        button_box.pack_start(self.button, False, False, 0)
        
        # Shortcut hints
        shortcuts_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        shortcuts_box.set_halign(Gtk.Align.CENTER)
        
        record_hint = Gtk.Label(label="Ctrl+Q: Toggle Recording")
        record_hint.get_style_context().add_class("stats-label")
        shortcuts_box.pack_start(record_hint, False, False, 0)
        
        if ENHANCEMENT_AVAILABLE:
            separator = Gtk.Label(label="|")
            separator.get_style_context().add_class("stats-label")
            shortcuts_box.pack_start(separator, False, False, 0)
            
            prompt_hint = Gtk.Label(label="Ctrl+Shift+Q: Toggle Prompt Mode")
            prompt_hint.get_style_context().add_class("stats-label")
            shortcuts_box.pack_start(prompt_hint, False, False, 0)
            
            if MODEL_CONFIG_AVAILABLE:
                separator2 = Gtk.Label(label="|")
                separator2.get_style_context().add_class("stats-label")
                shortcuts_box.pack_start(separator2, False, False, 0)
                
                dashboard_hint = Gtk.Label(label="Ctrl+D: Dashboard")
                dashboard_hint.get_style_context().add_class("stats-label")
                shortcuts_box.pack_start(dashboard_hint, False, False, 0)
        
        button_box.pack_start(shortcuts_box, False, False, 0)
        
        main_box.pack_start(button_box, False, False, 10)
        
        # Status labels (clipboard and enhancement)
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        self.clipboard_label = Gtk.Label(label="")
        self.clipboard_label.get_style_context().add_class("clipboard-status")
        status_box.pack_start(self.clipboard_label, False, False, 0)
        
        self.enhancement_label = Gtk.Label(label="")
        self.enhancement_label.get_style_context().add_class("enhancement-error")
        status_box.pack_start(self.enhancement_label, False, False, 0)
        
        main_box.pack_start(status_box, False, False, 0)
        
        # Clear button header (aligned right)
        clear_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Spacer
        clear_header.pack_start(Gtk.Label(), True, True, 0)

        # Clear button
        self.clear_button = Gtk.Button(label="Clear All")
        self.clear_button.connect("clicked", self.clear_transcript)
        self.clear_button.get_style_context().add_class("action-button")
        self.clear_button.get_style_context().add_class("clear-button")
        self.clear_button.set_sensitive(False)
        clear_header.pack_end(self.clear_button, False, False, 0)

        # History button
        self.history_button = Gtk.Button(label="History")
        self.history_button.connect("clicked", self.show_history)
        self.history_button.get_style_context().add_class("action-button")
        clear_header.pack_end(self.history_button, False, False, 0)

        main_box.pack_start(clear_header, False, False, 5)
        
        # Side-by-side transcript panels
        panels_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Original transcript panel
        original_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # Original header with copy button
        original_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        original_header = Gtk.Label(label="Original Transcript")
        original_header.get_style_context().add_class("panel-header")
        original_header_box.pack_start(original_header, False, False, 0)
        
        # Spacer
        original_header_box.pack_start(Gtk.Label(), True, True, 0)
        
        # Copy original button
        self.copy_original_button = Gtk.Button(label="Copy")
        self.copy_original_button.connect("clicked", self.copy_original)
        self.copy_original_button.get_style_context().add_class("action-button")
        self.copy_original_button.set_sensitive(False)
        original_header_box.pack_start(self.copy_original_button, False, False, 0)
        
        original_panel.pack_start(original_header_box, False, False, 0)
        
        # Original transcript scroll
        original_scroll = Gtk.ScrolledWindow()
        original_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        original_scroll.set_min_content_height(200)
        original_scroll.get_style_context().add_class("transcript-view")
        
        self.original_text_view = Gtk.TextView()
        self.original_text_view.set_editable(False)
        self.original_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.original_text_view.set_margin_start(10)
        self.original_text_view.set_margin_end(10)
        self.original_text_view.set_margin_top(10)
        self.original_text_view.set_margin_bottom(10)

        buffer = self.original_text_view.get_buffer()
        buffer.set_text("Your transcript will appear here...")
        self.partial_tag = buffer.create_tag("partial", foreground="#888888")
        
        original_scroll.add(self.original_text_view)
        original_panel.pack_start(original_scroll, True, True, 0)
        
        panels_box.pack_start(original_panel, True, True, 0)
        
        # Enhanced prompt panel (only if enhancement available)
        if ENHANCEMENT_AVAILABLE:
            enhanced_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            
            # Enhanced header with copy button
            enhanced_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            
            enhanced_header = Gtk.Label(label="✨ Enhanced Prompt")
            enhanced_header.get_style_context().add_class("panel-header")
            enhanced_header_box.pack_start(enhanced_header, False, False, 0)
            
            # Spacer
            enhanced_header_box.pack_start(Gtk.Label(), True, True, 0)
            
            # Copy enhanced button
            self.copy_enhanced_button = Gtk.Button(label="Copy")
            self.copy_enhanced_button.connect("clicked", self.copy_enhanced)
            self.copy_enhanced_button.get_style_context().add_class("action-button")
            self.copy_enhanced_button.set_sensitive(False)
            enhanced_header_box.pack_start(self.copy_enhanced_button, False, False, 0)
            
            enhanced_panel.pack_start(enhanced_header_box, False, False, 0)
            
            # Enhanced prompt scroll
            enhanced_scroll = Gtk.ScrolledWindow()
            enhanced_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            enhanced_scroll.set_min_content_height(200)
            enhanced_scroll.get_style_context().add_class("enhanced-view")
            
            self.enhanced_text_view = Gtk.TextView()
            self.enhanced_text_view.set_editable(False)
            self.enhanced_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
            self.enhanced_text_view.set_margin_start(10)
            self.enhanced_text_view.set_margin_end(10)
            self.enhanced_text_view.set_margin_top(10)
            self.enhanced_text_view.set_margin_bottom(10)
            
            buffer = self.enhanced_text_view.get_buffer()
            buffer.set_text("Enhanced prompt will appear here when Prompt Mode is enabled...")
            
            enhanced_scroll.add(self.enhanced_text_view)
            enhanced_panel.pack_start(enhanced_scroll, True, True, 0)
            
            panels_box.pack_start(enhanced_panel, True, True, 0)
        
        main_box.pack_start(panels_box, True, True, 0)
        
        self.window.add(main_box)
        self.window.show_all()
    
    def on_prompt_mode_toggled(self, widget):
        """Handle Prompt Mode toggle"""
        self.prompt_mode_enabled = widget.get_active()
        self.save_preferences()
        
        if self.prompt_mode_enabled:
            self.button.get_style_context().add_class("prompt-mode-active")
        else:
            self.button.get_style_context().remove_class("prompt-mode-active")
    
    def toggle_prompt_mode_accelerator(self, *args):
        """Handle Ctrl+Shift+Q accelerator - directly toggle without focusing"""
        # Toggle the checkbox state
        new_state = not self.prompt_mode_check.get_active()
        self.prompt_mode_check.set_active(new_state)
        
        # Remove focus from the checkbox to prevent visual highlighting
        self.window.set_focus(None)
        
        # Flash a quick visual feedback
        if new_state:
            self.status_label.set_text("✨ Prompt Mode enabled")
        else:
            self.status_label.set_text("Prompt Mode disabled")
        
        # Clear status after a short delay
        GLib.timeout_add_seconds(1.5, self._reset_status)

        return True

    def show_history_accelerator(self, *args):
        """Handle Ctrl+H accelerator"""
        self.show_history()
        return True
    
    def show_performance_dashboard_accelerator(self, *args):
        """Handle Ctrl+D accelerator"""
        self.show_performance_dashboard()
        return True
    
    def show_performance_dashboard(self, widget=None):
        """Show performance monitoring dashboard"""
        if hasattr(self, "performance_window") and self.performance_window:
            self.performance_window.present()
            return
        
        self.performance_window = Gtk.Window(title="Performance Dashboard")
        self.performance_window.set_default_size(800, 600)
        self.performance_window.set_transient_for(self.window)
        self.performance_window.connect("destroy", lambda _w: setattr(self, "performance_window", None))
        
        # Create dashboard content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # Title
        title = Gtk.Label(label="Performance Dashboard")
        title.get_style_context().add_class("panel-header")
        main_box.pack_start(title, False, False, 0)
        
        # Create notebook for different views
        notebook = Gtk.Notebook()
        
        # Usage Statistics Tab
        usage_tab = self._create_usage_statistics_tab()
        notebook.append_page(usage_tab, Gtk.Label(label="Usage Stats"))
        
        # Cost Analysis Tab
        cost_tab = self._create_cost_analysis_tab()
        notebook.append_page(cost_tab, Gtk.Label(label="Cost Analysis"))
        
        # Model Comparison Tab
        comparison_tab = self._create_model_comparison_tab()
        notebook.append_page(comparison_tab, Gtk.Label(label="Model Comparison"))
        
        main_box.pack_start(notebook, True, True, 0)
        
        # Refresh button
        refresh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        refresh_box.set_halign(Gtk.Align.END)
        
        refresh_button = Gtk.Button(label="Refresh Data")
        refresh_button.connect("clicked", self._refresh_dashboard_data)
        refresh_button.get_style_context().add_class("action-button")
        refresh_box.pack_start(refresh_button, False, False, 0)
        
        main_box.pack_start(refresh_box, False, False, 0)
        
        self.performance_window.add(main_box)
        self.performance_window.show_all()
    
    def _create_usage_statistics_tab(self):
        """Create usage statistics tab content"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        
        # Session Statistics
        session_frame = Gtk.Frame(label="Current Session")
        session_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        session_box.set_margin_top(10)
        session_box.set_margin_bottom(10)
        session_box.set_margin_start(10)
        session_box.set_margin_end(10)
        
        session_cost_label = Gtk.Label(label=f"Session Cost: ${self.session_cost:.4f}")
        session_cost_label.set_halign(Gtk.Align.START)
        session_box.pack_start(session_cost_label, False, False, 0)
        
        session_frame.add(session_box)
        vbox.pack_start(session_frame, False, False, 0)
        
        # Model Usage Statistics
        if ENHANCEMENT_AVAILABLE:
            try:
                usage_stats = get_usage_statistics()
                
                if usage_stats:
                    stats_frame = Gtk.Frame(label="Model Usage Statistics")
                    stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                    stats_box.set_margin_top(10)
                    stats_box.set_margin_bottom(10)
                    stats_box.set_margin_start(10)
                    stats_box.set_margin_end(10)
                    
                    for model_name, stats in usage_stats.items():
                        model_config = model_registry.get(model_name)
                        if model_config:
                            tier_info = model_config.get_tier_info()
                            model_label = Gtk.Label(
                                label=f"{model_config.display_name} ({tier_info['tier']}): "
                                     f"{stats['calls']} calls, ${stats['total_cost']:.4f}"
                            )
                            model_label.set_halign(Gtk.Align.START)
                            stats_box.pack_start(model_label, False, False, 0)
                    
                    stats_frame.add(stats_box)
                    vbox.pack_start(stats_frame, False, False, 0)
                else:
                    no_data_label = Gtk.Label(label="No usage data available yet.")
                    vbox.pack_start(no_data_label, False, False, 0)
                    
            except Exception as e:
                error_label = Gtk.Label(label=f"Error loading usage statistics: {e}")
                vbox.pack_start(error_label, False, False, 0)
        
        scroll.add(vbox)
        return scroll
    
    def _create_cost_analysis_tab(self):
        """Create cost analysis tab content"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        
        # Cost breakdown by tier
        if MODEL_CONFIG_AVAILABLE:
            tier_frame = Gtk.Frame(label="Cost by Tier")
            tier_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            tier_box.set_margin_top(10)
            tier_box.set_margin_bottom(10)
            tier_box.set_margin_start(10)
            tier_box.set_margin_end(10)
            
            try:
                models_by_tier = get_models_by_tier()
                for tier_name in ["economy", "standard", "premium"]:
                    tier_models = models_by_tier[tier_name]
                    if tier_models:
                        tier_label = Gtk.Label(label=f"{tier_name.upper()} TIER:")
                        tier_label.set_halign(Gtk.Align.START)
                        tier_label.get_style_context().add_class("panel-header")
                        tier_box.pack_start(tier_label, False, False, 0)
                        
                        for model in tier_models:
                            cost_label = Gtk.Label(
                                label=f"  {model['display']}: ${model['cost_input']*1000:.4f}/1K tokens"
                            )
                            cost_label.set_halign(Gtk.Align.START)
                            tier_box.pack_start(cost_label, False, False, 0)
                        
                        separator = Gtk.Separator()
                        tier_box.pack_start(separator, False, False, 5)
            
            except Exception as e:
                error_label = Gtk.Label(label=f"Error loading cost data: {e}")
                tier_box.pack_start(error_label, False, False, 0)
            
            tier_frame.add(tier_box)
            vbox.pack_start(tier_frame, False, False, 0)
        
        scroll.add(vbox)
        return scroll
    
    def _create_model_comparison_tab(self):
        """Create model comparison tab content"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        
        if MODEL_CONFIG_AVAILABLE:
            # Create comparison table
            comparison_frame = Gtk.Frame(label="Model Comparison")
            comparison_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            comparison_box.set_margin_top(10)
            comparison_box.set_margin_bottom(10)
            comparison_box.set_margin_start(10)
            comparison_box.set_margin_end(10)
            
            # Header
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            header_labels = ["Model", "Tier", "Cost/1K", "Context", "Features"]
            for label_text in header_labels:
                label = Gtk.Label(label=label_text)
                label.get_style_context().add_class("panel-header")
                label.set_size_request(120, -1)
                label.set_halign(Gtk.Align.START)
                header_box.pack_start(label, False, False, 0)
            
            comparison_box.pack_start(header_box, False, False, 0)
            
            separator = Gtk.Separator()
            comparison_box.pack_start(separator, False, False, 5)
            
            # Model rows
            available_models = model_registry.get_available_models()
            for model in available_models:
                model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                
                # Model name
                name_label = Gtk.Label(label=model.display_name)
                name_label.set_size_request(120, -1)
                name_label.set_halign(Gtk.Align.START)
                model_box.pack_start(name_label, False, False, 0)
                
                # Tier
                tier_info = model.get_tier_info()
                tier_label = Gtk.Label(label=tier_info['tier'].title())
                tier_label.set_size_request(120, -1)
                tier_label.set_halign(Gtk.Align.START)
                model_box.pack_start(tier_label, False, False, 0)
                
                # Cost
                cost_label = Gtk.Label(label=f"${model.cost_per_1k_input*1000:.4f}")
                cost_label.set_size_request(120, -1)
                cost_label.set_halign(Gtk.Align.START)
                model_box.pack_start(cost_label, False, False, 0)
                
                # Context window
                context_label = Gtk.Label(label=f"{model.context_window//1000}K")
                context_label.set_size_request(120, -1)
                context_label.set_halign(Gtk.Align.START)
                model_box.pack_start(context_label, False, False, 0)
                
                # Features
                features = []
                if model.supports_verbosity:
                    features.append("V")
                if model.supports_reasoning_effort:
                    features.append("RE")
                if "gpt-5" in model.model_name:
                    features.append("NEW")
                
                features_label = Gtk.Label(label=", ".join(features) if features else "-")
                features_label.set_size_request(120, -1)
                features_label.set_halign(Gtk.Align.START)
                model_box.pack_start(features_label, False, False, 0)
                
                comparison_box.pack_start(model_box, False, False, 0)
            
            comparison_frame.add(comparison_box)
            vbox.pack_start(comparison_frame, False, False, 0)
        
        scroll.add(vbox)
        return scroll
    
    def _refresh_dashboard_data(self, widget):
        """Refresh dashboard data"""
        if hasattr(self, "performance_window") and self.performance_window:
            self.performance_window.destroy()
            self.performance_window = None
            self.show_performance_dashboard()
    
    def on_style_changed(self, widget):
        """Handle enhancement style change"""
        styles = get_enhancement_styles()
        self.enhancement_style = styles[widget.get_active()]
        self.save_preferences()
    
    def _populate_tiered_model_selector(self):
        """Populate model selector with tiered grouping"""
        if not MODEL_CONFIG_AVAILABLE:
            return
            
        try:
            models_by_tier = get_models_by_tier()
            
            # Clear existing items
            self.model_combo.remove_all()
            
            # Add models grouped by tier with visual indicators
            tier_icons = {"economy": "🟢", "standard": "🔵", "premium": "🟣"}
            tier_colors = {"economy": "Economy", "standard": "Standard", "premium": "Premium"}
            
            for tier_name in ["economy", "standard", "premium"]:
                if models_by_tier[tier_name]:
                    # Add tier separator with icon
                    tier_label = f"{tier_icons[tier_name]} {tier_colors[tier_name].upper()} TIER"
                    self.model_combo.append(None, tier_label)
                    
                    # Add models in this tier
                    for model in models_by_tier[tier_name]:
                        cost_per_1k = model["cost_input"] * 1000
                        
                        # Build feature indicators
                        features = []
                        if model["features"]["verbosity"]:
                            features.append("V")  # Verbosity support
                        if model["features"]["reasoning_effort"]:
                            features.append("RE")  # Reasoning effort
                        if "gpt-5" in model["name"]:
                            features.append("NEW")  # New model
                        
                        # Create display text with proper formatting
                        indent = "  "  # Visual indent for tier grouping
                        name_part = model['display']
                        cost_part = f"${cost_per_1k:.4f}/1K"
                        
                        if features:
                            feature_part = f" [{','.join(features)}]"
                            if "NEW" in features:
                                feature_part = feature_part.replace("NEW", "🆕")
                        else:
                            feature_part = ""
                        
                        display_text = f"{indent}{name_part} ({cost_part}){feature_part}"
                        self.model_combo.append(model["name"], display_text)
            
            # Set saved selection
            saved_model = self.config.get("selected_model", "gpt-4o-mini")
            model_found = False
            
            # Find and set the saved model
            for i in range(self.model_combo.get_model().iter_n_children(None)):
                self.model_combo.set_active(i)
                if self.model_combo.get_active_id() == saved_model:
                    model_found = True
                    break
                    
            if not model_found:
                # Default to first selectable model (skip separators)
                for i in range(self.model_combo.get_model().iter_n_children(None)):
                    self.model_combo.set_active(i)
                    if self.model_combo.get_active_id() is not None:
                        break
                        
        except Exception as e:
            print(f"Error populating model selector: {e}")
            # Fallback to simple list
            self.model_combo.append("gpt-4o-mini", "GPT-4o Mini")
            self.model_combo.set_active(0)
    
    def _setup_model_tooltips(self):
        """Setup enhanced tooltips for model selector"""
        if not MODEL_CONFIG_AVAILABLE:
            return
            
        # Create comprehensive tooltip text
        tooltip_parts = [
            "AI Model Selection - Grouped by Performance Tier",
            "",
            "🟢 ECONOMY: Low-cost models for basic enhancement",
            "🔵 STANDARD: Balanced performance and cost",
            "🟣 PREMIUM: High-performance models with advanced features",
            "",
            "Features:",
            "  V = Verbosity control",
            "  RE = Reasoning effort",
            "  🆕 = New GPT-5 technology",
            "",
            "Costs shown per 1,000 input tokens"
        ]
        
        tooltip_text = "\n".join(tooltip_parts)
        self.model_combo.set_tooltip_text(tooltip_text)
    
    def on_model_changed(self, widget):
        """Handle model selection change with cost warnings"""
        if not MODEL_CONFIG_AVAILABLE:
            return
            
        model_id = widget.get_active_id()
        if not model_id:  # Skip separator items
            return
            
        # Get current and new model configs
        current_model = self.config.get("selected_model", "gpt-4o-mini")
        new_model_config = model_registry.get(model_id)
        current_model_config = model_registry.get(current_model)
        
        if not new_model_config or not current_model_config:
            return
            
        # Check if this is a more expensive model
        cost_increase = new_model_config.cost_per_1k_input - current_model_config.cost_per_1k_input
        
        if cost_increase > 0.00005:  # Threshold for showing warning
            tier_info = new_model_config.get_tier_info()
            if self._show_cost_warning_dialog(new_model_config, current_model_config, cost_increase):
                # User confirmed, proceed with change
                self._apply_model_change(model_id)
            else:
                # User cancelled, revert selection
                self._revert_model_selection(current_model)
        else:
            # No significant cost increase, apply directly
            self._apply_model_change(model_id)
    
    def _apply_model_change(self, model_id):
        """Apply the model change"""
        self.selected_model = model_id
        self.config["selected_model"] = model_id
        self.save_config()
        
        # Log for A/B testing
        print(f"Model switched to: {model_id}")
        self.track_model_usage(model_id)
        
        # Update cost display
        self.update_cost_display()
        
        # Update status
        model_config = model_registry.get(model_id)
        if model_config:
            tier_info = model_config.get_tier_info()
            self.status_label.set_text(f"Model: {model_config.display_name} ({tier_info['tier']})")
            GLib.timeout_add_seconds(2, self._reset_status)
    
    def _revert_model_selection(self, previous_model):
        """Revert model selection to previous choice"""
        for i in range(self.model_combo.get_model().iter_n_children(None)):
            self.model_combo.set_active(i)
            if self.model_combo.get_active_id() == previous_model:
                break
    
    def _show_cost_warning_dialog(self, new_model, current_model, cost_increase):
        """Show cost warning dialog for expensive model changes"""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Model Cost Warning"
        )
        
        # Calculate percentage increase
        percent_increase = (cost_increase / current_model.cost_per_1k_input) * 100
        
        # Estimate monthly cost for typical usage (50 enhancements/month)
        monthly_usage = 50
        avg_tokens = 200  # Average tokens per enhancement
        monthly_cost_increase = (avg_tokens / 1000) * cost_increase * monthly_usage
        
        tier_info = new_model.get_tier_info()
        
        secondary_text = (
            f"You're switching from {current_model.display_name} to {new_model.display_name}.\n\n"
            f"Cost increase: {percent_increase:.0f}% ({cost_increase*1000:.4f} → "
            f"{new_model.cost_per_1k_input*1000:.4f} per 1K tokens)\n"
            f"Estimated monthly increase: ${monthly_cost_increase:.2f}\n"
            f"Tier: {tier_info['tier'].title()}\n\n"
            f"Do you want to continue?"
        )
        
        dialog.format_secondary_text(secondary_text)
        
        response = dialog.run()
        dialog.destroy()
        
        return response == Gtk.ResponseType.YES
    
    def track_model_usage(self, model_key):
        """Track model usage for A/B testing"""
        usage_stats = self.config.get("model_usage_stats", {})
        
        # Initialize if needed
        if model_key not in usage_stats:
            usage_stats[model_key] = {
                "count": 0,
                "total_tokens": 0,
                "avg_latency": 0,
                "user_rating": []
            }
        
        usage_stats[model_key]["count"] += 1
        self.config["model_usage_stats"] = usage_stats
        self.save_config()
    
    def update_cost_display(self):
        """Update session cost and usage display"""
        if hasattr(self, 'cost_label'):
            self.cost_label.set_text(f"Cost: ${self.session_cost:.4f}")
        if hasattr(self, 'usage_label'):
            self.usage_label.set_text(f"Enhanced: {self.session_enhancements}")
    
    def add_to_session_cost(self, cost):
        """Add cost to session total and increment usage counter"""
        self.session_cost += cost
        self.session_enhancements += 1
        self.update_cost_display()  # Direct call since we're already in main thread
    
    def save_config(self):
        """Save config dictionary to file"""
        try:
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=2)
        except OSError as e:
            logging.error("Failed to save config: %s", e)
            print("Unable to save config. Please check file permissions.")
    
    def save_preferences(self):
        """Save user preferences to config file"""
        # Update config dictionary with current values
        self.config["prompt_mode_enabled"] = self.prompt_mode_enabled
        self.config["enhancement_style"] = self.enhancement_style
        self.config["history_enabled"] = self.history_enabled
        self.config["history_limit"] = self.history_limit
        self.config["selected_model"] = getattr(self, "selected_model", "gpt-4o-mini")
        self.config["model_preferences"] = getattr(self, "model_preferences", {
            "auto_fallback": True,
            "log_token_usage": True
        })
        
        # Save the config
        try:
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=2)
        except OSError as e:
            logging.error("Failed to save preferences: %s", e)
            print("Unable to save preferences. Please check file permissions.")
            if hasattr(self, "status_label"):
                self.status_label.set_text("⚠️ Unable to save preferences")

    def load_preferences(self):
        """Load user preferences from config file"""
        try:
            with open("config.json", "r") as f:
                prefs = json.load(f)
                # Store the entire config for later use
                self.config = prefs
                # Also set individual attributes for backward compatibility
                self.prompt_mode_enabled = prefs.get("prompt_mode_enabled", False)
                self.enhancement_style = prefs.get("enhancement_style", "balanced")
                self.history_enabled = prefs.get("history_enabled", True)
                self.history_limit = prefs.get("history_limit", 500)
                self.selected_model = prefs.get("selected_model", "gpt-4o-mini")
                self.model_preferences = prefs.get("model_preferences", {
                    "auto_fallback": True,
                    "log_token_usage": True
                })
        except (OSError, json.JSONDecodeError) as e:
            logging.error("Failed to load preferences: %s", e)
            print("Unable to load preferences. Defaults will be used.")
            # Use defaults if no config exists or file is invalid
            self.selected_model = "gpt-4o-mini"
            self.model_preferences = {
                "auto_fallback": True,
                "log_token_usage": True
            }
            self.prompt_mode_enabled = False
            self.enhancement_style = "balanced"
            self.history_enabled = True
            self.history_limit = 500
            # Also set default config dictionary
            self.config = {
                "selected_model": self.selected_model,
                "model_preferences": self.model_preferences,
                "prompt_mode_enabled": self.prompt_mode_enabled,
                "enhancement_style": self.enhancement_style,
                "history_enabled": self.history_enabled,
                "history_limit": self.history_limit
            }

    def load_history(self) -> List[Dict[str, Optional[str]]]:
        """Load history entries from JSONL file"""
        entries: List[Dict[str, Optional[str]]] = []
        try:
            with open(HISTORY_FILE, "r") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return entries

    def _add_to_history(self, original: str, enhanced: Optional[str]) -> None:
        """Append an entry to history file respecting limits"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "original": original,
            "enhanced": enhanced,
            "style": self.enhancement_style,
        }
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Enforce history limit
            with open(HISTORY_FILE, "r") as f:
                lines = f.readlines()
            if len(lines) > self.history_limit:
                lines = lines[-self.history_limit:]
                with open(HISTORY_FILE, "w") as f:
                    f.writelines(lines)
        except OSError as e:
            logging.error("Failed to write history: %s", e)

    def show_history(self, widget=None):
        """Display history window with search and copy"""
        if hasattr(self, "history_window") and self.history_window:
            self.history_window.present()
            return

        self.history_window = Gtk.Window(title="History")
        self.history_window.set_default_size(600, 400)
        self.history_window.connect("destroy", lambda _w: setattr(self, "history_window", None))

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.history_window.add(vbox)

        search_entry = Gtk.SearchEntry()
        vbox.pack_start(search_entry, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)

        list_box = Gtk.ListBox()
        list_box.set_activate_on_single_click(True)
        scrolled.add(list_box)

        entries = self.load_history()
        for entry in reversed(entries):
            ts = entry.get("timestamp", "")
            orig = entry.get("original", "")
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=f"{ts} - {orig}", xalign=0)
            label.set_line_wrap(True)
            row.add(label)
            row.transcript = orig
            list_box.add(row)

            enhanced = entry.get("enhanced")
            if enhanced:
                style = entry.get("style", "")
                row_e = Gtk.ListBoxRow()
                label_e = Gtk.Label(label=f"{ts} [{style}] - {enhanced}", xalign=0)
                label_e.set_line_wrap(True)
                row_e.add(label_e)
                row_e.transcript = enhanced
                list_box.add(row_e)

        def on_search(_entry):
            text = search_entry.get_text().lower()
            for row in list_box.get_children():
                row.set_visible(text in row.transcript.lower())

        def on_row_activated(_lb, row):
            if row and getattr(row, "transcript", None):
                self._copy_to_clipboard(row.transcript)

        list_box.connect("row-activated", on_row_activated)
        search_entry.connect("search-changed", on_search)

        self.history_window.show_all()
    
    def toggle_recording(self, widget=None):
        """Toggle recording state"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording"""
        logging.debug("Starting recording")
        self.recording = True
        self.audio_stream = tempfile.TemporaryFile()
        self.wav_writer = wave.open(self.audio_stream, 'wb')
        self.wav_writer.setnchannels(1)
        self.wav_writer.setsampwidth(2)
        self.wav_writer.setframerate(SAMPLE_RATE)
        self.total_frames = 0
        self.start_time = time.time()

        # Reset live transcript state and view
        buffer = self.original_text_view.get_buffer()
        buffer.set_text("")
        self.confirmed_text = ""
        self.partial_mark = None

        if self.use_live and self.deepgram_service:
            self.deepgram_service.start()
        
        self.button.set_label("Stop Recording")
        self.button.get_style_context().add_class("recording")
        self.status_label.set_text("🔴 Recording... Speak now!")
        self.window.set_title(f"{APP_TITLE} - Recording")
        self.window.set_urgency_hint(True)

        # Clear status labels
        self.clipboard_label.set_text("")
        self.enhancement_label.set_text("")
        logging.debug("Recording setup complete")
    
    def stop_recording(self):
        """Stop recording and process"""
        logging.debug("Stopping recording")
        self.recording = False
        self.button.get_style_context().remove_class("recording")
        self.button.set_label("Start Recording")
        self.status_label.set_text("⏳ Processing audio...")
        self.window.set_urgency_hint(False)
        self.window.set_title(APP_TITLE)

        if self.wav_writer:
            self.wav_writer.close()

        if self.audio_stream:
            self.audio_stream.seek(0)
            if self.total_frames > 0:
                if self.use_live and self.deepgram_service and self.deepgram_service.is_connected():
                    try:
                        logging.debug("Finalizing WebSocket stream")
                        success = self.deepgram_service.finalize()
                        if success:
                            GLib.idle_add(self._show_transcript, self.confirmed_text.strip())
                        else:
                            threading.Thread(target=self._process_audio).start()
                    except Exception as e:
                        logging.debug("WebSocket close error: %s", e)
                        threading.Thread(target=self._process_audio).start()

                    self.audio_stream.close()
                    self.audio_stream = None
                    self.wav_writer = None
                    self.total_frames = 0
                else:
                    threading.Thread(target=self._process_audio).start()
            else:
                self.status_label.set_text("No audio recorded")
                GLib.timeout_add_seconds(2, self._reset_status)
        logging.debug("Recording stopped")
    
    def _monitor_audio(self):
        """Continuously monitor audio input"""
        def audio_callback(indata, frames, time, status):
            if status:
                logging.debug("Audio status: %s", status)

            if self.recording:
                # Convert incoming float32 data to 16-bit PCM
                audio_int16 = (indata.copy() * 32767).astype(np.int16)

                if self.wav_writer:
                    self.wav_writer.writeframes(audio_int16.tobytes())
                    self.total_frames += len(audio_int16)

                if self.recording and self.deepgram_service:
                    chunk = audio_int16.tobytes()
                    self.deepgram_service.send(chunk)
                    # DeepgramService handles reconnection automatically with status updates
        
        # Start continuous audio stream
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
        ) as stream:
            self.input_stream = stream
            while not self.stop_audio.is_set():
                time.sleep(0.1)

        self.input_stream = None

    def _update_live_transcript(self, text, is_final):
        """Update the transcript view with partial and final results."""
        buffer = self.original_text_view.get_buffer()

        if self.partial_mark is None:
            end_iter = buffer.get_end_iter()
            self.partial_mark = buffer.create_mark(None, end_iter, True)

        # Remove any existing partial text and insert new text at the mark
        start_iter = buffer.get_iter_at_mark(self.partial_mark)
        buffer.delete(start_iter, buffer.get_end_iter())
        buffer.insert(start_iter, text)

        # Re-fetch iterators after modifying buffer
        start_iter = buffer.get_iter_at_mark(self.partial_mark)
        end_iter = buffer.get_end_iter()

        if is_final:
            # Finalize the segment and append a space for the next one
            buffer.remove_tag(self.partial_tag, start_iter, end_iter)
            buffer.insert(end_iter, " ")
            self.confirmed_text += text + " "
            self.partial_mark = None
        else:
            # Highlight partial results until they are finalized
            buffer.apply_tag(self.partial_tag, start_iter, end_iter)
        return False

    def _update_elapsed_time(self):
        """Update elapsed time display"""
        if self.recording and self.start_time:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.elapsed_label.set_text(f"Time: {minutes}:{seconds:02d}")
        return True
    
    def _process_audio(self):
        """Process recorded audio"""
        if not self.audio_stream:
            return

        duration = self.total_frames / SAMPLE_RATE
        print(f"Processing {duration:.1f} seconds of audio")

        self.audio_stream.seek(0)
        audio_bytes = self.audio_stream.read()
        self.audio_stream.close()
        self.audio_stream = None
        self.wav_writer = None
        self.total_frames = 0

        transcript = self._transcribe(audio_bytes)

        if transcript:
            GLib.idle_add(self._show_transcript, transcript)
        else:
            GLib.idle_add(self.status_label.set_text, "❌ No speech detected")
            GLib.timeout_add_seconds(2, self._reset_status)
    
    def _transcribe(self, audio_bytes):
        """Transcribe audio using Deepgram"""
        try:
            options = PrerecordedOptions(
                model="nova-3",
                language="en",
                punctuate=True,
                smart_format=True
            )
            
            source = {
                "buffer": audio_bytes,
                "mimetype": "audio/wav"
            }
            
            response = self.deepgram_client.listen.rest.v("1").transcribe_file(
                source=source,
                options=options
            )
            
            # Extract transcript
            if hasattr(response, 'results'):
                transcript = response.results.channels[0].alternatives[0].transcript
            elif isinstance(response, dict) and 'results' in response:
                transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
            else:
                return None
            
            return transcript.strip() if transcript else None
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
    
    def _show_transcript(self, transcript):
        """Display transcript and update UI"""
        self.transcript_text = transcript
        self.enhanced_text = ""
        self.enhancement_error = None
        
        # Update original text view
        buffer = self.original_text_view.get_buffer()
        buffer.set_text(transcript)
        
        # Update word count
        word_count = len(transcript.split())
        self.word_count_label.set_text(f"Words: {word_count}")
        
        # Update status
        self.status_label.set_text("✅ Transcribed successfully!")
        
        # Enable action buttons
        self.copy_original_button.set_sensitive(True)
        self.clear_button.set_sensitive(True)
        
        # Handle enhancement if Prompt Mode is enabled
        if ENHANCEMENT_AVAILABLE and self.prompt_mode_enabled:
            # Show enhancing status
            GLib.idle_add(self.enhancement_label.set_text, "✨ Enhancing prompt...")
            
            # Show preview in enhanced view
            enhanced_buffer = self.enhanced_text_view.get_buffer()
            preview = transcript[:50] + "..." if len(transcript) > 50 else transcript
            enhanced_buffer.set_text(f"Enhancing: {preview}\n\n⏳ Please wait...")
            
            # Enhance in background
            threading.Thread(target=self._enhance_transcript, args=(transcript,)).start()
        else:
            # Just copy original to clipboard
            self._copy_to_clipboard(transcript)

        # Add to history (enhanced will be added separately if available)
        if self.history_enabled:
            self._add_to_history(transcript, None)
    
    def _enhance_transcript(self, transcript):
        """Enhance transcript in background"""
        # Get the selected model if available
        model_key = self.config.get("selected_model", "gpt-4o-mini") if MODEL_CONFIG_AVAILABLE else None
        enhanced, error = enhance_prompt(transcript, self.enhancement_style, model_key=model_key)
        
        if enhanced:
            self.enhanced_text = enhanced
            GLib.idle_add(self._show_enhanced_transcript, enhanced)
        else:
            self.enhancement_error = error
            GLib.idle_add(self._show_enhancement_error, error)
    
    def _show_enhanced_transcript(self, enhanced):
        """Display enhanced transcript"""
        # Update enhanced text view
        buffer = self.enhanced_text_view.get_buffer()
        buffer.set_text(enhanced)
        
        # Enable copy enhanced button
        self.copy_enhanced_button.set_sensitive(True)
        
        # Clear enhancement status
        self.enhancement_label.set_text("")
        
        # Estimate and add cost for this enhancement (thread-safe)
        if MODEL_CONFIG_AVAILABLE and ENHANCEMENT_AVAILABLE:
            try:
                current_model = self.config.get("selected_model", "gpt-4o-mini")
                estimated_cost = estimate_enhancement_cost(self.transcript_text, current_model)
                # Use GLib.idle_add for thread safety
                GLib.idle_add(lambda: self.add_to_session_cost(estimated_cost) or False)
            except Exception as e:
                print(f"Error estimating cost: {e}")

        # Copy enhanced version to clipboard
        self._copy_to_clipboard(enhanced)

        # Add enhanced transcript to history
        if self.history_enabled:
            self._add_to_history(self.transcript_text, enhanced)
    
    def _show_enhancement_error(self, error):
        """Display enhancement error"""
        # Show error
        self.enhancement_label.set_text(f"⚠️ Enhancement failed: {error}")
        
        # Update enhanced view
        buffer = self.enhanced_text_view.get_buffer()
        buffer.set_text(f"Enhancement failed: {error}\n\nUsing original transcript.")
        
        # Copy original to clipboard as fallback
        self._copy_to_clipboard(self.transcript_text)
        
        # Clear error after delay
        GLib.timeout_add_seconds(5, lambda: self.enhancement_label.set_text(""))
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard and update UI"""
        pyperclip.copy(text)
        self.clipboard_label.set_text("✓ Copied to Clipboard!")
        
        # Auto-paste if on X11
        threading.Thread(target=self._attempt_paste).start()
        
        # Clear status after delay
        GLib.timeout_add_seconds(3, self._reset_status)
    
    def copy_original(self, widget):
        """Copy original transcript to clipboard"""
        if self.transcript_text:
            pyperclip.copy(self.transcript_text)
            self.clipboard_label.set_text("✓ Copied Original to Clipboard!")
            GLib.timeout_add_seconds(2, lambda: self.clipboard_label.set_text(""))
    
    def copy_enhanced(self, widget):
        """Copy enhanced transcript to clipboard"""
        if self.enhanced_text:
            pyperclip.copy(self.enhanced_text)
            self.clipboard_label.set_text("✓ Copied Enhanced to Clipboard!")
            GLib.timeout_add_seconds(2, lambda: self.clipboard_label.set_text(""))
        else:
            # Fallback to original if no enhanced version
            self.copy_original(widget)
    
    def clear_transcript(self, widget):
        """Clear the transcript"""
        self.transcript_text = ""
        self.enhanced_text = ""
        self.enhancement_error = None
        
        # Reset text views
        buffer = self.original_text_view.get_buffer()
        buffer.set_text("Your transcript will appear here...")
        
        if ENHANCEMENT_AVAILABLE:
            buffer = self.enhanced_text_view.get_buffer()
            buffer.set_text("Enhanced prompt will appear here when Prompt Mode is enabled...")
        
        # Reset counters
        self.word_count_label.set_text("Words: 0")
        self.elapsed_label.set_text("Time: 0:00")
        
        # Reset session tracking (optional - could be preserved across transcripts)
        # self.session_cost = 0.0
        # self.session_enhancements = 0
        # self.update_cost_display()
        
        # Disable action buttons
        self.copy_original_button.set_sensitive(False)
        self.clear_button.set_sensitive(False)
        if ENHANCEMENT_AVAILABLE:
            self.copy_enhanced_button.set_sensitive(False)
        
        # Clear status labels
        self.clipboard_label.set_text("")
        self.enhancement_label.set_text("")
        
        self.status_label.set_text("Transcript cleared")
        GLib.timeout_add_seconds(2, self._reset_status)
    
    def _attempt_paste(self):
        """Attempt to paste using available clipboard tools"""
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()

        if session_type == 'x11':
            try:
                time.sleep(0.5)
                subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
                print("Auto-pasted with xdotool")
            except Exception:
                pass
        elif session_type == 'wayland':
            try:
                time.sleep(0.5)
                subprocess.run(['wtype', pyperclip.paste()], check=True)
                print("Auto-pasted with wtype")
            except Exception:
                pass
    
    def _reset_status(self):
        """Reset status to ready"""
        self.status_label.set_text("Ready to transcribe")
        return False
    
    def on_destroy(self, widget):
        """Save preferences before closing"""
        self.save_preferences()
        self.stop_audio.set()
        if self.input_stream:
            self.input_stream.close()
            self.input_stream = None
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()
        Gtk.main_quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Transcribe")
    parser.add_argument("command", nargs="?", help="Optional command: toggle")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "toggle":
        # Send toggle signal to running instance
        toggle_file = "/tmp/voice_transcribe_toggle"
        with open(toggle_file, "w") as f:
            f.write("toggle")
        sys.exit(0)
    
    # Create app instance
    app = VoiceTranscribeApp()
    
    # Set up toggle file watcher for Ctrl+Q support
    def check_toggle():
        toggle_file = "/tmp/voice_transcribe_toggle"
        if os.path.exists(toggle_file):
            os.remove(toggle_file)
            app.toggle_recording()
        return True
    
    GLib.timeout_add(100, check_toggle)
    
    # Run the app
    Gtk.main()
