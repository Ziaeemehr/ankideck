"""Text-to-speech generation for Anki card audio.

Supported engines:
  - gtts: Google Text-to-Speech (free, requires internet)
  - elevenlabs: ElevenLabs API (higher quality, requires API key)

Usage example:
    from ankideck.tts import make_tts
    path = make_tts(["Bonjour le monde"], "hello.mp3", "tts_cache", engine="gtts", lang="fr")
"""

import os
import re
from typing import List, Optional


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _remove_non_latin(text: str) -> str:
    """Strip non-Latin scripts (e.g. Arabic/Persian) before sending to TTS."""
    cleaned = re.sub(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]+", "", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def make_tts_gtts(
    sentences: List[str],
    audio_path: str,
    lang: str = "fr",
    pause: bool = False,
    pause_duration: int = 700,
    tts_slow: bool = False,
    sleep_time: float = 0.4,
) -> Optional[str]:
    """Generate audio using Google TTS and save to audio_path.

    Returns the path on success, None on failure.
    """
    from gtts import gTTS
    from pydub import AudioSegment
    import time

    try:
        combined = AudioSegment.silent(duration=0)
        cache_dir = os.path.dirname(audio_path) or "."

        for sent in sentences:
            if not sent.strip():
                continue
            tts = gTTS(sent, lang=lang, slow=tts_slow)
            temp_path = os.path.join(cache_dir, "_tmp_tts.mp3")
            tts.save(temp_path)
            clip = AudioSegment.from_mp3(temp_path)
            combined += clip
            if pause:
                combined += AudioSegment.silent(duration=pause_duration)

        combined.export(audio_path, format="mp3")
        time.sleep(sleep_time)
        return audio_path
    except Exception as e:
        print(f"gTTS error: {e}")
        return None


def make_tts_elevenlabs(
    text: str,
    api_key_file: str,
    filename: str,
    cache_dir: str,
) -> Optional[str]:
    """Generate audio using the ElevenLabs API.

    Returns the file path on success, None on failure.
    """
    from elevenlabs.client import ElevenLabs

    text = _remove_non_latin(text)
    if not text.strip():
        return None

    try:
        with open(api_key_file, encoding="utf-8") as f:
            api_key = f.read().strip()

        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        os.makedirs(cache_dir, exist_ok=True)
        audio_path = os.path.join(cache_dir, filename)
        with open(audio_path, "wb") as f:
            f.write(b"".join(audio))
        return audio_path
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return None


def make_tts(
    sentences: List[str],
    filename: str,
    cache_dir: str,
    engine: str = "gtts",
    pause: bool = False,
    pause_duration: int = 700,
    lang: str = "fr",
    tts_slow: bool = False,
    sleep_time: float = 0.4,
    elevenlabs_api_key_file: Optional[str] = None,
) -> Optional[str]:
    """Generate TTS audio and cache it to disk.

    Returns the file path if successful, None otherwise.
    Skips generation if the file already exists in cache.
    """
    audio_path = os.path.join(cache_dir, filename)
    if os.path.exists(audio_path):
        return audio_path

    if engine == "elevenlabs":
        if not elevenlabs_api_key_file:
            print("ElevenLabs API key file not provided.")
            return None
        combined_text = " ".join(s.strip() for s in sentences if s.strip())
        if not combined_text:
            return None
        return make_tts_elevenlabs(
            text=combined_text,
            api_key_file=elevenlabs_api_key_file,
            filename=filename,
            cache_dir=cache_dir,
        )

    # Default: gTTS
    return make_tts_gtts(
        sentences=sentences,
        audio_path=audio_path,
        lang=lang,
        pause=pause,
        pause_duration=pause_duration,
        tts_slow=tts_slow,
        sleep_time=sleep_time,
    )
