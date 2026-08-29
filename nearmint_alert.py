import requests
from bs4 import BeautifulSoup
import json
import os

# ==========================
# TELEGRAM SETTINGS
# ==========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ==========================
# NEARMINT URL
# ==========================
URL = "https://nearmint.in/browse?universe=pokemon&format=single&sort=newest"
DATA_FILE = "seen_cards.json"

# ==========================
# REQUEST HEADERS
# ==========================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://nearmint.in/",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# ==========================
# TELEGRAM
# ==========================
def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ BOT_TOKEN or CHAT_ID is missing.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=10,
        )

        response.raise_for_status()

        print("✅ Telegram alert sent.")

    except requests.RequestException as e:
        print(f"⚠️ Failed to send Telegram alert: {e}")


# ==========================
# LOAD SEEN CARDS
# ==========================
def load_seen():

    if not os.path.exists(DATA_FILE):
        return []

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(f"⚠️ Failed to load {DATA_FILE}: {e}")
        return []


# ==========================
# SAVE SEEN CARDS
# ==========================
def save_seen(cards):

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                cards,
                f,
                indent=2,
                ensure_ascii=False
            )

        print("✅ seen_cards.json updated.")

    except Exception as e:

        print(f"⚠️ Failed to save {DATA_FILE}: {e}")


# ==========================
# GET CARDS FROM NEARMINT
# ==========================
def get_cards():

    print("Checking NearMint...")

    try:

        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            f"NearMint HTTP status: "
            f"{response.status_code}"
        )

        # ==========================
        # RATE LIMIT
        # ==========================
        if response.status_code == 429:

            print(
                "⚠️ NearMint returned 429 "
                "(Too Many Requests)."
            )

            print(
                "Skipping this run safely."
            )

            print(
                "seen_cards.json will NOT be changed."
            )

            return None

        # ==========================
        # OTHER HTTP ERRORS
        # ==========================
        response.raise_for_status()

    except requests.RequestException as e:

        print(
            f"⚠️ NearMint request failed: {e}"
        )

        print(
            "Skipping this run safely."
        )

        print(
            "seen_cards.json will NOT be changed."
        )

        return None

    # ==========================
    # PARSE PAGE
    # ==========================
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    cards = []

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a["href"]

        # Only NearMint listing URLs
        if "/listing/" not in href:
            continue

        title = a.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        full_url = (
            href
            if href.startswith("http")
            else f"https://nearmint.in{href}"
        )

        cards.append({
            "title": title,
            "url": full_url
        })

    # ==========================
    # REMOVE DUPLICATES
    # ==========================
    unique = []
    seen_urls = set()

    for card in cards:

        if card["url"] not in seen_urls:

            unique.append(card)
            seen_urls.add(card["url"])

    print(
        f"Found {len(unique)} NearMint listings."
    )

    return unique[:30]


# ==========================
# CHECK FOR NEW CARDS
# ==========================
def check_new_cards():

    current = get_cards()

    # ==========================
    # REQUEST FAILED / 429
    # ==========================
    if current is None:

        print(
            "No database changes made."
        )

        return

    old = load_seen()

    old_urls = {
        card["url"]
        for card in old
    }

    new_cards = []

    for card in current:

        if card["url"] not in old_urls:

            new_cards.append(card)

    # ==========================
    # FIRST RUN
    # ==========================
    if not old:

        print(
            "First run detected."
        )

        print(
            f"Saving {len(current)} existing "
            f"cards without alerts."
        )

        save_seen(current)

        return

    # ==========================
    # NEW CARDS FOUND
    # ==========================
    if new_cards:

        print(
            f"🚨 {len(new_cards)} NEW CARD(S) FOUND!"
        )

        for card in reversed(new_cards):

            message = (
                "🆕 New Pokémon Card Listed\n\n"
                f"{card['title']}\n\n"
                f"{card['url']}"
            )

            send_telegram(message)

    else:

        print(
            "No new cards."
        )

    # ==========================
    # UPDATE DATABASE
    # ==========================
    save_seen(current)

    print(
        f"Checked | {len(new_cards)} new"
    )


# ==========================
# MAIN
# ==========================
if __name__ == "__main__":

    print("=" * 60)
    print("NearMint Pokémon Card Tracker")
    print("=" * 60)

    check_new_cards()

    print("=" * 60)
    print("Run finished.")
    print("=" * 60)
