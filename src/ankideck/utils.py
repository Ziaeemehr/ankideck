import requests

ANKI_CONNECT_URL = "http://localhost:8765"

def invoke(action, **params):
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": action,
        "version": 6,
        "params": params
    }).json()
    if response.get("error"):
        raise Exception(f"AnkiConnect error: {response['error']}")
    return response.get("result")


def find_card_ids(query):
    return invoke("findCards", query=query)


def delete_cards(card_ids):
    if not card_ids:
        print("❌ No cards to delete.")
        return
    print(f"🗑️ Deleting {len(card_ids)} cards...")
    try:
        # First try deleteCards action
        result = invoke("deleteCards", cards=card_ids)
        print("✅ Deletion successful.")
    except Exception as e1:
        try:
            # If that fails, try deleteNotes action (delete the notes containing the cards)
            notes = invoke("cardsToNotes", cards=card_ids)
            result = invoke("deleteNotes", notes=notes)
            print("✅ Deletion successful (deleted notes).")
        except Exception as e2:
            print(f"❌ Failed to delete cards: {e1}")
            print(f"❌ Failed to delete notes: {e2}")


def remove_duplicate_cards(deck_name, field_name="Front"):
    """
    Remove duplicate cards from a deck based on the content of a specified field.
    Keeps the first occurrence and deletes subsequent duplicates.
    
    Args:
        deck_name (str): Name of the Anki deck to process
        field_name (str): Name of the field to check for duplicates (default: "Front")
    
    Returns:
        int: Number of duplicate cards removed
    """
    print(f"🔍 Finding duplicate cards in deck '{deck_name}' based on '{field_name}' field...")
    
    # Get all cards from the specified deck
    query = f'deck:"{deck_name}"'
    card_ids = find_card_ids(query)
    
    if not card_ids:
        print(f"No cards found in deck '{deck_name}'.")
        return 0
    
    print(f"Found {len(card_ids)} total cards in deck.")
    
    # Get note IDs from card IDs
    note_ids = invoke("cardsToNotes", cards=card_ids)
    
    # Get note info for all notes
    notes_info = invoke("notesInfo", notes=note_ids)
    
    # Track field content and find duplicates
    field_content_to_note = {}  # Maps field content to first note ID
    duplicate_note_ids = []
    
    for note_info in notes_info:
        note_id = note_info['noteId']
        fields = note_info['fields']
        
        if field_name in fields:
            field_content = fields[field_name]['value'].strip()
            
            if field_content:  # Only process non-empty fields
                if field_content in field_content_to_note:
                    # This is a duplicate
                    duplicate_note_ids.append(note_id)
                    original_note = field_content_to_note[field_content]
                    print(f"  Duplicate found: Note {note_id} (duplicate of Note {original_note})")
                    print(f"    Content: {field_content[:50]}...")
                else:
                    # This is the first occurrence, keep it
                    field_content_to_note[field_content] = note_id
    
    if not duplicate_note_ids:
        print("✅ No duplicate cards found.")
        return 0
    
    print(f"\n📊 Summary:")
    print(f"  - Total cards: {len(card_ids)}")
    print(f"  - Unique {field_name} values: {len(field_content_to_note)}")
    print(f"  - Duplicate cards to remove: {len(duplicate_note_ids)}")
    
    # Ask for confirmation
    print(f"\n⚠️  Are you sure you want to delete {len(duplicate_note_ids)} duplicate cards? (y/N): ", end="")
    confirmation = input().strip().lower()
    if confirmation not in ('y', 'yes'):
        print("Deletion cancelled.")
        return 0
    
    # Delete the duplicate notes
    try:
        invoke("deleteNotes", notes=duplicate_note_ids)
        print(f"✅ Successfully deleted {len(duplicate_note_ids)} duplicate cards.")
        return len(duplicate_note_ids)
    except Exception as e:
        print(f"❌ Error deleting duplicate cards: {e}")
        return 0
