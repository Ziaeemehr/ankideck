"""Text-to-speech generation for Anki card audio.

Supported engines:
  - edge: Microsoft Edge TTS (free, requires internet, natural-sounding voices) [default]
  - gtts: Google Text-to-Speech (free, requires internet)
  - elevenlabs: ElevenLabs API (higher quality, requires API key)
  - voicebox: local Voicebox app (offline, no API key, requires the app running)

Usage example:
    from ankideck.tts import make_tts
    path = make_tts(["Bonjour le monde"], "hello.mp3", "tts_cache", engine="edge", lang="fr")
"""

import os
import re
from typing import List, Optional


def _temp_path(audio_path: str, suffix: str) -> str:
    """A scratch path unique to this output file.

    The temp name must not be shared: callers may synthesize several clips
    at once (see scripts/revoice_deck.py --jobs), and a fixed name means one
    worker reads the half-written file of another and the wrong audio ends
    up under the wrong name.
    """
    directory = os.path.dirname(audio_path) or "."
    return os.path.join(directory, f".tmp_{os.path.basename(audio_path)}{suffix}")


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
        temp_path = _temp_path(audio_path, ".gtts.mp3")

        try:
            for sent in sentences:
                if not sent.strip():
                    continue
                tts = gTTS(sent, lang=lang, slow=tts_slow)
                tts.save(temp_path)
                clip = AudioSegment.from_mp3(temp_path)
                combined += clip
                if pause:
                    combined += AudioSegment.silent(duration=pause_duration)

            combined.export(audio_path, format="mp3")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        time.sleep(sleep_time)
        return audio_path
    except Exception as e:
        print(f"gTTS error: {e}")
        return None


# Default Edge TTS voice per language code. Override with the `voice`
# argument or by passing a full voice name as `lang` (e.g. "fr-FR-HenriNeural").
EDGE_DEFAULT_VOICES = {
    "fr": "fr-FR-VivienneMultilingualNeural",
    "en": "en-US-AriaNeural",
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
    "it": "it-IT-ElsaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "fa": "fa-IR-DilaraNeural",
}


def make_tts_edge(
    sentences: List[str],
    audio_path: str,
    lang: str = "fr",
    voice: Optional[str] = None,
    pause: bool = False,
    pause_duration: int = 700,
    rate: Optional[str] = None,
) -> Optional[str]:
    """Generate audio using Microsoft Edge TTS and save to audio_path.

    All sentences are sent as a single synthesis request (one network
    round-trip) rather than one request per sentence, since Edge TTS has
    no SSML break-tag support in this client and per-sentence round trips
    dominate runtime on bulk decks. Edge's neural voices already pause
    naturally at sentence-ending punctuation.

    Returns the path on success, None on failure.
    """
    import asyncio
    import edge_tts
    from pydub import AudioSegment

    voice_name = voice or EDGE_DEFAULT_VOICES.get(lang, lang)
    cache_dir = os.path.dirname(audio_path) or "."
    os.makedirs(cache_dir, exist_ok=True)

    text = " ".join(s.strip() for s in sentences if s.strip())
    if not text:
        return None

    async def _synth(text: str, out_path: str) -> None:
        kwargs = {"rate": rate} if rate else {}
        communicate = edge_tts.Communicate(text, voice_name, **kwargs)
        await communicate.save(out_path)

    try:
        temp_path = _temp_path(audio_path, ".edge.mp3")
        try:
            asyncio.run(_synth(text, temp_path))
            combined = AudioSegment.from_mp3(temp_path)
            if pause:
                combined += AudioSegment.silent(duration=pause_duration)

            combined.export(audio_path, format="mp3")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        return audio_path
    except Exception as e:
        print(f"Edge TTS error: {e}")
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


VOICEBOX_HOST = "http://127.0.0.1:17493"


def make_tts_voicebox(
    sentences: List[str],
    audio_path: str,
    profile_id: str,
    lang: str = "fr",
    host: str = VOICEBOX_HOST,
    vb_engine: str = "kokoro",
    pause: bool = False,
    pause_duration: int = 700,
    timeout: int = 600,
) -> Optional[str]:
    """Generate audio with a locally running Voicebox instance.

    Voicebox runs offline on the user's machine, so unlike edge/gtts it
    needs no internet but does need the desktop app (or its server) up.
    Generation is asynchronous: POST /generate returns an id, progress
    arrives as a server-sent event stream, and the finished WAV is then
    fetched and transcoded to mp3 for Anki.

    Returns the path on success, None on failure.
    """
    import json
    import requests
    from pydub import AudioSegment

    text = " ".join(s.strip() for s in sentences if s.strip())
    if not text:
        return None

    cache_dir = os.path.dirname(audio_path) or "."
    os.makedirs(cache_dir, exist_ok=True)

    try:
        resp = requests.post(
            f"{host}/generate",
            json={
                "profile_id": profile_id,
                "text": text,
                "language": lang,
                "engine": vb_engine,
            },
            timeout=60,
        )
        resp.raise_for_status()
        gen_id = resp.json()["id"]

        # /generate/{id}/status is an SSE stream, not plain JSON: consume
        # events until one reports a terminal state.
        status = None
        with requests.get(
            f"{host}/generate/{gen_id}/status", stream=True, timeout=timeout
        ) as stream:
            stream.raise_for_status()
            for line in stream.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                event = json.loads(line[len("data: "):])
                status = event.get("status")
                if status in ("completed", "failed", "error", "cancelled"):
                    break

        if status != "completed":
            print(f"Voicebox generation {status or 'did not finish'}.")
            return None

        audio = requests.get(f"{host}/audio/{gen_id}", timeout=timeout)
        audio.raise_for_status()

        temp_path = _temp_path(audio_path, ".voicebox.wav")
        try:
            with open(temp_path, "wb") as f:
                f.write(audio.content)

            combined = AudioSegment.from_file(temp_path)
            if pause:
                combined += AudioSegment.silent(duration=pause_duration)
            combined.export(audio_path, format="mp3")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        return audio_path
    except Exception as e:
        print(f"Voicebox error: {e}")
        return None


def make_tts(
    sentences: List[str],
    filename: str,
    cache_dir: str,
    engine: str = "edge",
    pause: bool = False,
    pause_duration: int = 700,
    lang: str = "fr",
    tts_slow: bool = False,
    sleep_time: float = 0.4,
    elevenlabs_api_key_file: Optional[str] = None,
    voice: Optional[str] = None,
    voicebox_profile_id: Optional[str] = None,
    voicebox_host: str = VOICEBOX_HOST,
    voicebox_engine: str = "kokoro",
    rate: Optional[str] = None,
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

    if engine == "voicebox":
        if not voicebox_profile_id:
            print("Voicebox profile id not provided.")
            return None
        return make_tts_voicebox(
            sentences=sentences,
            audio_path=audio_path,
            profile_id=voicebox_profile_id,
            lang=lang,
            host=voicebox_host,
            vb_engine=voicebox_engine,
            pause=pause,
            pause_duration=pause_duration,
        )

    if engine == "gtts":
        return make_tts_gtts(
            sentences=sentences,
            audio_path=audio_path,
            lang=lang,
            pause=pause,
            pause_duration=pause_duration,
            tts_slow=tts_slow,
            sleep_time=sleep_time,
        )

    # Default: Microsoft Edge TTS
    return make_tts_edge(
        sentences=sentences,
        audio_path=audio_path,
        lang=lang,
        voice=voice,
        pause=pause,
        pause_duration=pause_duration,
        rate=rate,
    )
