import requests
import re
import argparse

ANKI_CONNECT_URL = "http://localhost:8765"

def invoke(action, **params):
    resp = requests.post(ANKI_CONNECT_URL, json={
        "action": action,
        "version": 6,
        "params": params
    }).json()
    if 'error' in resp and resp['error']:
        raise Exception(f"AnkiConnect error: {resp['error']}")
    return resp["result"]

def get_card_ids(deck_name):
    return invoke("findCards", query=f'deck:"{deck_name}"')

def get_notes_from_cards(card_ids):
    return invoke("cardsInfo", cards=card_ids)

def get_media_list():
    return invoke("getMediaFilesNames")

def get_media_data(media_name):
    return invoke("getMediaFile", filename=media_name)

def human_readable_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def main():
    parser = argparse.ArgumentParser(description="Get stats for an Anki deck.")
    parser.add_argument("deck_name", help="Name of the Anki deck")
    args = parser.parse_args()

    deck_name = args.deck_name
    print(f"📊 Stats for deck: {deck_name}")

    card_ids = get_card_ids(deck_name)
    notes_info = get_notes_from_cards(card_ids)

    num_notes = len({note['note'] for note in notes_info})
    num_cards = len(card_ids)
    num_audio = 0
    num_images = 0

    for card in notes_info:
        for field in card["fields"].values():
            content = field.get("value", "")
            if "[sound:" in content:
                num_audio += 1
            if re.search(r'<img[^>]+src="([^"]+)"', content):
                num_images += 1

    print(f"   🗂️  Cards: {num_cards}")
    print(f"   📝 Notes: {num_notes}")
    print(f"   🔊 Cards with audio: {num_audio}")
    print(f"   🖼️  Cards with images: {num_images}")

    # Optional: media info
    print("\n💽 Media usage...")
    media_files = get_media_list()
    total_media_files = len(media_files)
    total_size = 0

    for name in media_files:
        try:
            data = get_media_data(name)
            total_size += len(data.encode("utf-8"))
        except:
            continue

    print(f"📁 Total media files: {total_media_files}")
    print(f"📦 Estimated total media size: {human_readable_size(total_size)}")

if __name__ == "__main__":
    main()
