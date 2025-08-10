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
import numpy as np
import sounddevice as sd
import pyperclip
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
from deepgram import DeepgramClient, PrerecordedOptions
from dotenv import load_dotenv

# Import our enhancement module
try:
    from enhance import enhance_prompt, get_enhancement_styles
    ENHANCEMENT_AVAILABLE = True
except ImportError:
    print("Warning: enhance.py not found. Prompt Mode will be disabled.")
    ENHANCEMENT_AVAILABLE = False

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Audio Configuration
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.1  # 100ms chunks

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
        
        # Load saved preferences
        self.load_preferences()
        
        # Setup Deepgram
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create window
        self.window = Gtk.Window()
        self.window.set_title("Voice Transcribe v3.2")
        self.window.set_default_size(700, 500)  # Wider for side-by-side
        self.window.set_keep_above(True)
        self.window.connect("destroy", self.on_destroy)
        
        # Apply CSS styling
        self.apply_css()
        
        # Create UI
        self.create_ui()
        
        # Set up keyboard accelerators
        self.setup_accelerators()
        
        # Start audio monitoring thread
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
        
        # Ctrl+Shift+Q for Prompt Mode toggle
        if ENHANCEMENT_AVAILABLE:
            key, modifier = Gtk.accelerator_parse("<Control><Shift>q")
            accel_group.connect(key, modifier, Gtk.AccelFlags.VISIBLE,
                              self.toggle_prompt_mode_accelerator)
    
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
    
    def on_style_changed(self, widget):
        """Handle enhancement style change"""
        styles = get_enhancement_styles()
        self.enhancement_style = styles[widget.get_active()]
        self.save_preferences()
    
    def save_preferences(self):
        """Save user preferences to config file"""
        prefs = {
            "prompt_mode_enabled": self.prompt_mode_enabled,
            "enhancement_style": self.enhancement_style
        }
        try:
            with open("config.json", "w") as f:
                json.dump(prefs, f)
        except:
            pass  # Fail silently
    
    def load_preferences(self):
        """Load user preferences from config file"""
        try:
            with open("config.json", "r") as f:
                prefs = json.load(f)
                self.prompt_mode_enabled = prefs.get("prompt_mode_enabled", False)
                self.enhancement_style = prefs.get("enhancement_style", "balanced")
        except:
            # Use defaults if no config exists
            self.prompt_mode_enabled = False
            self.enhancement_style = "balanced"
    
    def toggle_recording(self, widget=None):
        """Toggle recording state"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording"""
        self.recording = True
        self.audio_stream = tempfile.TemporaryFile()
        self.wav_writer = wave.open(self.audio_stream, 'wb')
        self.wav_writer.setnchannels(1)
        self.wav_writer.setsampwidth(2)
        self.wav_writer.setframerate(SAMPLE_RATE)
        self.total_frames = 0
        self.start_time = time.time()
        
        self.button.set_label("Stop Recording")
        self.button.get_style_context().add_class("recording")
        self.status_label.set_text("🔴 Recording... Speak now!")
        
        # Clear status labels
        self.clipboard_label.set_text("")
        self.enhancement_label.set_text("")
    
    def stop_recording(self):
        """Stop recording and process"""
        self.recording = False
        self.button.get_style_context().remove_class("recording")
        self.button.set_label("Start Recording")
        self.status_label.set_text("⏳ Processing audio...")

        if self.wav_writer:
            self.wav_writer.close()

        if self.audio_stream:
            self.audio_stream.seek(0)
            if self.total_frames > 0:
                threading.Thread(target=self._process_audio).start()
            else:
                self.status_label.set_text("No audio recorded")
                GLib.timeout_add_seconds(2, self._reset_status)
    
    def _monitor_audio(self):
        """Continuously monitor audio input"""
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")

            if self.recording and self.wav_writer:
                audio_int16 = (indata.copy() * 32767).astype(np.int16)
                self.wav_writer.writeframes(audio_int16.tobytes())
                self.total_frames += len(audio_int16)
        
        # Start continuous audio stream
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=audio_callback,
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION)
        ):
            while True:
                time.sleep(0.1)
    
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
            
            response = self.deepgram.listen.rest.v("1").transcribe_file(
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
    
    def _enhance_transcript(self, transcript):
        """Enhance transcript in background"""
        enhanced, error = enhance_prompt(transcript, self.enhancement_style)
        
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
        
        # Copy enhanced version to clipboard
        self._copy_to_clipboard(enhanced)
    
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
        """Attempt to paste using xdotool on X11"""
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        
        if session_type == 'x11':
            try:
                time.sleep(0.5)
                subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
                print("Auto-pasted with xdotool")
            except:
                pass
    
    def _reset_status(self):
        """Reset status to ready"""
        self.status_label.set_text("Ready to transcribe")
        return False
    
    def on_destroy(self, widget):
        """Save preferences before closing"""
        self.save_preferences()
        Gtk.main_quit()

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "toggle":
        # Send toggle signal to running instance
        toggle_file = "/tmp/voice_transcribe_toggle"
        with open(toggle_file, 'w') as f:
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
