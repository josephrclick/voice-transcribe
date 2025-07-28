#!/usr/bin/env python3
import os
import sys
import threading
import io
import wave
import time
import subprocess
import numpy as np
import sounddevice as sd
import pyperclip
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
from deepgram import DeepgramClient, PrerecordedOptions
from dotenv import load_dotenv

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
}

class VoiceTranscribeApp:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.start_time = None
        self.transcript_text = ""
        
        # Setup Deepgram
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create window
        self.window = Gtk.Window()
        self.window.set_title("Voice Transcribe v3")
        self.window.set_default_size(450, 400)
        self.window.set_keep_above(True)
        self.window.connect("destroy", Gtk.main_quit)
        
        # Apply CSS styling
        self.apply_css()
        
        # Create UI
        self.create_ui()
        
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
        
        .clipboard-status {{
            color: {COLORS['success']};
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
        """
        
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def create_ui(self):
        """Create the user interface"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # Header box for title and stats
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        header_box.get_style_context().add_class("header-box")
        
        # Status label
        self.status_label = Gtk.Label(label="Ready to transcribe")
        self.status_label.get_style_context().add_class("status-label")
        header_box.pack_start(self.status_label, False, False, 0)
        
        # Stats box (horizontal)
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        stats_box.set_halign(Gtk.Align.CENTER)
        
        # Elapsed time
        self.elapsed_label = Gtk.Label(label="Time: 0:00")
        self.elapsed_label.get_style_context().add_class("stats-label")
        stats_box.pack_start(self.elapsed_label, False, False, 0)
        
        # Word count
        self.word_count_label = Gtk.Label(label="Words: 0")
        self.word_count_label.get_style_context().add_class("stats-label")
        stats_box.pack_start(self.word_count_label, False, False, 0)
        
        header_box.pack_start(stats_box, False, False, 0)
        main_box.pack_start(header_box, False, False, 0)
        
        # Main button with shortcut hint
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        self.button = Gtk.Button(label="Start Recording")
        self.button.connect("clicked", self.toggle_recording)
        self.button.get_style_context().add_class("main-button")
        button_box.pack_start(self.button, False, False, 0)
        
        # Shortcut hint
        shortcut_label = Gtk.Label(label="Press Ctrl+Q to toggle")
        shortcut_label.get_style_context().add_class("stats-label")
        button_box.pack_start(shortcut_label, False, False, 0)
        
        main_box.pack_start(button_box, False, False, 10)
        
        # Clipboard status
        self.clipboard_label = Gtk.Label(label="")
        self.clipboard_label.get_style_context().add_class("clipboard-status")
        main_box.pack_start(self.clipboard_label, False, False, 0)
        
        # Transcript section with header
        transcript_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        transcript_title = Gtk.Label(label="Transcript:")
        transcript_title.get_style_context().add_class("status-label")
        transcript_header.pack_start(transcript_title, False, False, 0)
        
        # Spacer
        transcript_header.pack_start(Gtk.Label(), True, True, 0)
        
        # Action buttons
        self.copy_button = Gtk.Button(label="Copy")
        self.copy_button.connect("clicked", self.copy_transcript)
        self.copy_button.get_style_context().add_class("action-button")
        self.copy_button.set_sensitive(False)
        transcript_header.pack_start(self.copy_button, False, False, 0)
        
        self.clear_button = Gtk.Button(label="Clear")
        self.clear_button.connect("clicked", self.clear_transcript)
        self.clear_button.get_style_context().add_class("action-button")
        self.clear_button.get_style_context().add_class("clear-button")
        self.clear_button.set_sensitive(False)
        transcript_header.pack_start(self.clear_button, False, False, 0)
        
        main_box.pack_start(transcript_header, False, False, 0)
        
        # Scrolled window for transcript
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(150)
        scroll.get_style_context().add_class("transcript-view")
        
        # Text view
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_margin_start(10)
        self.text_view.set_margin_end(10)
        self.text_view.set_margin_top(10)
        self.text_view.set_margin_bottom(10)
        
        # Set initial placeholder
        buffer = self.text_view.get_buffer()
        buffer.set_text("Your transcript will appear here...")
        
        scroll.add(self.text_view)
        main_box.pack_start(scroll, True, True, 0)
        
        self.window.add(main_box)
        self.window.show_all()
    
    def toggle_recording(self, widget=None):
        """Toggle recording state"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording"""
        self.recording = True
        self.audio_data = []
        self.start_time = time.time()
        
        self.button.set_label("Stop Recording")
        self.button.get_style_context().add_class("recording")
        self.status_label.set_text("🔴 Recording... Speak now!")
        
        # Clear clipboard status
        self.clipboard_label.set_text("")
    
    def stop_recording(self):
        """Stop recording and process"""
        self.recording = False
        self.button.get_style_context().remove_class("recording")
        self.button.set_label("Start Recording")
        self.status_label.set_text("⏳ Processing audio...")
        
        # Process in background
        if self.audio_data:
            threading.Thread(target=self._process_audio).start()
        else:
            self.status_label.set_text("No audio recorded")
            GLib.timeout_add_seconds(2, self._reset_status)
    
    def _monitor_audio(self):
        """Continuously monitor audio input"""
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            
            if self.recording:
                self.audio_data.append(indata.copy())
        
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
        # Combine audio chunks
        audio = np.concatenate(self.audio_data, axis=0)
        duration = len(audio) / SAMPLE_RATE
        print(f"Processing {duration:.1f} seconds of audio")
        
        # Convert to WAV format
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            audio_int16 = (audio * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())
        
        wav_buffer.seek(0)
        audio_bytes = wav_buffer.read()
        
        # Transcribe
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
        
        # Update text view
        buffer = self.text_view.get_buffer()
        buffer.set_text(transcript)
        
        # Update word count
        word_count = len(transcript.split())
        self.word_count_label.set_text(f"Words: {word_count}")
        
        # Update status
        self.status_label.set_text("✅ Transcribed successfully!")
        
        # Copy to clipboard
        pyperclip.copy(transcript)
        self.clipboard_label.set_text("✓ Copied to Clipboard!")
        
        # Enable action buttons
        self.copy_button.set_sensitive(True)
        self.clear_button.set_sensitive(True)
        
        # Auto-paste if on X11
        threading.Thread(target=self._attempt_paste).start()
        
        # Clear status after delay
        GLib.timeout_add_seconds(3, self._reset_status)
    
    def copy_transcript(self, widget):
        """Copy transcript to clipboard"""
        if self.transcript_text:
            pyperclip.copy(self.transcript_text)
            self.clipboard_label.set_text("✓ Copied to Clipboard!")
            GLib.timeout_add_seconds(2, lambda: self.clipboard_label.set_text(""))
    
    def clear_transcript(self, widget):
        """Clear the transcript"""
        self.transcript_text = ""
        
        # Reset text view
        buffer = self.text_view.get_buffer()
        buffer.set_text("Your transcript will appear here...")
        
        # Reset counters
        self.word_count_label.set_text("Words: 0")
        self.elapsed_label.set_text("Time: 0:00")
        
        # Disable action buttons
        self.copy_button.set_sensitive(False)
        self.clear_button.set_sensitive(False)
        
        # Clear clipboard status
        self.clipboard_label.set_text("")
        
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