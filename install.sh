#!/data/data/com.termux/files/usr/bin/bash
# One-shot installer for Jarvis on Termux (free Gemini API key).
set -e

pkg update -y
pkg install -y python termux-api git
pip install requests

echo
echo "Get a FREE key at https://aistudio.google.com/apikey (no card needed)."
read -rp "Paste your Gemini API key: " KEY
echo "export GEMINI_API_KEY=\"$KEY\"" > "$HOME/.jarvis_env"
chmod 600 "$HOME/.jarvis_env"

grep -q ".jarvis_env" "$HOME/.bashrc" 2>/dev/null || echo 'source ~/.jarvis_env' >> "$HOME/.bashrc"
grep -q "alias jarvis=" "$HOME/.bashrc" 2>/dev/null || echo "alias jarvis='python $(pwd)/jarvis.py'" >> "$HOME/.bashrc"

echo "Done. Close and reopen Termux, then type: jarvis"
