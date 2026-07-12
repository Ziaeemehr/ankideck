import base64
import os
import re
import sys
from tqdm import tqdm
from ankideck.anki_connect import invoke
from ankideck.tts import make_tts, strip_html



def main():
    if len(sys.argv) < 2:
        print("Usage: python add_tts.py <deck_name> [front_engine] [back_engine] [elevenlabs_api_key_file]")
        print("  deck_name: Name of the Anki deck")
        print("  front_engine: 'edge', 'gtts', or 'elevenlabs' (default: 'edge')")
        print("  back_engine: 'edge', 'gtts', 'elevenlabs', or 'none' to skip Back (default: 'edge')")
        print("  elevenlabs_api_key_file: Path to ElevenLabs API key file")
        print("                           (default: '/Users/tng/Projects/Language/FR/Anki_decks/elevenlabs_api_key.txt')")
        print("\nExamples:")
        print("  python add_tts.py 'My Deck'  # Both fields with Edge TTS")
        print("  python add_tts.py 'My Deck' elevenlabs gtts  # Front with ElevenLabs, Back with gtts")
        print("  python add_tts.py 'My Deck' elevenlabs none  # Only Front with ElevenLabs")
        sys.exit(1)

    DECK_NAME = sys.argv[1].replace(" ", "_")

    # TTS Engine Selection for Front and Back
    FRONT_ENGINE = sys.argv[2] if len(sys.argv) > 2 else "edge"
    BACK_ENGINE = sys.argv[3] if len(sys.argv) > 3 else "edge"
    ELEVENLABS_API_KEY_FILE = sys.argv[4] if len(sys.argv) > 4 else "/Users/tng/Projects/Language/FR/Anki_decks/elevenlabs_api_key.txt"
    
    # Check if back voice should be added
    ADD_BACK_VOICE = BACK_ENGINE.lower() != "none"
    
    FRONT_FIELD = "Front"   # فیلد جمله یا عبارت فرانسوی
    BACK_FIELD = "Back"     # فیلد توضیح و مثال‌ها
    LANG = "fr"
    TTS_SLOW = False
    SLEEP_TIME = 1.0
    CACHE_DIR = f"tts_cache_{DECK_NAME}"
    PAUSE_DURATION = 700  # milliseconds
    # -----------------------------

    os.makedirs(CACHE_DIR, exist_ok=True)

    # 1️⃣ یافتن کارت‌ها
    cards = invoke("findCards", query=f'deck:"{DECK_NAME}"')
    print(f"✅ {len(cards)} کارت در دک '{DECK_NAME}' یافت شد.")
    print(f"🔊 موتور TTS برای Front: {FRONT_ENGINE.upper()}")
    print(f"� موتور TTS برای Back: {BACK_ENGINE.upper() if ADD_BACK_VOICE else 'خیر'}\n")

    notes = invoke("cardsToNotes", cards=cards)
    notes_info = invoke("notesInfo", notes=notes)

    for note in tqdm(notes_info, desc="🔊 تولید تلفظ برای Front و Back"):
        note_id = note["noteId"]
        fields = note["fields"]

        front_val = fields.get(FRONT_FIELD, {}).get("value", "")
        back_val = fields.get(BACK_FIELD, {}).get("value", "")

        if not front_val.strip() and not back_val.strip():
            continue

        # ---------- FRONT ----------
        if front_val.strip() and "[sound:" not in front_val:
            clean_front = strip_html(front_val)
            if clean_front.strip():
                front_name = f"tts_{note_id}_front.mp3"
                front_sentences = [clean_front]
                path = make_tts(
                    sentences=front_sentences, 
                    filename=front_name, 
                    cache_dir=CACHE_DIR,
                    engine=FRONT_ENGINE,
                    pause=False,
                    pause_duration=PAUSE_DURATION,
                    lang=LANG,
                    tts_slow=TTS_SLOW,
                    sleep_time=SLEEP_TIME,
                    elevenlabs_api_key_file=ELEVENLABS_API_KEY_FILE
                )
                if path:
                    with open(path, "rb") as f:
                        audio_data = f.read()
                        if not audio_data:
                            print(f"⚠️ Skipping empty audio for front of note {note_id}")
                            continue
                        audio_b64 = base64.b64encode(audio_data).decode()
                    invoke("storeMediaFile", filename=front_name, data=audio_b64)
                    sound_tag = f"<br>[sound:{front_name}]"
                    new_val = front_val + sound_tag
                    invoke("updateNoteFields", note={"id": note_id, "fields": {FRONT_FIELD: new_val}})

        # ---------- BACK ----------
        if ADD_BACK_VOICE and back_val.strip() and "[sound:" not in back_val:
            clean_back = strip_html(back_val)
            if clean_back.strip():
                back_name = f"tts_{note_id}_back.mp3"
                back_sentences = re.split(r'(?<=[.?!;])\s+', clean_back)
                path = make_tts(
                    sentences=back_sentences, 
                    filename=back_name, 
                    cache_dir=CACHE_DIR,
                    engine=BACK_ENGINE,
                    pause=True,
                    pause_duration=PAUSE_DURATION,
                    lang=LANG,
                    tts_slow=TTS_SLOW,
                    sleep_time=SLEEP_TIME,
                    elevenlabs_api_key_file=ELEVENLABS_API_KEY_FILE
                )
                if path:
                    with open(path, "rb") as f:
                        audio_data = f.read()
                        if not audio_data:
                            print(f"⚠️ Skipping empty audio for back of note {note_id}")
                            continue
                        audio_b64 = base64.b64encode(audio_data).decode()
                    invoke("storeMediaFile", filename=back_name, data=audio_b64)
                    sound_tag = f"<br>[sound:{back_name}]"
                    new_val = back_val + sound_tag
                    invoke("updateNoteFields", note={"id": note_id, "fields": {BACK_FIELD: new_val}})

    if ADD_BACK_VOICE:
        print("\n✅ تلفظ‌ها برای هر دو فیلد (Front و Back) با مکث طبیعی ساخته شدند 🎧")
    else:
        print("\n✅ تلفظ‌ها برای فیلد Front ساخته شدند 🎧")


if __name__ == "__main__":
    main()
