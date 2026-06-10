name: NearMint Card Tracker

on:
  schedule:
    - cron: '*/10 * * * *' # Back to every 10 minutes!
  workflow_dispatch:

jobs:
  run-tracker:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout Repository Code
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.9'

      - name: Install Scraping Tools
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4

      - name: Run Scraper (With Hidden Secrets Passed In)
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
        run: python nearmint_alert.py

      - name: Commit & Save Memory File
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add seen_cards.json
          git commit -m "Update tracker memory [skip ci]" || exit 0
          git push
