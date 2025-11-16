from elevenlabs.client import ElevenLabs
import requests
import re
import os

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
def remove_farsi_text(text):
    """
    Remove Farsi/Persian characters from text.
    Persian Unicode range: \u0600-\u06FF (Arabic and Persian)
    Also includes: \u0750-\u077F, \uFB50-\uFDFF, \uFE70-\uFEFF
    """
    # Remove Persian/Arabic characters
    cleaned = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+', '', text)
    # Clean up extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def make_tts_elevenlabs(text, api_key_address, filename, cache_dir):
    """
    Generate audio from text using ElevenLabs API.
    Store audio as MP3 file.
    Returns the path to the saved audio file or None if failed.
    """
    # Remove Farsi text before sending to ElevenLabs
    text = remove_farsi_text(text)
    
    # If text is empty after removing Farsi, return None
    if not text.strip():
        return None
    
    try:
        # Load API key
        with open(api_key_address, "r", encoding="utf-8") as f:
            elevenlabs_api_key = f.read().strip()

        # Initialize ElevenLabs client
        elevenlabs = ElevenLabs(api_key=elevenlabs_api_key)

        # Generate audio
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Save audio to MP3 file
        audio_bytes = b"".join(audio)
        os.makedirs(cache_dir, exist_ok=True)
        audio_path = os.path.join(cache_dir, filename)
        
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        
        return audio_path
    except Exception as e:
        print(f"⚠️ خطا در ساخت صدا با ElevenLabs: {e}")
        return None
    
def strip_html(text):
    return re.sub(r"<.*?>", "", text).strip()


def make_tts_gtts(sentences, audio_path, lang="fr", pause=False, pause_duration=700, tts_slow=False, sleep_time=0.4):
    """
    Generate TTS audio using Google Text-to-Speech (gTTS).
    
    Args:
        sentences: List of text sentences to convert
        audio_path: Full path where the audio file will be saved
        lang: Language code (default: "fr" for French)
        pause: Whether to add pauses between sentences
        pause_duration: Duration of pause in milliseconds
        tts_slow: Whether to use slow speech
        sleep_time: Time to sleep after generating audio
        
    Returns:
        str: Path to the saved audio file, or None if failed
    """
    from gtts import gTTS
    from pydub import AudioSegment
    import time
    
    try:
        combined = AudioSegment.silent(duration=0)
        cache_dir = os.path.dirname(audio_path)
        
        for sent in sentences:
            if not sent.strip():
                continue
            tts = gTTS(sent, lang=lang, slow=tts_slow)
            temp_path = os.path.join(cache_dir, "temp.mp3")
            tts.save(temp_path)
            clip = AudioSegment.from_mp3(temp_path)
            combined += clip
            if pause:
                combined += AudioSegment.silent(duration=pause_duration)
        
        combined.export(audio_path, format="mp3")
        time.sleep(sleep_time)
        return audio_path
    except Exception as e:
        print(f"⚠️ خطا در ساخت صدا: {e}")
        return None


def make_tts(sentences, filename, cache_dir, engine="gtts", pause=False, 
             pause_duration=700, lang="fr", tts_slow=False, sleep_time=0.4,
             elevenlabs_api_key_file=None):
    """
    Generate TTS audio using the specified engine (gTTS or ElevenLabs).
    
    Args:
        sentences: List of text sentences to convert
        filename: Name of the output audio file
        cache_dir: Directory to store the audio file
        engine: "gtts" or "elevenlabs"
        pause: Whether to add pauses between sentences (gTTS only)
        pause_duration: Duration of pause in milliseconds (gTTS only)
        lang: Language code for gTTS (default: "fr")
        tts_slow: Whether to use slow speech for gTTS
        sleep_time: Time to sleep after generating audio (gTTS only)
        elevenlabs_api_key_file: Path to ElevenLabs API key file (required for elevenlabs engine)
        
    Returns:
        str: Path to the saved audio file, or None if failed
    """
    audio_path = os.path.join(cache_dir, filename)
    
    # Return existing file if it exists
    if os.path.exists(audio_path):
        return audio_path
    
    if engine == "elevenlabs":
        # Use ElevenLabs for TTS
        if not elevenlabs_api_key_file:
            print("⚠️ ElevenLabs API key file not provided")
            return None
            
        # Combine all sentences into one text
        combined_text = " ".join(sent.strip() for sent in sentences if sent.strip())
        if not combined_text:
            return None
        
        return make_tts_elevenlabs(
            text=combined_text,
            api_key_address=elevenlabs_api_key_file,
            filename=filename,
            cache_dir=cache_dir
        )
    
    else:  # Default to gtts
        return make_tts_gtts(
            sentences=sentences,
            audio_path=audio_path,
            lang=lang,
            pause=pause,
            pause_duration=pause_duration,
            tts_slow=tts_slow,
            sleep_time=sleep_time
        )
