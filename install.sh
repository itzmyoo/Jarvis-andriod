#!/data/data/com.termux/files/usr/bin/bash
# One-shot installer for Jarvis on Termux.
set -e

pkg update -y
pkg install -y python termux-api git
pip install requests

if [ ! -f "$HOME/.jarvis_env" ]; then
  read -rp "Paste your Anthropic API key: " KEY
  echo "export ANTHROPIC_API_KEY=\"$KEY\"" > "$HOME/.jarvis_env"
  chmod 600 "$HOME/.jarvis_env"
fi

grep -q ".jarvis_env" "$HOME/.bashrc" 2>/dev/null || echo 'source ~/.jarvis_env' >> "$HOME/.bashrc"
grep -q "alias jarvis=" "$HOME/.bashrc" 2>/dev/null || echo "alias jarvis='python $(pwd)/jarvis.py'" >> "$HOME/.bashrc"

echo "Done. Close and reopen Termux, then type: jarvis"
