import requests
from bs4 import BeautifulSoup
import json
import os
import time

# ==========================
# TELEGRAM SETTINGS
# ==========================
BOT_TOKEN = "8827266849:AAHBwzWnpxWNeXDAJ8fouk-L5rezTKIcTDs" 
CHAT_ID = "1250061274"

# ==========================
# NEARMINT URL
# ==========================
URL = "https://nearmint.in/browse?universe=pokemon&format=single&sort=newest"
DATA_FILE = "seen_cards.json"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")


def load_seen():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_seen(cards):
    with open(DATA_FILE, "w") as f:
        json.dump(cards, f)


def get_cards():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    cards = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/product/" in href:
            title = a.get_text(" ", strip=True)

            if not title:
                continue
            
            full_url = (
                href if href.startswith("http")
                else f"https://nearmint.in{href}"
            )

            cards.append({
                "title": title,
                "url": full_url
            })

    unique = []
    seen_urls = set()

    for card in cards:
        if card["url"] not in seen_urls:
            unique.append(card)
            seen_urls.add(card["url"])

    return unique[:30]


def check_new_cards():
    current = get_cards()
    old = load_seen()

    old_urls = {x["url"] for x in old}
    new_cards = []

    for card in current:
        if card["url"] not in old_urls:
            new_cards.append(card)

    if old:
        for card in reversed(new_cards):
            msg = (
                f"🆕 *New Pokémon Card Listed*\n\n"
                f"{card['title']}\n\n"
                f"{card['url']}"
            )
            send_telegram(msg)

    save_seen(current)

    print(f"Checked | Found {len(new_cards)} new")


if __name__ == "__main__":
    # GitHub Action runs this once per trigger
    check_new_cards()