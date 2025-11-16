import base64
import os
import re
import sys
from tqdm import tqdm
from ankideck.utils import invoke, strip_html, make_tts



def main():
    if len(sys.argv) < 2:
        print("Usage: python add_tts.py <deck_name> [tts_engine] [elevenlabs_api_key_file] [add_back_voice]")
        print("  deck_name: Name of the Anki deck")
        print("  tts_engine: 'gtts' or 'elevenlabs' (default: 'gtts')")
        print("  elevenlabs_api_key_file: Path to ElevenLabs API key file")
        print("                           (default: '/Users/tng/Projects/Language/FR/Anki_decks/elevenlabs_api_key.txt')")
        print("  add_back_voice: 'true' or 'false' - whether to add voice for Back field (default: 'true')")
        sys.exit(1)

    DECK_NAME = sys.argv[1].replace(" ", "_")
    
    # TTS Engine Selection: "gtts" or "elevenlabs"
    TTS_ENGINE = sys.argv[2] if len(sys.argv) > 2 else "gtts"
    ELEVENLABS_API_KEY_FILE = sys.argv[3] if len(sys.argv) > 3 else "/Users/tng/Projects/Language/FR/Anki_decks/elevenlabs_api_key.txt"
    ADD_BACK_VOICE = sys.argv[4].lower() in ('true', 'yes', '1') if len(sys.argv) > 4 else True
    
    FRONT_FIELD = "Front"   # فیلد جمله یا عبارت فرانسوی
    BACK_FIELD = "Back"     # فیلد توضیح و مثال‌ها
    LANG = "fr"
    TTS_SLOW = False
    SLEEP_TIME = 0.4
    CACHE_DIR = f"tts_cache_{DECK_NAME}"
    PAUSE_DURATION = 700  # milliseconds
    # -----------------------------

    os.makedirs(CACHE_DIR, exist_ok=True)

    # 1️⃣ یافتن کارت‌ها
    cards = invoke("findCards", query=f'deck:"{DECK_NAME}"')
    print(f"✅ {len(cards)} کارت در دک '{DECK_NAME}' یافت شد.")
    print(f"🔊 موتور TTS: {TTS_ENGINE.upper()}")
    print(f"📝 افزودن صدا به Front: بله")
    print(f"📝 افزودن صدا به Back: {'بله' if ADD_BACK_VOICE else 'خیر'}\n")

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
            if clean_front:
                front_name = f"tts_{note_id}_front.mp3"
                front_sentences = [clean_front]
                path = make_tts(
                    sentences=front_sentences, 
                    filename=front_name, 
                    cache_dir=CACHE_DIR,
                    engine=TTS_ENGINE,
                    pause=False,
                    pause_duration=PAUSE_DURATION,
                    lang=LANG,
                    tts_slow=TTS_SLOW,
                    sleep_time=SLEEP_TIME,
                    elevenlabs_api_key_file=ELEVENLABS_API_KEY_FILE
                )
                if path:
                    with open(path, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
                    invoke("storeMediaFile", filename=front_name, data=audio_b64)
                    sound_tag = f"<br>[sound:{front_name}]"
                    new_val = front_val + sound_tag
                    invoke("updateNoteFields", note={"id": note_id, "fields": {FRONT_FIELD: new_val}})

        # ---------- BACK ----------
        if ADD_BACK_VOICE and back_val.strip() and "[sound:" not in back_val:
            clean_back = strip_html(back_val)
            if clean_back:
                back_name = f"tts_{note_id}_back.mp3"
                back_sentences = re.split(r'(?<=[.?!;])\s+', clean_back)
                path = make_tts(
                    sentences=back_sentences, 
                    filename=back_name, 
                    cache_dir=CACHE_DIR,
                    engine=TTS_ENGINE,
                    pause=True,
                    pause_duration=PAUSE_DURATION,
                    lang=LANG,
                    tts_slow=TTS_SLOW,
                    sleep_time=SLEEP_TIME,
                    elevenlabs_api_key_file=ELEVENLABS_API_KEY_FILE
                )
                if path:
                    with open(path, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
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
