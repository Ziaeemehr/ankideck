You are doing a bulk translation job for an Anki flashcard deck.

Input file: `scripts/vocab_prog_a2b1/manifest_filtered.json` — a JSON array of
1124 objects, each shaped like:

```json
{
  "note_id": 1783717322445,
  "lesson": "01 Presentations et usages",
  "front_word": "ça te va ? / ça vous va ? [sound:tts_...mp3]",
  "example_fr": "Une réunion mardi à 14h, ça te va ?"
}
```

Task: for every object, translate the `example_fr` sentence into natural,
idiomatic, everyday-spoken Persian (Farsi), and add a new field `example_fa`
holding that translation. Do not modify any other field. Do not drop or
reorder entries — the output array must have exactly the same 1124 entries in
the same order, each with `example_fa` added.

Style guide for the Persian translations (match the existing "Communication
essentielle A2" Anki deck in this repo, e.g. look at a few notes there for
tone if useful; the same job was already done for the "Grammaire en
dialogues B1" deck at scripts/gram_diag_b1/manifest_translated.json — you can
look at that file too as a style reference for the tone/quality expected):
- Natural spoken/colloquial Persian a native speaker would actually say, not
  a stiff literal word-for-word calque.
- Preserve register: familiar/informal French (tu, slang, exclamations) ->
  informal Persian; neutral French -> neutral Persian.
- Preserve sentence type: a question stays a question, an exclamation stays
  an exclamation, an imperative stays an imperative.
- Use standard Persian script with correct spacing (ZWNJ where appropriate),
  no diacritics needed.
- Keep it a single sentence/utterance matching the French, not an expanded
  paraphrase or an added explanation.

Process the 1124 entries yourself (you may write a throwaway Python script to
manage batching/IO, but the actual translation judgment must be yours, not a
call to an external translation API/service — there is no API key configured
for that here). Work in batches (e.g. 40-60 at a time) to keep each step
manageable, writing progress incrementally so the job is resumable if
interrupted.

Output file: write the final result to
`scripts/vocab_prog_a2b1/manifest_translated.json` (same directory), as a
JSON array with the same 1124 objects, each now including `example_fa`.

When done, print a short summary: how many entries were translated, and 5
random example_fr -> example_fa pairs so I can spot-check quality.
