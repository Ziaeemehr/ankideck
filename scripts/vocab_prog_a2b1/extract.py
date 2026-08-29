import json, re, sys
sys.path.insert(0, "/Users/tng/git/AnkiDecks_develop/src")
from ankideck.anki_connect import invoke

SOURCE_DECK = "Vocabulaire progressif du français A2-B1"
ITALIC_STYLED = re.compile(r'<div style="margin-top:8px;font-style:italic;color:#444">(.*?)</div>', re.S)

def strip_html(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()

decks = [d for d in invoke("deckNames") if d == SOURCE_DECK or d.startswith(SOURCE_DECK + "::")]
subdecks = [d for d in decks if d != SOURCE_DECK]

out = []
for sub in subdecks:
    lesson = sub.split("::", 1)[1]
    note_ids = invoke("findNotes", query=f'deck:"{sub}"')
    for note in invoke("notesInfo", notes=note_ids):
        back = note["fields"].get("Back", {}).get("value", "")
        front_word = strip_html(note["fields"].get("Front", {}).get("value", ""))
        m = ITALIC_STYLED.search(back)
        example_fr = strip_html(m.group(1)) if m else ""
        out.append({
            "note_id": note["noteId"],
            "lesson": lesson,
            "front_word": front_word,
            "example_fr": example_fr,
        })

with open("/Users/tng/git/AnkiDecks_develop/scripts/vocab_prog_a2b1/manifest.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(out)} notes from {len(subdecks)} subdecks")
no_example = [o for o in out if not o["example_fr"]]
print(f"No example sentence: {len(no_example)}")
thin = sorted((o for o in out if o["example_fr"]), key=lambda o: len(o["example_fr"]))[:30]
print("\nShortest example sentences:")
for o in thin:
    print(f"  [{len(o['example_fr']):3d}] {o['lesson']:45s} | word={o['front_word']!r:30s} | {o['example_fr']!r}")
