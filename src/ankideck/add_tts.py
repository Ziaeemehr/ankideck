import base64
import os
import re
import sys
import time
from gtts import gTTS
import requests
from tqdm import tqdm
from pydub import AudioSegment


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_tts_general.py <deck_name>")
        sys.exit(1)

    DECK_NAME = sys.argv[1].replace(" ", "_")
    FRONT_FIELD = "Front"   # فیلد جمله یا عبارت فرانسوی
    BACK_FIELD = "Back"     # فیلد توضیح و مثال‌ها
    LANG = "fr"
    TTS_SLOW = False
    SLEEP_TIME = 0.4
    CACHE_DIR = f"tts_cache_{DECK_NAME}"
    PAUSE_DURATION = 700  # milliseconds
    # -----------------------------

    os.makedirs(CACHE_DIR, exist_ok=True)

    def invoke(action, **params):
        r = requests.post("http://localhost:8765", json={
            "action": action,
            "version": 6,
            "params": params
        }).json()
        if r.get("error"):
            raise Exception(r["error"])
        return r["result"]

    def strip_html(text):
        return re.sub(r"<.*?>", "", text).strip()

    def make_tts(sentences, filename, pause=False):
        """ساخت صدا با یا بدون مکث بین جمله‌ها"""
        audio_path = os.path.join(CACHE_DIR, filename)
        if os.path.exists(audio_path):
            return audio_path

        try:
            combined = AudioSegment.silent(duration=0)
            for sent in sentences:
                if not sent.strip():
                    continue
                tts = gTTS(sent, lang=LANG, slow=TTS_SLOW)
                temp_path = os.path.join(CACHE_DIR, "temp.mp3")
                tts.save(temp_path)
                clip = AudioSegment.from_mp3(temp_path)
                combined += clip
                if pause:
                    combined += AudioSegment.silent(duration=PAUSE_DURATION)
            combined.export(audio_path, format="mp3")
            time.sleep(SLEEP_TIME)
            return audio_path
        except Exception as e:
            print(f"⚠️ خطا در ساخت صدا: {e}")
            return None

    # 1️⃣ یافتن کارت‌ها
    cards = invoke("findCards", query=f'deck:"{DECK_NAME}"')
    print(f"✅ {len(cards)} کارت در دک '{DECK_NAME}' یافت شد.\n")

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
                path = make_tts(front_sentences, front_name, pause=False)
                if path:
                    with open(path, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
                    invoke("storeMediaFile", filename=front_name, data=audio_b64)
                    sound_tag = f"<br>[sound:{front_name}]"
                    new_val = front_val + sound_tag
                    invoke("updateNoteFields", note={"id": note_id, "fields": {FRONT_FIELD: new_val}})

        # ---------- BACK ----------
        if back_val.strip() and "[sound:" not in back_val:
            clean_back = strip_html(back_val)
            if clean_back:
                back_name = f"tts_{note_id}_back.mp3"
                back_sentences = re.split(r'(?<=[.?!;])\s+', clean_back)
                path = make_tts(back_sentences, back_name, pause=True)
                if path:
                    with open(path, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
                    invoke("storeMediaFile", filename=back_name, data=audio_b64)
                    sound_tag = f"<br>[sound:{back_name}]"
                    new_val = back_val + sound_tag
                    invoke("updateNoteFields", note={"id": note_id, "fields": {BACK_FIELD: new_val}})

    print("\n✅ تلفظ‌ها برای هر دو فیلد (Front و Back) با مکث طبیعی ساخته شدند 🎧")


if __name__ == "__main__":
    main()
