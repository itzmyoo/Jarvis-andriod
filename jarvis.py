#!/usr/bin/env python3
"""Jarvis: a voice assistant for Android (Termux + Termux:API).

Uses the free Google Gemini API by default (GEMINI_API_KEY).
If ANTHROPIC_API_KEY is set and no Gemini key exists, it uses Claude instead.

Usage:
    python jarvis.py          # voice mode
    python jarvis.py --text   # type instead of speak
"""
import os
import re
import subprocess
import sys

import requests

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.environ.get("JARVIS_MODEL", "gemini-2.5-flash")
CLAUDE_MODEL = "claude-sonnet-5-5"

SYSTEM = (
    "You are Jarvis, a concise, witty voice assistant running on an Android phone. "
    "Reply in at most 3 short sentences, in plain speech (no markdown, no asterisks). "
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


def ask_gemini(history):
    contents = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [{"text": m["content"]}]}
        for m in history
    ]
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    r = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_KEY, "content-type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": SYSTEM}]},
            "contents": contents,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def ask_claude(history):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": CLAUDE_MODEL, "max_tokens": 400,
              "system": SYSTEM, "messages": history},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def ask(history):
    return ask_gemini(history) if GEMINI_KEY else ask_claude(history)


def main():
    if not (GEMINI_KEY or ANTHROPIC_KEY):
        sys.exit("No API key found. Run: source ~/.jarvis_env  (see README).")
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
