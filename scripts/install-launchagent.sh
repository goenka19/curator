#!/bin/bash
#
# Install Curator Dashboard LaunchAgent
# Sets up auto-run on wake and daily at 9 AM
#

set -e

CURATOR_DIR="/Users/ujjwalgoenka/Desktop/Coding/curator"
LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.curator.dashboard.plist"
PLIST_SOURCE="$CURATOR_DIR/scripts/$PLIST_NAME"
PLIST_DEST="$LAUNCHAGENT_DIR/$PLIST_NAME"

echo "🚀 Installing Curator Dashboard LaunchAgent..."
echo

# Check if running from correct directory
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Error: Cannot find $PLIST_SOURCE"
    echo "   Make sure you're running from the curator directory"
    exit 1
fi

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCHAGENT_DIR"

# Copy plist file
echo "📋 Copying LaunchAgent plist..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Set correct permissions
chmod 644 "$PLIST_DEST"

# Create logs directory
mkdir -p "$HOME/.curator/logs"

# Unload existing if present (to update)
if launchctl list | grep -q "com.curator.dashboard"; then
    echo "🔄 Unloading existing LaunchAgent..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Load new LaunchAgent
echo "▶️  Loading LaunchAgent..."
launchctl load "$PLIST_DEST"

# Test run
echo "🧪 Testing dashboard (first run may take a moment)..."
"$CURATOR_DIR/backend/venv/bin/python" -c "
import sys
sys.path.insert(0, '$CURATOR_DIR')
from backend.state_manager import get_state_manager
sm = get_state_manager()
state = sm.load_state()
print(f'   State loaded successfully (version {state.version})')
print(f'   Initialized: {state.initialized}')
"

echo
echo "✅ Installation complete!"
echo
echo "The dashboard will now:"
echo "  • Run daily at 9:00 AM"
echo "  • Check for new content automatically"
echo "  • Track costs and notify at milestones"
echo
echo "Commands:"
echo "  launchctl start com.curator.dashboard    # Run now"
echo "  launchctl stop com.curator.dashboard     # Stop"
echo "  launchctl unload $PLIST_DEST   # Uninstall"
echo
echo "Logs: $HOME/.curator/logs/"
echo "State: $HOME/.curator/state.json"
