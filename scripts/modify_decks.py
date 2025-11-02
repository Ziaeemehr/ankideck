from ankideck.utils import find_card_ids, delete_cards, invoke, remove_duplicate_cards
import requests
import argparse
import sys
import re



def remove_cards_without_audio():
    parser = argparse.ArgumentParser(description='Modify Anki decks by deleting cards without audio in Front field.')
    parser.add_argument('deck_name', help='Name of the Anki deck to process')
    
    args = parser.parse_args()
    deck = args.deck_name.strip()
    if not deck:
        print("Error: Deck name is required.", file=sys.stderr)
        sys.exit(1)

    query = f'(deck:"{deck}") AND (-(*:*[sound:*))'
    print(f"🔍 Searching cards in deck '{deck}' with query:\n{query}")

    card_ids = find_card_ids(query)
    print(f"Found {len(card_ids)} cards without audio in any field.")
    if card_ids:
        print(f"Card IDs: {card_ids[:5]}...")  # Show first 5

    if not card_ids:
        print("No cards to delete.")
        return

    print(f"Are you sure you want to delete {len(card_ids)} cards? (y/N): ", end="")
    confirmation = input().strip().lower()
    if confirmation not in ('y', 'yes'):
        print("Deletion cancelled.")
        return

    delete_cards(card_ids)


def modify_cards_contents():
    parser = argparse.ArgumentParser(description='Modify Anki decks by removing 🇮🇷 emoji from card contents.')
    parser.add_argument('deck_name', help='Name of the Anki deck to process')
    
    args = parser.parse_args()
    deck = args.deck_name.strip()
    if not deck:
        print("Error: Deck name is required.", file=sys.stderr)
        sys.exit(1)

    # Search for cards containing the Iranian flag emoji
    query = f'(deck:"{deck}") AND (*🇮🇷*)'
    print(f"🔍 Searching cards in deck '{deck}' containing 🇮🇷 emoji...")
    print(f"Query: {query}")

    card_ids = find_card_ids(query)
    print(f"Found {len(card_ids)} cards containing 🇮🇷 emoji.")
    
    if not card_ids:
        print("No cards found with 🇮🇷 emoji.")
        return

    # Get note IDs from card IDs using invoke function from utils
    note_ids = invoke("cardsToNotes", cards=card_ids)
    print(f"Found {len(note_ids)} unique notes to process.")

    # Get note info for each note using invoke function from utils
    notes_info = invoke("notesInfo", notes=note_ids)
    
    # Track changes
    modified_count = 0
    
    for note_info in notes_info:
        note_id = note_info['noteId']
        fields = note_info['fields']
        
        # Check if any field contains the emoji and prepare updates
        updated_fields = {}
        has_changes = False
        
        for field_name, field_content in fields.items():
            if '🇮🇷' in field_content['value']:
                # Remove the emoji
                new_content = field_content['value'].replace('🇮🇷', '')
                updated_fields[field_name] = new_content
                has_changes = True
                print(f"  Note {note_id}, Field '{field_name}': Removing 🇮🇷 emoji")
        
        # Update the note if there are changes using invoke function from utils
        if has_changes:
            note = {
                "id": note_id,
                "fields": updated_fields
            }
            invoke("updateNoteFields", note=note)
            modified_count += 1
    
    print(f"✅ Successfully modified {modified_count} notes, removing 🇮🇷 emoji from card contents.")


def remove_sound_from_field():
    parser = argparse.ArgumentParser(description='Modify Anki decks by removing audio from specific fields.')
    parser.add_argument('deck_name', help='Name of the Anki deck to process')
    parser.add_argument('field_name', help='Name of the field to remove audio from')

    args = parser.parse_args()
    deck = args.deck_name.strip()
    field_name = args.field_name.strip()
    
    if not deck or not field_name:
        print("Error: Both deck name and field name are required.", file=sys.stderr)
        sys.exit(1)

    # Search for cards containing sound tags in the specified field
    query = f'(deck:"{deck}") AND ({field_name}:*[sound:*)'
    print(f"🔍 Searching cards in deck '{deck}' with sound tags in '{field_name}' field...")
    print(f"Query: {query}")

    card_ids = find_card_ids(query)
    print(f"Found {len(card_ids)} cards with sound tags in '{field_name}' field.")
    
    if not card_ids:
        print(f"No cards found with sound tags in '{field_name}' field.")
        return

    # Get note IDs from card IDs using invoke function from utils
    note_ids = invoke("cardsToNotes", cards=card_ids)
    print(f"Found {len(note_ids)} unique notes to process.")

    # Get note info for each note using invoke function from utils
    notes_info = invoke("notesInfo", notes=note_ids)
    
    # Track changes
    modified_count = 0
    
    # Regex pattern to match [sound:filename.ext] tags
    sound_pattern = r'\[sound:[^\]]+\]'
    
    for note_info in notes_info:
        note_id = note_info['noteId']
        fields = note_info['fields']
        
        # Check if the specified field contains sound tags and prepare updates
        updated_fields = {}
        has_changes = False
        
        # Only process the specified field
        if field_name in fields and fields[field_name]['value']:
            field_content = fields[field_name]['value']
            if re.search(sound_pattern, field_content):
                # Remove all sound tags
                new_content = re.sub(sound_pattern, '', field_content)
                # Clean up any extra whitespace left behind
                new_content = re.sub(r'\s+', ' ', new_content).strip()
                updated_fields[field_name] = new_content
                has_changes = True
                print(f"  Note {note_id}, {field_name} field: Removing sound tags")
        
        # Update the note if there are changes using invoke function from utils
        if has_changes:
            note = {
                "id": note_id,
                "fields": updated_fields
            }
            invoke("updateNoteFields", note=note)
            modified_count += 1
    
    print(f"✅ Successfully modified {modified_count} notes, removing sound tags from '{field_name}' field.")


def remove_duplicates():
    parser = argparse.ArgumentParser(description='Remove duplicate cards from a deck based on field content.')
    parser.add_argument('deck_name', help='Name of the Anki deck to process')
    parser.add_argument('--field', default='Front', help='Name of the field to check for duplicates (default: Front)')

    args = parser.parse_args()
    deck = args.deck_name.strip()
    field_name = args.field.strip()
    
    if not deck:
        print("Error: Deck name is required.", file=sys.stderr)
        sys.exit(1)

    # Use the utility function to remove duplicates
    removed_count = remove_duplicate_cards(deck, field_name)
    
    if removed_count > 0:
        print(f"🎉 Operation completed! Removed {removed_count} duplicate cards from deck '{deck}'.")
    else:
        print("No duplicates were removed.")
    

if __name__ == "__main__":
    try:
        # remove_cards_without_audio()
        # modify_cards_contents()
        # remove_sound_from_field()
        # python3 modify_decks.py "Edito_A2_2022" "Back"
        remove_duplicates()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)