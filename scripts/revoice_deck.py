#!/usr/bin/env python3
"""Demo: re-voice a live Anki deck with a different TTS engine.

Replaces the audio behind the ``[sound:...]`` tags a deck already has, e.g.
swapping robotic gtts clips for natural Edge TTS ones.  The existing media
filenames are reused, so the notes themselves are never modified -- only the
files in Anki's media folder are overwritten.  That keeps the cards, their
scheduling and their HTML exactly as they are.

Anki must be running with AnkiConnect installed.

Runs in three resumable steps (``--step all`` does them in order):

    backup    download the current audio to ``--backup-dir``
    generate  synthesize replacements into ``--cache-dir``
    upload    push the generated files into Anki's media folder

Nothing is overwritten in Anki until ``upload``, so a failed or interrupted
generate costs nothing.  Re-running any step skips work already done, and the
backup directory holds the original clips if you want to roll back (re-upload
them with ``--cache-dir <backup-dir> --step upload``).

Choosing a voice:

    Edge's ``*MultilingualNeural`` voices (including fr-FR-Vivienne, the
    default in ``tts.py``) detect the language of each phrase and switch to
    foreign phonetics on words they read as foreign.  On short front-side
    prompts there is too little context for that to work and French words
    spelled like English ones -- "le budget", "la boxe", "un ticket" -- come
    out with an English accent.  For single words and short phrases prefer a
    monolingual voice, e.g. ``--voice fr-FR-DeniseNeural`` or
    ``fr-FR-HenriNeural``, which always applies French phonetics.

Which text gets spoken:

    Front  the field text, minus HTML and the sound tag
    Back   by default only the example sentence -- the first italic block of
           the field -- so translations and notes are not read aloud; pass
           ``--back-text full`` to speak the whole field instead

Run:
    python scripts/revoice_deck.py "My Deck"
    python scripts/revoice_deck.py "My Deck" --engine edge --voice fr-FR-HenriNeural
    python scripts/revoice_deck.py "My Deck" --fields front --step backup
    python scripts/revoice_deck.py "My Deck" --dry-run
"""

import argparse
import base64
import html
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck.anki_connect import invoke
from ankideck.tts import _remove_non_latin, make_tts

SOUND_TAG = re.compile(r"\[sound:([^\]]+)\]")
ITALIC_BLOCK = re.compile(r"<(div|i|em)[^>]*(?:font-style:\s*italic|)[^>]*>(.*?)</\1>", re.S)
ITALIC_STYLED = re.compile(r"<[^>]*font-style:\s*italic[^>]*>(.*?)</[a-z]+>", re.S)


def plain_text(field_html: str, strip_non_latin: bool = True) -> str:
    """Field HTML -> the bare text a TTS engine should read.

    Only the text *before* the first sound tag is kept.  Audio belongs to
    the text it follows, and cards sometimes park a translation or a note
    after the tag which should not be read aloud.  Fields whose tag sits at
    the very end -- the common case -- are unaffected.

    Non-Latin scripts (Persian, Arabic, ...) are dropped by default: these
    are foreign-language glosses, and a French voice reading them produces
    noise at best.
    """
    head = SOUND_TAG.split(field_html)[0]
    text = head if head.strip() else SOUND_TAG.sub("", field_html)
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if strip_non_latin:
        text = _remove_non_latin(text)
    return text.strip()


def example_text(field_html: str, strip_non_latin: bool = True) -> str:
    """The italic example sentence of a back field, or the whole field."""
    match = ITALIC_STYLED.search(field_html) or ITALIC_BLOCK.search(field_html)
    if match:
        found = plain_text(match.group(match.lastindex), strip_non_latin)
        if found:
            return found
    return plain_text(field_html, strip_non_latin)


def collect_clips(deck, fields, back_text, strip_non_latin=True):
    """Return [(media_filename, text)] for every sound tag in the deck.

    Notes whose field has no sound tag are skipped: this script replaces
    existing audio, it does not add audio to cards that never had any (use
    ``add_tts.py`` for that).
    """
    note_ids = invoke("findNotes", query=f'deck:"{deck}"')
    if not note_ids:
        print(f"No notes found in deck '{deck}'.")
        return []

    clips, skipped = [], 0
    for note in invoke("notesInfo", notes=note_ids):
        for field in fields:
            field_html = note["fields"].get(field, {}).get("value", "")
            filenames = SOUND_TAG.findall(field_html)
            if not filenames:
                skipped += 1
                continue
            if field.lower() == "back" and back_text == "example":
                text = example_text(field_html, strip_non_latin)
            else:
                text = plain_text(field_html, strip_non_latin)
            if not text:
                print(f"  note {note['noteId']}: '{field}' has audio but no text, skipping")
                continue
            # A field with several clips gets the same text for each; that is
            # rare and better than silently voicing only the first.
            for filename in filenames:
                clips.append((filename, text))

    seen = {}
    for filename, text in clips:
        if filename in seen and seen[filename] != text:
            raise SystemExit(
                f"Media file '{filename}' is used for two different texts; "
                "aborting rather than overwriting it with the wrong audio."
            )
        seen[filename] = text

    print(f"{len(clips)} clips in {len(note_ids)} notes"
          f"{f' ({skipped} fields had no audio)' if skipped else ''}")
    return clips


def backup(clips, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    saved = present = missing = 0
    for filename, _ in clips:
        path = os.path.join(backup_dir, filename)
        if os.path.exists(path):
            present += 1
            continue
        data = invoke("retrieveMediaFile", filename=filename)
        if data is False:
            print(f"  not in Anki's media folder: {filename}")
            missing += 1
            continue
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        saved += 1
        if saved % 200 == 0:
            print(f"  backed up {saved}...", flush=True)
    print(f"backup: {saved} saved, {present} already there, {missing} missing "
          f"-> {backup_dir}/")
    return missing


def generate(clips, cache_dir, engine, voice, lang, elevenlabs_key,
             voicebox_profile, jobs=1, retries=4):
    os.makedirs(cache_dir, exist_ok=True)
    todo = [c for c in clips if not os.path.exists(os.path.join(cache_dir, c[0]))]
    print(f"generate: {len(clips) - len(todo)} cached, {len(todo)} to synthesize "
          f"with {engine} ({jobs} at a time)", flush=True)

    # Each worker synthesizes into its own directory: make_tts writes a
    # temp file next to its output, and the name is fixed per engine, so
    # workers sharing a directory would clobber each other's temp file.
    def work_dir(slot):
        d = os.path.join(cache_dir, f".w{slot}")
        os.makedirs(d, exist_ok=True)
        return d

    done = {"n": 0}
    lock = threading.Lock()

    def synth(item):
        index, (filename, text) = item
        target = os.path.join(cache_dir, filename)
        staging = work_dir(index % jobs)
        ok = False
        # Network engines drop the occasional request, more so under
        # concurrency; without a retry those clips silently keep their old
        # audio and the deck ends up voiced by two engines.
        for attempt in range(retries):
            path = make_tts(
                sentences=[text],
                filename=filename,
                cache_dir=staging,
                engine=engine,
                lang=lang,
                voice=voice,
                elevenlabs_api_key_file=elevenlabs_key,
                voicebox_profile_id=voicebox_profile,
            )
            ok = bool(path) and os.path.exists(path) and os.path.getsize(path) > 0
            if ok:
                os.replace(path, target)
                break
            if path and os.path.exists(path):
                os.remove(path)  # so make_tts does not return the stub next time
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
        if not ok:
            print(f"  FAILED after {retries} tries {filename}: {text[:60]}", flush=True)
        with lock:
            done["n"] += 1
            if done["n"] % 50 == 0:
                print(f"  {done['n']}/{len(todo)}", flush=True)
        return ok

    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(synth, enumerate(todo)))
    else:
        results = [synth(item) for item in enumerate(todo)]

    for slot in range(jobs):
        d = os.path.join(cache_dir, f".w{slot}")
        if os.path.isdir(d):
            for leftover in os.listdir(d):
                os.remove(os.path.join(d, leftover))
            os.rmdir(d)

    failed = results.count(False)
    print(f"generate: {len(todo) - failed} written to {cache_dir}/, {failed} failed")
    return failed


def upload(clips, cache_dir):
    stored = 0
    for filename, _ in clips:
        path = os.path.join(cache_dir, filename)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print(f"  no audio to upload for {filename}, leaving it alone")
            continue
        with open(path, "rb") as f:
            invoke("storeMediaFile", filename=filename,
                   data=base64.b64encode(f.read()).decode())
        stored += 1
        if stored % 200 == 0:
            print(f"  uploaded {stored}...", flush=True)
    print(f"upload: {stored}/{len(clips)} media files replaced in Anki")
    return stored


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("deck", help="deck name, as shown in Anki")
    parser.add_argument("--engine", default="edge",
                        choices=["edge", "gtts", "elevenlabs", "voicebox"],
                        help="TTS engine for the new audio (default: edge)")
    parser.add_argument("--voice", default=None,
                        help="engine voice override, e.g. fr-FR-HenriNeural")
    parser.add_argument("--lang", default="fr", help="language code (default: fr)")
    parser.add_argument("--fields", default="Front,Back",
                        help="comma-separated fields to re-voice (default: Front,Back)")
    parser.add_argument("--back-text", default="example", choices=["example", "full"],
                        help="what to speak on the back: only the italic example "
                             "sentence, or the whole field (default: example)")
    parser.add_argument("--step", default="all",
                        choices=["all", "backup", "generate", "upload"],
                        help="which step to run (default: all)")
    parser.add_argument("--cache-dir", default=None,
                        help="where new audio is written (default: revoice_<engine>_<deck>)")
    parser.add_argument("--backup-dir", default=None,
                        help="where current audio is saved (default: revoice_backup_<deck>)")
    parser.add_argument("--elevenlabs-key", default=None,
                        help="path to a file holding an ElevenLabs API key")
    parser.add_argument("--voicebox-profile", default=None,
                        help="Voicebox profile id (required for --engine voicebox)")
    parser.add_argument("--jobs", type=int, default=8,
                        help="clips to synthesize at once (default: 8; use 1 to "
                             "serialize if an engine rate-limits you)")
    parser.add_argument("--retries", type=int, default=4,
                        help="attempts per clip before giving up (default: 4)")
    parser.add_argument("--keep-non-latin", action="store_true",
                        help="also speak non-Latin text (Persian, Arabic, ...); "
                             "by default those glosses are dropped")
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be voiced and exit")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    slug = re.sub(r"\W+", "_", args.deck).strip("_")
    cache_dir = args.cache_dir or f"revoice_{args.engine}_{slug}"
    backup_dir = args.backup_dir or f"revoice_backup_{slug}"
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    if args.engine == "voicebox" and not args.voicebox_profile:
        sys.exit("--engine voicebox needs --voicebox-profile "
                 "(list them: curl -s http://127.0.0.1:17493/profiles)")

    clips = collect_clips(args.deck, fields, args.back_text,
                          strip_non_latin=not args.keep_non_latin)
    if not clips:
        return 1

    if args.dry_run:
        for filename, text in clips[:10]:
            print(f"  {filename}: {text[:70]}")
        if len(clips) > 10:
            print(f"  ... and {len(clips) - 10} more")
        print(f"\nDry run: nothing generated or uploaded. "
              f"Would write to {cache_dir}/ and back up to {backup_dir}/.")
        return 0

    if args.step in ("all", "backup"):
        backup(clips, backup_dir)
    if args.step in ("all", "generate"):
        if generate(clips, cache_dir, args.engine, args.voice, args.lang,
                    args.elevenlabs_key, args.voicebox_profile,
                    jobs=max(1, args.jobs), retries=args.retries):
            print("Some clips failed; re-run to retry them "
                  "(finished ones are cached).")
    if args.step in ("all", "upload"):
        upload(clips, cache_dir)
        print(f"\nDone. Originals are in {backup_dir}/ if you need to roll back:\n"
              f"  python {Path(__file__).name} \"{args.deck}\" "
              f"--cache-dir {backup_dir} --step upload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
