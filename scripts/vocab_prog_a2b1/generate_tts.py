"""Generate French audio for each example sentence in manifest_translated.json.

Resumable: skips files already present in the cache dir. Uses the repo's
existing edge-TTS wrapper with the same default French voice used elsewhere
(fr-FR-VivienneMultilingualNeural).

Run:
    python3 scripts/gram_diag_b1/generate_tts.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tqdm import tqdm
from ankideck.tts import make_tts

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest_translated.json"
CACHE_DIR = HERE / "tts_cache"


def audio_filename(note_id: int) -> str:
    return f"tts_vocab_prog_a2b1_{note_id}.mp3"


def main():
    entries = json.loads(MANIFEST.read_text())
    CACHE_DIR.mkdir(exist_ok=True)

    ok = fail = 0
    for entry in tqdm(entries, desc="Generating French audio", unit="card"):
        fname = audio_filename(entry["note_id"])
        path = make_tts(
            [entry["example_fr"]],
            fname,
            str(CACHE_DIR),
            engine="edge",
            lang="fr",
        )
        if path:
            ok += 1
        else:
            fail += 1
            print(f"  FAILED: note {entry['note_id']}: {entry['example_fr']!r}")

    print(f"\n{ok} audio files ready in {CACHE_DIR}, {fail} failed.")


if __name__ == "__main__":
    main()
