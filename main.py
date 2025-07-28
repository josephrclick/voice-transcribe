#!/usr/bin/env python3
import os
import sys
import threading
import io
import wave
import time
import subprocess
import collections
import numpy as np
import sounddevice as sd
import pyperclip
import torch
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
from deepgram import DeepgramClient, PrerecordedOptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# VAD Configuration
SAMPLE_RATE = 16000
VAD_FRAME_MS = 30  # Silero VAD expects 30ms chunks
VAD_FRAME_SIZE = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)
SPEECH_THRESHOLD = 0.5  # Probability threshold for speech
MIN_SPEECH_DURATION_MS = 250  # Minimum speech duration to start recording
MIN_SILENCE_DURATION_MS = 1500  # Silence duration to stop recording

# Colors
COLORS = {
    'bg': '#1e1e2e',           # Dark background
    'button_idle': '#45475a',   # Gray
    'button_recording': '#f38ba8',  # Red/Pink
    'button_success': '#a6e3a1',    # Green
    'text': '#cdd6f4',         # Light text
    'accent': '#89b4fa',       # Blue accent
    'vad_active': '#fab387',   # Orange
}

class VoiceTranscribeApp:
    def __init__(self):
        self.recording = False
        self.vad_active = False
        self.audio_queue = collections.deque()
        self.speech_buffer = []
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        
        # Setup Deepgram
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Load Silero VAD
        print("Loading Silero VAD model...")
        self.vad_model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
        trust_repo=True
        )
        self.vad_model.eval()
        print("VAD model loaded!")
        
        # Create window
        self.window = Gtk.Window()
        self.window.set_title("Voice Transcribe v2")
        self.window.set_default_size(400, 300)
        self.window.set_keep_above(True)
        self.window.connect("destroy", self.on_destroy)
        
        # Apply CSS styling
        self.apply_css()
        
        # Create UI
        self.create_ui()
        
        # Start audio monitoring thread for VAD
        self.monitor_thread = threading.Thread(target=self._monitor_audio, daemon=True)
        self.monitor_thread.start()
    
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
            font-size: 16px;
            font-weight: bold;
        }}
        
        .main-button:hover {{
            background-color: {COLORS['accent']};
        }}
        
        .recording {{
            background-color: {COLORS['button_recording']};
        }}
        
        .success {{
            background-color: {COLORS['button_success']};
        }}
        
        .vad-active {{
            background-color: {COLORS['vad_active']};
        }}
        
        .status-label {{
            color: {COLORS['text']};
            font-size: 14px;
            padding: 5px;
        }}
        
        .transcript-view {{
            background-color: rgba(69, 71, 90, 0.5);
            color: {COLORS['text']};
            border-radius: 8px;
            padding: 10px;
            font-family: monospace;
        }}
        
        .mode-button {{
            background-color: transparent;
            color: {COLORS['text']};
            border: 1px solid {COLORS['accent']};
            padding: 5px 10px;
            margin: 5px;
        }}
        
        .mode-button:checked {{
            background-color: {COLORS['accent']};
            color: {COLORS['bg']};
        }}
        
        .vad-indicator {{
            color: {COLORS['accent']};
            font-family: monospace;
            font-size: 12px;
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
        
        # Status label
        self.status_label = Gtk.Label(label="Ready to transcribe")
        self.status_label.get_style_context().add_class("status-label")
        main_box.pack_start(self.status_label, False, False, 0)
        
        # Mode selector
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        mode_box.set_halign(Gtk.Align.CENTER)
        
        self.manual_radio = Gtk.RadioButton.new_with_label_from_widget(None, "Manual")
        self.manual_radio.get_style_context().add_class("mode-button")
        
        self.vad_radio = Gtk.RadioButton.new_with_label_from_widget(self.manual_radio, "Auto VAD")
        self.vad_radio.get_style_context().add_class("mode-button")
        
        mode_box.pack_start(self.manual_radio, False, False, 0)
        mode_box.pack_start(self.vad_radio, False, False, 0)
        main_box.pack_start(mode_box, False, False, 10)
        
        # Main button
        self.button = Gtk.Button(label="Start Recording")
        self.button.connect("clicked", self.toggle_recording)
        self.button.set_size_request(360, 80)
        self.button.get_style_context().add_class("main-button")
        main_box.pack_start(self.button, False, False, 10)
        
        # VAD indicator
        self.vad_indicator = Gtk.Label(label="")
        self.vad_indicator.get_style_context().add_class("vad-indicator")
        main_box.pack_start(self.vad_indicator, False, False, 0)
        
        # Transcript preview
        self.transcript_label = Gtk.Label(label="Transcript will appear here...")
        self.transcript_label.set_line_wrap(True)
        self.transcript_label.set_max_width_chars(50)
        self.transcript_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.transcript_label.get_style_context().add_class("status-label")
        
        # Scrolled window for transcript
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(80)
        scroll.get_style_context().add_class("transcript-view")
        
        # Text view for longer transcripts
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_margin_start(10)
        self.text_view.set_margin_end(10)
        self.text_view.set_margin_top(10)
        self.text_view.set_margin_bottom(10)
        
        scroll.add(self.text_view)
        main_box.pack_start(scroll, True, True, 0)
        
        self.window.add(main_box)
        self.window.show_all()
    
    def on_destroy(self, widget):
        """Clean shutdown"""
        self.recording = False
        self.vad_active = False
        Gtk.main_quit()
    
    def toggle_recording(self, widget=None):
        """Toggle recording state"""
        if self.vad_radio.get_active():
            # Voice activated mode
            if not self.vad_active:
                self.start_vad_mode()
            else:
                self.stop_vad_mode()
        else:
            # Manual mode
            if not self.recording:
                self.start_manual_recording()
            else:
                self.stop_manual_recording()
    
    def start_vad_mode(self):
        """Start voice-activated recording mode"""
        self.vad_active = True
        self.audio_queue.clear()
        self.speech_buffer = []
        self.button.set_label("Stop VAD Mode")
        self.button.get_style_context().add_class("vad-active")
        self.status_label.set_text("🎤 Listening for speech...")
    
    def stop_vad_mode(self):
        """Stop voice-activated recording mode"""
        self.vad_active = False
        self.button.get_style_context().remove_class("vad-active")
        
        # Process any accumulated speech
        if self.speech_buffer:
            self.status_label.set_text("Processing final audio...")
            self._process_audio_buffer(self.speech_buffer)
            self.speech_buffer = []
        
        self.button.set_label("Start Recording")
        self.status_label.set_text("Ready to transcribe")
        self.vad_indicator.set_text("")
    
    def start_manual_recording(self):
        """Start manual recording"""
        self.recording = True
        self.audio_queue.clear()
        self.button.set_label("Stop Recording")
        self.button.get_style_context().add_class("recording")
        self.status_label.set_text("🔴 Recording...")
    
    def stop_manual_recording(self):
        """Stop manual recording and process"""
        self.recording = False
        self.button.get_style_context().remove_class("recording")
        self.button.set_label("Processing...")
        self.button.set_sensitive(False)
        self.status_label.set_text("⏳ Processing audio...")
        
        # Convert queue to list for processing
        audio_data = list(self.audio_queue)
        self.audio_queue.clear()
        
        if audio_data:
            threading.Thread(target=self._process_audio_buffer, args=(audio_data,)).start()
        else:
            self.reset_ui()
    
    def _monitor_audio(self):
        """Continuously monitor audio input"""
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            
            # Add to queue if recording manually
            if self.recording:
                self.audio_queue.append(indata.copy())
            
            # Process for VAD if active
            if self.vad_active:
                self.audio_queue.append(indata.copy())
                # Keep only last few seconds in queue
                while len(self.audio_queue) > 100:  # ~3 seconds
                    self.audio_queue.popleft()
        
        # Start continuous audio stream
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=audio_callback,
            blocksize=VAD_FRAME_SIZE
        ):
            while True:
                if self.vad_active and len(self.audio_queue) > 0:
                    self._process_vad_frame()
                time.sleep(0.01)
    
    def _process_vad_frame(self):
        """Process audio frame with VAD"""
        if not self.audio_queue:
            return
        
        # Get audio frame
        frame = self.audio_queue[-1]
        
        # Convert to tensor
        audio_tensor = torch.FloatTensor(frame.flatten())
        
        # Run VAD
        with torch.no_grad():
            speech_prob = self.vad_model(audio_tensor, SAMPLE_RATE).item()
        
        # Update UI indicator
        bars = int(speech_prob * 10)
        indicator_text = f"{'▓' * bars}{'░' * (10 - bars)} {speech_prob:.2f}"
        GLib.idle_add(self.vad_indicator.set_text, indicator_text)
        
        # Detect speech state changes
        if speech_prob >= SPEECH_THRESHOLD:
            self.speech_frames += 1
            self.silence_frames = 0
            
            if not self.is_speaking and self.speech_frames >= MIN_SPEECH_DURATION_MS / VAD_FRAME_MS:
                # Start of speech detected
                self.is_speaking = True
                GLib.idle_add(self.status_label.set_text, "🎤 Speech detected - recording...")
                # Add buffered audio to speech buffer
                self.speech_buffer.extend(list(self.audio_queue))
            elif self.is_speaking:
                # Continue adding to speech buffer
                self.speech_buffer.append(frame)
        else:
            self.silence_frames += 1
            self.speech_frames = 0
            
            if self.is_speaking:
                # Add silence to buffer (for natural pauses)
                self.speech_buffer.append(frame)
                
                if self.silence_frames >= MIN_SILENCE_DURATION_MS / VAD_FRAME_MS:
                    # End of speech detected
                    self.is_speaking = False
                    GLib.idle_add(self.status_label.set_text, "⏳ Processing speech...")
                    
                    # Process the speech buffer
                    threading.Thread(
                        target=self._process_audio_buffer,
                        args=(self.speech_buffer.copy(),)
                    ).start()
                    
                    # Clear buffer for next utterance
                    self.speech_buffer = []
    
    def _process_audio_buffer(self, audio_data):
        """Process accumulated audio data"""
        if not audio_data:
            GLib.idle_add(self.reset_ui)
            return
        
        # Combine audio chunks
        audio = np.concatenate(audio_data, axis=0)
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
            print(f"Transcript: {transcript}")
            pyperclip.copy(transcript)
            GLib.idle_add(self._show_success, transcript)
        else:
            GLib.idle_add(self.status_label.set_text, "❌ No speech detected")
            GLib.idle_add(self.reset_ui)
    
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
    
    def _show_success(self, transcript):
        """Show success message and transcript"""
        # Update status
        self.status_label.set_text("✅ Transcribed successfully!")
        
        # Show transcript in text view
        buffer = self.text_view.get_buffer()
        buffer.set_text(transcript)
        
        # Update button
        self.button.set_label("✓ Copied to Clipboard!")
        self.button.get_style_context().add_class("success")
        
        # Try to paste automatically
        threading.Thread(target=self._attempt_paste).start()
        
        # Reset after delay
        GLib.timeout_add_seconds(3, self.reset_ui)
    
    def _attempt_paste(self):
        """Attempt to paste using available methods"""
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        
        if session_type == 'x11':
            try:
                time.sleep(0.5)
                subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
                print("Auto-pasted with xdotool")
                return
            except:
                pass
    
    def reset_ui(self):
        """Reset UI to ready state"""
        self.button.get_style_context().remove_class("recording")
        self.button.get_style_context().remove_class("success")
        self.button.get_style_context().remove_class("vad-active")
        self.button.set_sensitive(True)
        
        if self.vad_active:
            self.button.set_label("Stop VAD Mode")
            self.button.get_style_context().add_class("vad-active")
            self.status_label.set_text("🎤 Listening for speech...")
        else:
            self.button.set_label("Start Recording")
            self.status_label.set_text("Ready to transcribe")
        
        return False

def toggle_from_command():
    """Function to be called from command line for global hotkey"""
    toggle_file = "/tmp/voice_transcribe_toggle"
    with open(toggle_file, 'w') as f:
        f.write("toggle")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "toggle":
            # Send toggle signal to running instance
            toggle_file = "/tmp/voice_transcribe_toggle"
            with open(toggle_file, 'w') as f:
                f.write("toggle")
            sys.exit(0)
        elif sys.argv[1] == "vad":
            # Send VAD mode signal
            toggle_file = "/tmp/voice_transcribe_vad"
            with open(toggle_file, 'w') as f:
                f.write("vad")
            sys.exit(0)
    
    # Start the app
    app = VoiceTranscribeApp()
    
    # Set up file watchers for commands
    def check_toggle():
        toggle_file = "/tmp/voice_transcribe_toggle"
        if os.path.exists(toggle_file):
            os.remove(toggle_file)
            app.toggle_recording()
        return True
    
    def check_vad():
        vad_file = "/tmp/voice_transcribe_vad"
        if os.path.exists(vad_file):
            os.remove(vad_file)
            # Force VAD mode
            app.vad_radio.set_active(True)
            app.toggle_recording()
        return True
    
    # Check for commands periodically
    GLib.timeout_add(100, check_toggle)
    GLib.timeout_add(100, check_vad)
    
    Gtk.main()