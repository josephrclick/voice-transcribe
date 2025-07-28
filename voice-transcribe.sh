#!/bin/bash
# Voice Transcribe Launcher Script

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please create a .env file with your Deepgram API key:"
    echo "DEEPGRAM_API_KEY=your_key_here"
    
    # Show error dialog
    zenity --error --text="No .env file found!\n\nPlease create a .env file with:\nDEEPGRAM_API_KEY=your_key_here" 2>/dev/null || \
    notify-send -u critical "Voice Transcribe" "No .env file found! Please add your Deepgram API key."
    exit 1
fi

# Run the application
python main.py "$@"