#!/usr/bin/env python3
"""Jarvis: a voice assistant for Android (Termux + Termux:API + Claude API).

Usage:
    python jarvis.py          # voice mode
    python jarvis.py --text   # type instead of speak
"""
import os
import re
import subprocess
import sys

import requests

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("JARVIS_MODEL", "claude-sonnet-5-5")
API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM = (
    "You are Jarvis, a concise, witty voice assistant running on an Android phone. "
    "Reply in at most 3 short sentences, in plain speech (no markdown). "
    "To control the phone, end your reply with exactly one line of the form "
    "'ACTION: <name> [arg]'. Available actions: "
    "flashlight on, flashlight off, battery, open_url <url>, "
    "set_volume <0-15>, vibrate. Only use an action when the user asks for it."
)


def run(cmd, timeout=30):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def speak(text):
    print(f"Jarvis: {text}")
    run(["termux-tts-speak", text], timeout=120)


def listen():
    print("Listening...")
    text = run(["termux-speech-to-text"], timeout=60)
    print(f"You: {text}")
    return text


def do_action(line):
    m = re.match(r"ACTION:\s*(\w+)\s*(.*)", line.strip())
    if not m:
        return None
    name, arg = m.group(1), m.group(2).strip()
    if name == "flashlight":
        run(["termux-torch", "on" if "on" in arg else "off"])
    elif name == "battery":
        return run(["termux-battery-status"])
    elif name == "open_url" and arg:
        run(["termux-open-url", arg])
    elif name == "set_volume" and arg.isdigit():
        run(["termux-volume", "music", arg])
    elif name == "vibrate":
        run(["termux-vibrate"])
    return None


def ask(history):
    r = requests.post(
        API_URL,
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": 400, "system": SYSTEM, "messages": history},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def main():
    if not API_KEY:
        sys.exit("Set ANTHROPIC_API_KEY first (see README).")
    text_mode = "--text" in sys.argv
    history = []
    speak("Jarvis online. How can I help?")
    while True:
        user = input("You: ") if text_mode else listen()
        if not user:
            continue
        if user.lower().strip() in {"exit", "quit", "goodbye", "shut down"}:
            speak("Goodbye.")
            break
        history.append({"role": "user", "content": user})
        try:
            reply = ask(history)
        except Exception as e:  # noqa: BLE001
            speak("I couldn't reach my brain. Check your connection or API key.")
            print(e)
            history.pop()
            continue
        history.append({"role": "assistant", "content": reply})
        history = history[-20:]
        lines = reply.splitlines()
        spoken = " ".join(l for l in lines if not l.startswith("ACTION:"))
        extra = None
        for l in lines:
            if l.startswith("ACTION:"):
                extra = do_action(l)
        speak(spoken or "Done.")
        if extra:
            print(extra)


if __name__ == "__main__":
    main()
