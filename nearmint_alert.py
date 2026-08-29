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
# NEARMINT
# ==========================
URL = "https://nearmint.in/browse?universe=pokemon&format=single&sort=newest"
DATA_FILE = "seen_cards.json"

# ==========================
# REQUEST SETTINGS
# ==========================
MAX_RETRIES = 2
TIMEOUT = 30

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
        print("ERROR: BOT_TOKEN or CHAT_ID is missing.")
        return

    telegram_url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    try:
        response = requests.post(
            telegram_url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=10,
        )

        response.raise_for_status()
        print("Telegram alert sent.")

    except requests.RequestException as e:
        print(f"Telegram error: {e}")


# ==========================
# LOAD SEEN
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
        print(f"Could not load {DATA_FILE}: {e}")
        return []


# ==========================
# SAVE SEEN
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

    except Exception as e:
        print(f"Could not save {DATA_FILE}: {e}")


# ==========================
# GET PAGE
# ==========================
def get_page():

    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"Checking NearMint "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            response = session.get(
                URL,
                timeout=TIMEOUT
            )

            print(
                f"NearMint HTTP status: "
                f"{response.status_code}"
            )

            # ==========================
            # RATE LIMITED
            # ==========================
            if response.status_code == 429:

                if attempt < MAX_RETRIES:

                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    if retry_after:
                        try:
                            wait_time = min(
                                int(retry_after),
                                60
                            )
                        except ValueError:
                            wait_time = 20
                    else:
                        wait_time = 20

                    wait_time += random.randint(3, 8)

                    print(
                        f"⚠️ NearMint rate limited "
                        f"the request (429)."
                    )

                    print(
                        f"Waiting {wait_time} seconds "
                        f"before one final retry..."
                    )

                    time.sleep(wait_time)

                    continue

                print(
                    "⚠️ NearMint still returned 429."
                )

                print(
                    "Skipping this run safely."
                )

                return None

            # ==========================
            # SERVER ERROR
            # ==========================
            if response.status_code >= 500:

                if attempt < MAX_RETRIES:

                    wait_time = 15 + random.randint(
                        3,
                        8
                    )

                    print(
                        f"NearMint server error "
                        f"{response.status_code}."
                    )

                    print(
                        f"Retrying in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                    continue

                print(
                    "NearMint server error persists."
                )

                return None

            # ==========================
            # SUCCESS
            # ==========================
            response.raise_for_status()

            return response.text

        except requests.RequestException as e:

            print(
                f"NearMint request error: {e}"
            )

            if attempt < MAX_RETRIES:

                wait_time = 10 + random.randint(
                    3,
                    8
                )

                print(
                    f"Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:

                print(
                    "Skipping this run."
                )

                return None

    return None


# ==========================
# GET CARDS
# ==========================
def get_cards():

    html = get_page()

    # NEVER replace seen_cards.json
    # if NearMint failed.
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
        f"Found {len(unique)} listings."
    )

    return unique[:30]


# ==========================
# CHECK NEW CARDS
# ==========================
def check_new_cards():

    current = get_cards()

    # ==========================
    # NEARMINT FAILED
    # ==========================
    if current is None:

        print(
            "⚠️ NearMint could not be checked."
        )

        print(
            "Existing seen_cards.json "
            "will NOT be changed."
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
            f"Saving {len(current)} listings "
            "without Telegram alerts."
        )

        save_seen(current)

        return

    # ==========================
    # NEW CARDS
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

            time.sleep(1)

    else:

        print(
            "No new cards."
        )

    # ==========================
    # SAVE CURRENT
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
