"""
Alexa-like voice assistant (terminal-only)
Python 3.11+ | No PyAudio required | Uses sounddevice for recording
"""

import speech_recognition as sr
import pyttsx3
import pywhatkit
import datetime
import wikipedia
import pyjokes
import requests
import os
import webbrowser
import time
import ctypes
import pyautogui
import psutil
import threading
import sounddevice as sd
import numpy as np
import sys

# ---------------------------
# CONFIG
# ---------------------------
OPENWEATHER_API_KEY = ""   # Optional
NEWSAPI_KEY = ""           # Optional
SAMPLE_RATE = 16000
RECORD_SECONDS = 3

# ---------------------------
# INITIALIZE
# ---------------------------
listener = sr.Recognizer()
engine = pyttsx3.init()
voices = engine.getProperty("voices")
try:
    engine.setProperty("voice", voices[1].id)  # female voice
except Exception:
    pass

def talk(text: str):
    """Speak and print Alexa's response."""
    print("Alexa:", text)
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("TTS error:", e)

# ---------------------------
# AUDIO RECORDING
# ---------------------------
def record_audio(duration=RECORD_SECONDS, fs=SAMPLE_RATE):
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
        audio_np = np.squeeze(recording)
        audio_bytes = audio_np.tobytes()
        return sr.AudioData(audio_bytes, fs, 2)
    except Exception as e:
        print("Recording error:", e)
        return None

def listen_once(timeout_seconds=RECORD_SECONDS):
    audio_data = record_audio(duration=timeout_seconds)
    if not audio_data:
        return ""
    try:
        return listener.recognize_google(audio_data).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        talk("Speech recognition service unavailable.")
        return ""
    except Exception as e:
        print("Recognition error:", e)
        return ""

# ---------------------------
# UTILS
# ---------------------------
def open_website_or_app(name: str):
    mapping = {
        "youtube": "https://youtube.com",
        "facebook": "https://facebook.com",
        "gmail": "https://mail.google.com",
        "whatsapp": "https://web.whatsapp.com",
        "google": "https://google.com",
        "chatgpt": "https://chat.openai.com",
        "news": "https://news.google.com"
    }
    url = mapping.get(name)
    if url:
        webbrowser.open(url)
        talk(f"Opening {name}")
    elif "." in name or name.startswith("http"):
        webbrowser.open(name)
        talk(f"Opening {name}")
    else:
        talk(f"I don't have a direct mapping for {name}. Searching Google.")
        webbrowser.open(f"https://www.google.com/search?q={name}")

def get_time():
    return datetime.datetime.now().strftime("%I:%M %p")

def get_date():
    return datetime.datetime.now().strftime("%A, %B %d, %Y")

def get_weather(city: str):
    if not city:
        return "Please provide a city name."
    if OPENWEATHER_API_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
            r = requests.get(url, timeout=5).json()
            if r.get("main"):
                temp = r["main"]["temp"]
                desc = r["weather"][0]["description"]
                return f"The temperature in {city} is {temp}°C with {desc}."
            return f"Could not fetch weather for {city}."
        except Exception:
            return "Weather service error."
    try:
        r = requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return r.text
    except Exception:
        return "Could not fetch weather."

def get_news():
    if NEWSAPI_KEY:
        try:
            url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWSAPI_KEY}"
            r = requests.get(url, timeout=5).json()
            articles = r.get("articles", [])[:5]
            headlines = [a.get("title", "No title") for a in articles]
            return "Top headlines: " + " | ".join(headlines) if headlines else "No headlines found."
        except Exception:
            return "News service error."
    webbrowser.open("https://news.google.com")
    return "Opened Google News in your browser."

# ---------------------------
# ALARM
# ---------------------------
def alarm_worker(time_str):
    talk(f"Alarm scheduled for {time_str}")
    while True:
        if datetime.datetime.now().strftime("%H:%M") == time_str:
            talk("Alarm! It's time.")
            for _ in range(3):
                print("\a")
                time.sleep(1)
            break
        time.sleep(5)

def set_alarm(time_str):
    threading.Thread(target=alarm_worker, args=(time_str,), daemon=True).start()

# ---------------------------
# SYSTEM CONTROLS
# ---------------------------
def take_screenshot():
    try:
        filename = f"screenshot_{int(time.time())}.png"
        img = pyautogui.screenshot()
        img.save(filename)
        return filename
    except Exception:
        return None

def lock_screen():
    try:
        ctypes.windll.user32.LockWorkStation()
        return True
    except Exception:
        return False

def shutdown_pc():
    os.system("shutdown /s /t 1")

def restart_pc():
    os.system("shutdown /r /t 1")

def battery_info():
    try:
        bat = psutil.sensors_battery()
        if not bat:
            return "Battery information not available."
        status = "plugged in" if bat.power_plugged else "not plugged in"
        return f"Battery at {bat.percent}% and {status}."
    except Exception:
        return "Could not get battery information."

def change_volume_percent(percent: int):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(max(0, min(100, percent)) / 100.0, None)
        return True
    except Exception:
        return False

# ---------------------------
# COMMAND PROCESSOR
# ---------------------------
def process_command(command: str):
    command = command.strip().lower()
    if not command:
        talk("I didn't catch that.")
        return

    if command.startswith("play "):
        song = command.replace("play ", "", 1)
        talk(f"Playing {song} on YouTube.")
        pywhatkit.playonyt(song)
        return

    if "time" in command and "date" not in command:
        talk("The current time is " + get_time())
        return

    if "date" in command:
        talk("Today's date is " + get_date())
        return

    if "weather" in command:
        city = ""
        if "in " in command:
            city = command.split("in ", 1)[1].strip()
        if not city:
            talk("Which city?")
            city = listen_once(timeout_seconds=3)
        talk(get_weather(city))
        return

    if "news" in command:
        talk(get_news())
        return

    if "set alarm" in command or command.startswith("alarm"):
        import re
        m = re.search(r'(\d{1,2}[:.]\d{2})', command)
        if m:
            t = m.group(1).replace(".", ":")
            try:
                h, mi = map(int, t.split(":"))
                set_alarm(f"{h:02d}:{mi:02d}")
                talk(f"Alarm set for {h:02d}:{mi:02d}")
            except Exception:
                talk("Could not parse that time.")
        else:
            talk("Please say the time like 'set alarm for 07:30'.")
        return

    if "open " in command:
        target = command.replace("open ", "", 1)
        open_website_or_app(target)
        return

    if "search" in command or command.startswith(("what is", "who is", "what are")):
        query = command
        for prefix in ["search", "search for", "what is", "who is", "what are"]:
            if query.startswith(prefix):
                query = query.replace(prefix, "", 1).strip()
        if query:
            try:
                talk(wikipedia.summary(query, sentences=2, auto_suggest=False, redirect=True))
            except Exception:
                talk("Couldn't find a quick answer. Searching Google.")
                webbrowser.open(f"https://www.google.com/search?q={query}")
        else:
            talk("Please say what you want to search.")
        return

    if "screenshot" in command:
        fn = take_screenshot()
        talk(f"Screenshot saved as {fn}" if fn else "Could not take screenshot.")
        return

    if "lock" in command:
        talk("Screen locked." if lock_screen() else "Could not lock screen.")
        return

    if "shutdown" in command:
        talk("Shutting down in 5 seconds.")
        time.sleep(5)
        shutdown_pc()
        return

    if "restart" in command:
        talk("Restarting in 5 seconds.")
        time.sleep(5)
        restart_pc()
        return

    if "battery" in command:
        talk(battery_info())
        return

    if "joke" in command:
        talk(pyjokes.get_joke())
        return

    if "volume" in command:
        import re
        m = re.search(r'(\d{1,3})', command)
        if m:
            percent = int(m.group(1))
            talk(f"Volume set to {percent}%" if change_volume_percent(percent) else "Couldn't change volume.")
        else:
            talk("Please say a volume percentage, e.g., 'volume 50'.")
        return

    if "who are you" in command or "what can you do" in command:
        talk("I am your desktop assistant. I can play music, fetch weather and news, set alarms, open websites, take screenshots, and more.")
        return

    if any(word in command for word in ["stop", "exit", "goodbye", "quit"]):
        talk("Goodbye! Exiting now.")
        sys.exit(0)

    talk("I didn't understand that. Searching the web.")
    webbrowser.open(f"https://www.google.com/search?q={command}")

# ---------------------------
# MAIN LOOP
# ---------------------------
def main_loop():
    talk("Hello! Alexa is now running. Say 'Alexa' followed by a command.")
    while True:
        text = listen_once(timeout_seconds=RECORD_SECONDS)
        if not text:
            continue
        print("Heard:", text)
        if "alexa" in text:
            text = text.replace("alexa", "").strip()
            process_command(text)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        talk("Goodbye!")
        sys.exit(0)
