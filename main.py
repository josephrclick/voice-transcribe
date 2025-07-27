#!/usr/bin/env python3
import os
import threading
import io
import wave
import time
import subprocess
import numpy as np
import sounddevice as sd
import pyperclip
from pynput.keyboard import Key, Controller
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from deepgram import DeepgramClient, PrerecordedOptions
from dotenv import load_dotenv

# Load API key
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

class VoiceTranscribeApp:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.keyboard = Controller()
        
        # Setup Deepgram
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create window
        self.window = Gtk.Window()
        self.window.set_title("Voice Transcribe")
        self.window.set_default_size(200, 100)
        self.window.set_keep_above(True)  # Always on top
        self.window.connect("destroy", Gtk.main_quit)
        
        # Create button
        self.button = Gtk.Button(label="Start Recording")
        self.button.connect("clicked", self.toggle_recording)
        self.button.set_size_request(180, 60)
        
        # Layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.pack_start(self.button, True, True, 0)
        
        self.window.add(box)
        self.window.show_all()
        
    def toggle_recording(self, widget):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.recording = True
        self.audio_data = []
        self.button.set_label("Stop Recording")
        
        # Start recording in background thread
        self.record_thread = threading.Thread(target=self._record_audio)
        self.record_thread.start()
    
    def _record_audio(self):
        """Record audio in chunks"""
        samplerate = 16000
        chunk_duration = 0.1  # 100ms chunks
        
        def callback(indata, frames, time, status):
            if self.recording:
                self.audio_data.append(indata.copy())
        
        with sd.InputStream(samplerate=samplerate, 
                          channels=1, 
                          dtype='float32',
                          callback=callback,
                          blocksize=int(samplerate * chunk_duration)):
            while self.recording:
                sd.sleep(100)
    
    def stop_recording(self):
        self.recording = False
        self.button.set_label("Processing...")
        self.button.set_sensitive(False)
        
        # Process in background
        threading.Thread(target=self._process_audio).start()
    
    def _process_audio(self):
        """Process the recorded audio"""
        if not self.audio_data:
            GLib.idle_add(self._reset_button)
            return
        
        # Combine audio chunks
        audio = np.concatenate(self.audio_data, axis=0)
        
        # Convert to WAV format with proper headers
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(16000)  # Sample rate
            
            # Convert audio to 16-bit integers
            audio_int16 = (audio * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())
        
        # Get WAV data
        wav_buffer.seek(0)
        audio_bytes = wav_buffer.read()
        
        # Run transcription
        transcript = self._transcribe(audio_bytes)
        
        if transcript:
            # Copy to clipboard
            pyperclip.copy(transcript)
            
            # Paste to active window
            GLib.idle_add(self._paste_text)
        
        GLib.idle_add(self._reset_button)
    
    def _transcribe(self, audio_bytes):
        """Transcribe audio using Deepgram"""
        try:
            options = PrerecordedOptions(
                model="nova-3",
                language="en",
                punctuate=True,
                smart_format=True
            )
            
            # Use dictionary format for source (SDK v4 format)
            source = {
                "buffer": audio_bytes,
                "mimetype": "audio/wav"
            }
            
            response = self.deepgram.listen.rest.v("1").transcribe_file(
                source=source,
                options=options
            )
            
            # Handle response
            if hasattr(response, 'results'):
                transcript = response.results.channels[0].alternatives[0].transcript
            elif isinstance(response, dict) and 'results' in response:
                transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
            else:
                return None
            
            return transcript.strip() if transcript else None
            
        except Exception as e:
            print(f"Transcription error: {type(e).__name__}: {e}")
            return None
    
    def _paste_text(self):
        """Schedule paste operation outside GTK thread"""
        # Don't run paste directly in GTK callback
        threading.Thread(target=self._do_paste_operation).start()

    def _do_paste_operation(self):
        """Execute paste in separate thread"""
        # Check if we're on X11
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        
        if session_type == 'x11':
            try:
                time.sleep(0.5)  # Allow window focus
                subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
                return
            except Exception as e:
                print(f"xdotool failed: {e}")
        
        # Try pynput
        try:
            time.sleep(0.5)
            with self.keyboard.pressed(Key.ctrl):
                self.keyboard.press('v')
                self.keyboard.release('v')
            return
        except Exception as e:
            print(f"pynput failed: {e}")
        
        # Fallback notification
        GLib.idle_add(self._show_copy_notification)
    
    def _show_copy_notification(self):
        """Show notification that text was copied"""
        self.button.set_label("✓ Copied! Press Ctrl+V")
        # Reset button after 2 seconds
        GLib.timeout_add_seconds(2, self._reset_button)
        return False
    
    def _reset_button(self):
        """Reset button to initial state"""
        self.button.set_label("Start Recording")
        self.button.set_sensitive(True)
        return False  # Return False to stop the timer

if __name__ == "__main__":
    # Run app
    app = VoiceTranscribeApp()
    Gtk.main()