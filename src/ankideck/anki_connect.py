"""AnkiConnect API wrapper.

Requires Anki to be running with the AnkiConnect add-on installed.
Default URL: http://localhost:8765
"""

import requests

ANKI_CONNECT_URL = "http://localhost:8765"


def invoke(action: str, **params):
    """Send a request to AnkiConnect and return the result."""
    response = requests.post(
        ANKI_CONNECT_URL,
        json={"action": action, "version": 6, "params": params},
    ).json()
    if response.get("error"):
        raise Exception(f"AnkiConnect error: {response['error']}")
    return response.get("result")


def find_card_ids(query: str):
    return invoke("findCards", query=query)


def delete_cards(card_ids):
    if not card_ids:
        print("No cards to delete.")
        return
    print(f"Deleting {len(card_ids)} cards...")
    try:
        invoke("deleteCards", cards=card_ids)
        print("Deletion successful.")
    except Exception as e1:
        try:
            notes = invoke("cardsToNotes", cards=card_ids)
            invoke("deleteNotes", notes=notes)
            print("Deletion successful (deleted notes).")
        except Exception as e2:
            print(f"Failed to delete cards: {e1}")
            print(f"Failed to delete notes: {e2}")


def remove_duplicate_cards(deck_name: str, field_name: str = "Front") -> int:
    """Remove duplicate notes from a live Anki deck via AnkiConnect.

    Keeps the first occurrence of each unique field value and deletes the rest.
    Prompts for confirmation before deleting.

    Returns:
        Number of duplicate notes removed.
    """
    print(f"Finding duplicates in deck '{deck_name}' by '{field_name}' field...")

    card_ids = find_card_ids(f'deck:"{deck_name}"')
    if not card_ids:
        print(f"No cards found in deck '{deck_name}'.")
        return 0

    print(f"Found {len(card_ids)} total cards.")

    note_ids = invoke("cardsToNotes", cards=card_ids)
    notes_info = invoke("notesInfo", notes=note_ids)

    seen: dict = {}
    duplicate_note_ids = []

    for note_info in notes_info:
        note_id = note_info["noteId"]
        fields = note_info["fields"]
        if field_name in fields:
            value = fields[field_name]["value"].strip()
            if value:
                if value in seen:
                    duplicate_note_ids.append(note_id)
                    print(f"  Duplicate note {note_id} (original: {seen[value]}): {value[:50]}")
                else:
                    seen[value] = note_id

    if not duplicate_note_ids:
        print("No duplicate cards found.")
        return 0

    print(f"\nTotal: {len(card_ids)}, unique: {len(seen)}, duplicates: {len(duplicate_note_ids)}")
    print(f"Delete {len(duplicate_note_ids)} duplicate notes? [y/N] ", end="")
    if input().strip().lower() not in ("y", "yes"):
        print("Cancelled.")
        return 0

    try:
        invoke("deleteNotes", notes=duplicate_note_ids)
        print(f"Deleted {len(duplicate_note_ids)} duplicate notes.")
        return len(duplicate_note_ids)
    except Exception as e:
        print(f"Error deleting notes: {e}")
        return 0
