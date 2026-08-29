import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

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
# REQUEST SETTINGS
# ==========================
MAX_RETRIES = 5

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
}


# ==========================
# TELEGRAM
# ==========================
def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram BOT_TOKEN or CHAT_ID is missing.")
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
        print("Telegram alert sent.")

    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")


# ==========================
# LOAD SEEN CARDS
# ==========================
def load_seen():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"Failed to load seen cards: {e}")
        return []


# ==========================
# SAVE SEEN CARDS
# ==========================
def save_seen(cards):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                cards,
                f,
                indent=2,
                ensure_ascii=False
            )

    except Exception as e:
        print(f"Failed to save seen cards: {e}")


# ==========================
# GET NEARMINT PAGE
# ==========================
def get_page():

    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            print(
                f"Checking NearMint "
                f"(attempt {attempt}/{MAX_RETRIES})..."
            )

            response = session.get(
                URL,
                timeout=30
            )

            print(
                f"NearMint response: "
                f"{response.status_code}"
            )

            # ==========================
            # RATE LIMIT — HTTP 429
            # ==========================
            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        wait_time = 60
                else:
                    # Exponential backoff:
                    # 30 → 60 → 120 → 240 → 300
                    wait_time = min(
                        300,
                        30 * (2 ** (attempt - 1))
                    )

                # Add small random delay
                wait_time += random.randint(5, 15)

                print(
                    f"⚠️ NearMint rate limited us (429)."
                )

                print(
                    f"Waiting {wait_time} seconds "
                    f"before retry..."
                )

                time.sleep(wait_time)
                continue

            # ==========================
            # SERVER ERROR
            # ==========================
            if response.status_code >= 500:

                wait_time = min(
                    300,
                    30 * (2 ** (attempt - 1))
                )

                print(
                    f"⚠️ NearMint server error "
                    f"{response.status_code}."
                )

                print(
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)
                continue

            # ==========================
            # OTHER HTTP ERRORS
            # ==========================
            response.raise_for_status()

            return response.text

        except requests.RequestException as e:

            print(
                f"Request failed: {e}"
            )

            if attempt == MAX_RETRIES:
                print(
                    "❌ NearMint request failed "
                    "after all retries."
                )
                return None

            wait_time = min(
                300,
                30 * (2 ** (attempt - 1))
            )

            wait_time += random.randint(5, 15)

            print(
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    return None


# ==========================
# GET CARDS
# ==========================
def get_cards():

    html = get_page()

    # IMPORTANT:
    # If NearMint is still rate limiting us after all retries,
    # return None instead of an empty list.
    #
    # This prevents the script from thinking that all old cards
    # disappeared and overwriting seen_cards.json.
    if html is None:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    cards = []

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a["href"]

        if "/listing/" in href:

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
        f"Found {len(unique)} listings on NearMint."
    )

    return unique[:30]


# ==========================
# CHECK NEW CARDS
# ==========================
def check_new_cards():

    current = get_cards()

    # ==========================
    # REQUEST FAILED
    # ==========================
    if current is None:

        print(
            "⚠️ Could not retrieve NearMint."
        )

        print(
            "Keeping existing seen_cards.json."
        )

        return

    old = load_seen()

    old_urls = {
        x["url"]
        for x in old
    }

    new_cards = []

    for card in current:

        if card["url"] not in old_urls:
            new_cards.append(card)

    # ==========================
    # SEND NEW CARD ALERTS
    # ==========================
    if old:

        for card in reversed(new_cards):

            msg = (
                "🆕 New Pokémon Card Listed\n\n"
                f"{card['title']}\n\n"
                f"{card['url']}"
            )

            send_telegram(msg)

            # Small delay between Telegram messages
            time.sleep(1)

    else:

        print(
            "First run — establishing card database."
        )

    # ==========================
    # SAVE CURRENT CARDS
    # ==========================
    save_seen(current)

    print(
        f"Checked | Found {len(new_cards)} new"
    )


# ==========================
# MAIN
# ==========================
if __name__ == "__main__":

    print("=" * 50)
    print("NearMint Pokémon Tracker")
    print("=" * 50)

    check_new_cards()

    print("=" * 50)
    print("Finished")
    print("=" * 50)
