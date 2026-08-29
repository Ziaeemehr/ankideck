You are doing a bulk translation job for an Anki flashcard deck.

Input file: `scripts/gram_diag_b1/manifest_filtered.json` — a JSON array of 756
objects, each shaped like:

```json
{
  "note_id": 1783603218540,
  "lesson": "01 Le present de l'indicatif",
  "front_word": "un goujat [sound:tts_...mp3]",
  "example_fr": "C'est un vrai goujat, cet homme !"
}
```

Task: for every object, translate the `example_fr` sentence into natural,
idiomatic, everyday-spoken Persian (Farsi), and add a new field `example_fa`
holding that translation. Do not modify any other field. Do not drop or
reorder entries — the output array must have exactly the same 756 entries in
the same order, each with `example_fa` added.

Style guide for the Persian translations (match the existing "Communication
essentielle A2" Anki deck in this repo, e.g. look at a few notes there for
tone if useful):
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

Process the 756 entries yourself (you may write a throwaway Python script to
manage batching/IO, but the actual translation judgment must be yours, not a
call to an external translation API/service — there is no API key configured
for that here). Work in batches (e.g. 40-60 at a time) to keep each step
manageable, writing progress incrementally so the job is resumable if
interrupted.

Output file: write the final result to
`scripts/gram_diag_b1/manifest_translated.json` (same directory), as a JSON
array with the same 756 objects, each now including `example_fa`.

When done, print a short summary: how many entries were translated, and 5
random example_fr -> example_fa pairs so I can spot-check quality.
