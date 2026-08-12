#!/usr/bin/env python3
"""Demo: build a small French deck voiced by the local Voicebox app.

Voicebox runs offline on your own machine, so the desktop app (or its
server) must be running before this script starts.  Find a profile id
with:

    curl -s http://127.0.0.1:17493/profiles

Run:
    python scripts/demo_voicebox.py <voicebox_profile_id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck import write_apkg
from ankideck.reader import Card

OUTPUT = "demo_voicebox.apkg"
DECK_NAME = "Demo Voicebox FR"

# Front is the French prompt that gets spoken; back is the English meaning
# plus an example sentence that gets its own audio.
CARDS = [
    ("Bonjour", "Hello / Good morning", "Bonjour, comment allez-vous ?"),
    ("Merci beaucoup", "Thank you very much", "Merci beaucoup pour votre aide."),
    ("Je voudrais un café", "I would like a coffee", "Je voudrais un café, s'il vous plaît."),
    ("Où est la gare ?", "Where is the train station?", "Excusez-moi, où est la gare ?"),
    ("Il fait beau aujourd'hui", "The weather is nice today", "Il fait beau aujourd'hui, allons nous promener."),
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    profile_id = sys.argv[1]

    cards = [
        Card(
            front=front,
            back=f"{meaning}<br><br><i>{example}</i>",
            tags=["demo", "voicebox"],
            tts_front=front,
            tts_back=example,
            tts_examples=[],
        )
        for front, meaning, example in CARDS
    ]

    n = write_apkg(
        DECK_NAME,
        cards,
        OUTPUT,
        tts_lang="fr",
        tts_cache_dir="tts_cache_demo_voicebox",
        engine="voicebox",
        voicebox_profile_id=profile_id,
    )
    print(f"\nWritten {n} cards to '{OUTPUT}'")
    print(f"Import into Anki: File -> Import -> {OUTPUT}")


if __name__ == "__main__":
    main()
