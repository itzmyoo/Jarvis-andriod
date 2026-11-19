# Jarvis for Android

A voice assistant for your phone using Termux, Termux:API and the Claude API.
Say what you want, Jarvis answers out loud and can control the flashlight,
volume, vibration, battery check and open links.

## Requirements
- Android phone
- Termux and Termux:API, both from F-Droid or GitHub releases (NOT the Play Store)
- An Anthropic API key from console.anthropic.com

## Install
1. Install **Termux** and **Termux:API** apps. Open Termux:API once.
2. In Android Settings > Apps > Termux:API > Permissions, allow Microphone.
3. In Termux:
   ```
   pkg install git -y
   git clone https://github.com/YOUR_USERNAME/jarvis-android.git
   cd jarvis-android
   bash install.sh
   ```
4. Close and reopen Termux, then run `jarvis` (or `jarvis --text` to type).

## Say things like
- "What's the weather like for hiking?"
- "Turn on the flashlight"
- "How's my battery?"
- "Open youtube.com"
- "Goodbye" to exit

## Change the model
`export JARVIS_MODEL=claude-haiku-5-5` for faster, cheaper replies.
