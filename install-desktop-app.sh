#!/bin/bash
# Install Voice Transcribe as a desktop application
# Optional: install 'wtype' for Wayland auto-paste support (sudo apt install wtype)

echo "Installing Voice Transcribe desktop application..."
echo "Tip: For auto-paste on Wayland, install 'wtype'"

# Get the current directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
USER_HOME=$(eval echo ~$USER)

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Make the launcher script executable
echo "Setting up launcher script..."
chmod +x "$PROJECT_DIR/voice-transcribe"

# 2. Create an icon (using Python to generate a simple microphone icon)
echo "Creating application icon..."
python3 << EOF
import os

# SVG icon for microphone
svg_icon = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#89b4fa;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#45475a;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="30" fill="#1e1e2e"/>
  <g transform="translate(128,128)">
    <!-- Microphone body -->
    <rect x="-30" y="-70" width="60" height="100" rx="30" fill="url(#grad1)"/>
    <!-- Microphone grill lines -->
    <line x1="-15" y1="-50" x2="-15" y2="-20" stroke="#1e1e2e" stroke-width="2"/>
    <line x1="0" y1="-50" x2="0" y2="-20" stroke="#1e1e2e" stroke-width="2"/>
    <line x1="15" y1="-50" x2="15" y2="-20" stroke="#1e1e2e" stroke-width="2"/>
    <!-- Microphone stand -->
    <path d="M -40 30 Q -40 60 0 60 Q 40 60 40 30" 
          stroke="#cdd6f4" stroke-width="8" fill="none"/>
    <line x1="0" y1="60" x2="0" y2="80" stroke="#cdd6f4" stroke-width="8"/>
    <rect x="-20" y="80" width="40" height="8" rx="4" fill="#cdd6f4"/>
  </g>
</svg>'''

# Save SVG icon
with open('$PROJECT_DIR/images/icon.svg', 'w') as f:
    f.write(svg_icon)

# Convert SVG to PNG using rsvg-convert if available
import subprocess
try:
    subprocess.run(['rsvg-convert', '--width=256', '--height=256', 
                   '$PROJECT_DIR/images/icon.svg', '-o', '$PROJECT_DIR/images/icon.png'], 
                   check=True, capture_output=True)
    print("Created PNG icon")
except:
    print("Note: Install librsvg2-bin for PNG icon: sudo apt install librsvg2-bin")
    # Create a simple PNG fallback using PIL if available
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (256, 256), '#1e1e2e')
        draw = ImageDraw.Draw(img)
        # Simple microphone shape
        draw.rounded_rectangle([98, 50, 158, 150], radius=30, fill='#89b4fa')
        draw.arc([80, 140, 176, 200], start=180, end=0, fill='#cdd6f4', width=8)
        draw.rectangle([124, 200, 132, 220], fill='#cdd6f4')
        draw.rounded_rectangle([108, 220, 148, 228], radius=4, fill='#cdd6f4')
        img.save('$PROJECT_DIR/images/icon.png')
        print("Created PNG icon using PIL")
    except:
        print("Note: Install pillow for PNG icon: pip install pillow")

print("Icon creation complete")
EOF

# 3. Update the .desktop file with correct paths
echo "Creating desktop entry..."
sed -e "s|/home/joe/dev/projects/voice-transcribe|$PROJECT_DIR|g" \
    "$PROJECT_DIR/voice-transcribe.desktop" > "$PROJECT_DIR/voice-transcribe.desktop.tmp"
mv "$PROJECT_DIR/voice-transcribe.desktop.tmp" "$PROJECT_DIR/voice-transcribe.desktop"

# 4. Install the desktop file
DESKTOP_DIR="$USER_HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cp "$PROJECT_DIR/voice-transcribe.desktop" "$DESKTOP_DIR/"

# 5. Update desktop database
echo "Updating desktop database..."
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# 6. Create symbolic link in ~/.local/bin (optional, for command line access)
BIN_DIR="$USER_HOME/.local/bin"
if [ -d "$BIN_DIR" ]; then
    echo "Creating command line shortcut..."
    ln -sf "$PROJECT_DIR/voice-transcribe" "$BIN_DIR/voice-transcribe"
fi

# 7. Set up keyboard shortcut for Ctrl+Q (GNOME)
if command -v gsettings &> /dev/null; then
    echo "Setting up Ctrl+Q keyboard shortcut..."
    
    # Get current custom keybindings
    CUSTOM_KEYBINDINGS=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
    
    # Check if our keybinding already exists
    if [[ ! "$CUSTOM_KEYBINDINGS" == *"voice-transcribe"* ]]; then
        # Add our keybinding
        if [ "$CUSTOM_KEYBINDINGS" == "@as []" ]; then
            NEW_KEYBINDINGS="['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voice-transcribe/']"
        else
            # Remove the closing bracket, add our binding, then close
            NEW_KEYBINDINGS="${CUSTOM_KEYBINDINGS%]}, '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voice-transcribe/']"
        fi
        
        gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_KEYBINDINGS"
        
        # Set the keybinding properties
        gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voice-transcribe/ name 'Voice Transcribe Toggle'
        gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voice-transcribe/ command "$PROJECT_DIR/voice-transcribe toggle"
        gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voice-transcribe/ binding '<Control>q'
        
        echo -e "${GREEN}✓ Keyboard shortcut Ctrl+Q configured${NC}"
    else
        echo "Keyboard shortcut already configured"
    fi
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "You can now:"
echo "1. Find 'Voice Transcribe' in your application menu"
echo "2. Pin it to your dock/taskbar"
echo "3. Use Ctrl+Q to toggle recording (on GNOME)"
echo "4. Run 'voice-transcribe' from terminal (if ~/.local/bin is in PATH)"
echo ""
echo "First time setup:"
echo "- Make sure your .env file contains: DEEPGRAM_API_KEY=your_key_here"
echo "- The app will create the virtual environment on first launch if needed"