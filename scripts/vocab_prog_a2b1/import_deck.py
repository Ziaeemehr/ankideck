"""Create the Gram_diag_B1 deck in Anki and add notes via AnkiConnect.

Front = Persian translation (example_fa), no audio.
Back   = French example sentence (example_fr) + audio.
Model  = "Basic+" (same note type used by Communication essentielle A2).

Mirrors the 39 lesson subdeck names from "Grammaire en dialogues B1" under
"Gram_diag_B1::<lesson>". Idempotent: skips a note if one with the same
Front already exists in that subdeck, so it's safe to re-run after fixing
translations or regenerating audio.

Run:
    python3 scripts/gram_diag_b1/import_deck.py
    python3 scripts/gram_diag_b1/import_deck.py --dry-run
"""
import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tqdm import tqdm
from ankideck.anki_connect import invoke

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest_translated.json"
CACHE_DIR = HERE / "tts_cache"
DECK_ROOT = "Vocab_Prog_A2B1"
MODEL_NAME = "Basic+"


def audio_filename(note_id: int) -> str:
    return f"tts_vocab_prog_a2b1_{note_id}.mp3"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    entries = json.loads(MANIFEST.read_text())

    lessons = sorted({e["lesson"] for e in entries})
    print(f"{len(entries)} notes across {len(lessons)} lessons")

    if not args.dry_run:
        invoke("createDeck", deck=DECK_ROOT)
        for lesson in lessons:
            invoke("createDeck", deck=f"{DECK_ROOT}::{lesson}")

    added = skipped_dup = skipped_media = 0
    for entry in tqdm(entries, desc="Importing notes", unit="card"):
        deck = f"{DECK_ROOT}::{entry['lesson']}"
        front = entry["example_fa"]
        fname = audio_filename(entry["note_id"])
        audio_path = CACHE_DIR / fname

        if not audio_path.exists():
            skipped_media += 1
            print(f"  no audio for note {entry['note_id']}, skipping: {entry['example_fr']!r}")
            continue

        back = f"{entry['example_fr']}<br>[sound:{fname}]"

        if args.dry_run:
            added += 1
            continue

        existing = invoke("findNotes", query=f'deck:"{deck}" Front:"{front}"')
        if existing:
            skipped_dup += 1
            continue

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        invoke("storeMediaFile", filename=fname, data=audio_b64)

        try:
            invoke(
                "addNote",
                note={
                    "deckName": deck,
                    "modelName": MODEL_NAME,
                    "fields": {"Front": front, "Back": back},
                    "options": {"allowDuplicate": False},
                    "tags": ["Vocab_Prog_A2B1"],
                },
            )
            added += 1
        except Exception as e:
            if "duplicate" in str(e).lower():
                skipped_dup += 1
            else:
                raise

    print(f"\nAdded {added}, skipped {skipped_dup} duplicates, {skipped_media} missing audio.")


if __name__ == "__main__":
    main()
