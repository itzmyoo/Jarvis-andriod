#!/usr/bin/env python3
"""Jarvis: a voice assistant for Android (Termux + Termux:API).

Uses the free Google Gemini API by default (GEMINI_API_KEY).
If ANTHROPIC_API_KEY is set and no Gemini key exists, it uses Claude instead.

Usage:
    python jarvis.py          # voice mode (one question at a time)
    python jarvis.py --wake   # always listening, reacts to "Hey Jarvis"
    python jarvis.py --once   # push-to-talk: answer one question, then exit
    python jarvis.py --text   # type instead of speak
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import requests

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.environ.get("JARVIS_MODEL", "gemini-2.5-flash")
CLAUDE_MODEL = "claude-sonnet-5-5"
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]
WAKE_WORDS = (
    "jarvis", "jervis", "jarvice", "jarvas", "jarvus",
    "javis", "javed", "jarvi", "jarves",
)

SYSTEM = (
    "You are Jarvis, a concise, friendly voice assistant running on an Android phone. "
    "Reply in at most 3 short sentences, in plain speech (no markdown, no asterisks). "
    "To control the phone, end your reply with exactly one line of the form "
    "'ACTION: <n> [arg]'. Available actions: "
    "flashlight on, flashlight off, battery, open_url <url>, "
    "set_volume <0-15>, vibrate. Only use an action when the user asks for it."
)


def system_prompt():
    now = datetime.now().strftime("%A, %B %d %Y, %I:%M %p")
    return SYSTEM + f" The current date and time is {now}."


def run(cmd, timeout=30):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def get_volume(stream):
    try:
        for v in json.loads(run(["termux-volume"])):
            if v["stream"] == stream:
                return v["volume"]
    except Exception:  # noqa: BLE001
        pass
    return None


def speak(text):
    print(f"Jarvis: {text}")
    run(["termux-tts-speak", "-s", "MUSIC", text], timeout=120)


def listen():
    print("Listening...")
    text = run(["termux-speech-to-text"], timeout=60)
    if text.startswith("error:"):
        text = ""
    print(f"Heard: {text}")
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
    models = [GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != GEMINI_MODEL]
    last_err = None
    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        try:
            r = requests.post(
                url,
                headers={"x-goog-api-key": GEMINI_KEY,
                         "content-type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt()}]},
                    "contents": contents,
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[{model}] {e}")
    raise last_err


def ask_claude(history):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": CLAUDE_MODEL, "max_tokens": 400,
              "system": system_prompt(), "messages": history},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def ask(history):
    return ask_gemini(history) if GEMINI_KEY else ask_claude(history)


def extract_command(heard):
    """Return the text after the wake word, or None if no wake word was said."""
    low = heard.lower()
    for w in WAKE_WORDS:
        i = low.find(w)
        if i != -1:
            return heard[i + len(w):].strip(" ,.!?")
    return None


def respond(user, history):
    history.append({"role": "user", "content": user})
    try:
        reply = ask(history)
    except Exception as e:  # noqa: BLE001
        speak("I couldn't reach my brain. Try again in a moment.")
        print(e)
        history.pop()
        return history
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
    return history


def is_exit(text):
    return text.lower().strip(" .!") in {"exit", "quit", "goodbye", "shut down",
                                         "stop listening"}


def main():
    if not (GEMINI_KEY or ANTHROPIC_KEY):
        sys.exit("No API key found. Run: source ~/.jarvis_env  (see README).")
    text_mode = "--text" in sys.argv
    wake_mode = "--wake" in sys.argv
    once_mode = "--once" in sys.argv
    history = []
    saved_vol = None

    if wake_mode:
        run(["termux-wake-lock"])  # keeps Termux alive with the screen off
        # Mute the notification stream so the mic beep is silent.
        saved_vol = get_volume("notification")
        run(["termux-volume", "notification", "0"])
        speak("Wake mode on. Say Jarvis, then your request.")
    elif once_mode:
        speak("Yes?")
    else:
        speak("Jarvis online. How can I help?")

    try:
        while True:
            if text_mode:
                user = input("You: ")
            elif wake_mode:
                heard = listen()
                if not heard:
                    time.sleep(0.5)
                    continue
                user = extract_command(heard)
                if user is None:
                    continue  # no wake word, ignore
                if not user:
                    speak("Yes?")
                    user = listen()
            else:
                user = listen()
            if not user:
                if once_mode:
                    speak("I didn't catch that.")
                    break
                continue
            if is_exit(user):
                speak("Goodbye.")
                break
            history = respond(user, history)
            if once_mode:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if wake_mode:
            run(["termux-wake-unlock"])
            run(["termux-volume", "notification",
                 str(saved_vol if saved_vol is not None else 7)])


if __name__ == "__main__":
    main()
