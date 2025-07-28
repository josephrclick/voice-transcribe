# Voice Transcribe

A simple Linux desktop tool for voice-to-text transcription using Deepgram's API. Built quickly as a hobby project with a goal of increasing productivity. 

Speak naturally, and your words appear ready to paste into any application.

## Features

- 🎤 **Click-to-record** - Simple UI with a single button
- 🚀 **Fast transcription** - Powered by Deepgram's Nova-3 model
- 📋 **Automatic clipboard** - Transcribed text is copied automatically
- 🔝 **Always-on-top window** - Easy access while working
- 🐧 **Linux native** - Built with GTK for Linux desktops

## Requirements

- Ubuntu 22.04+ (or similar Linux distribution)
- Python 3.10+
- Deepgram API key (free tier available)
- PulseAudio or PipeWire audio system
- X11 display server (recommended) or Wayland

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/josephrclick/voice-transcribe.git
   cd voice-transcribe
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install system dependencies**
   ```bash
   # For clipboard support
   sudo apt install wl-clipboard  # Wayland
   sudo apt install xclip         # X11
   
   # For auto-paste on X11
   sudo apt install xdotool
   ```

5. **Set up your Deepgram API key**
   ```bash
   # Create .env file
   echo "DEEPGRAM_API_KEY=your_api_key_here" > .env
   ```
   
   Shout out to Deepgram for being solid as hell.

## Usage

### Basic Usage

1. **Start the application**
   ```bash
   source venv/bin/activate
   python main.py
   ```

2. **Click "Start Recording"** and speak

3. **Click "Stop Recording"** when done

4. **Paste your transcribed text** with Ctrl+V

### Desktop Launcher (Optional)

Create a desktop shortcut for easy access:

```bash
cat > ~/.local/share/applications/voice-transcribe.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Voice Transcribe
Comment=Transcribe speech to text
Exec=bash -c "cd $HOME/voice-transcribe && source venv/bin/activate && python main.py"
Icon=audio-input-microphone
Terminal=false
Categories=Utility;Audio;
EOF
```

## Configuration

### Audio Settings

The app uses your default microphone at 16kHz sample rate. To change your default mic:
```bash
# List audio devices
pactl list short sources

# Set default
pactl set-default-source <device_name>
```

### Display Server

- **X11** (Recommended): Auto-paste works automatically
- **Wayland**: Manual paste required (Ctrl+V)

## Project Structure

```
voice-transcribe/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── .env                # API keys (not in git)
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Troubleshooting

### No audio recording
- Check your microphone permissions
- Verify default audio input: `pactl info | grep "Default Source"`

### Transcription fails
- Verify your Deepgram API key is correct
- Check internet connection
- Ensure you have API credits remaining

### Auto-paste not working
- On Wayland: This is expected - use Ctrl+V manually
- On X11: Ensure xdotool is installed
- Try clicking in your target window immediately after recording

### GTK warnings
- Usually harmless and can be ignored
- To suppress: `export GTK_THEME=Adwaita`

## Coming in v2

- 🎯 Voice Activity Detection (VAD) - Automatic recording when you speak
- ⌨️ Global hotkey support (Ctrl+Q to toggle)
- 🔄 Continuous transcription mode
- 🤖 OpenAI integration for transcript enhancement
- 📝 Transcription history

## Dependencies

- **deepgram-sdk** - Speech-to-text API
- **PyGObject** - GTK bindings for Python
- **sounddevice** - Audio recording
- **numpy** - Audio processing
- **pyperclip** - Clipboard management
- **pynput** - Keyboard automation
- **python-dotenv** - Environment variables

##Acknowledgments

- ☕ 
- 🎵 
