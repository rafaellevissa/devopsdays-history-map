import requests
from bs4 import BeautifulSoup
import csv
import os

BASE_URL = "https://devopsdays.org"
LEGACY_BASE = "https://legacy.devopsdays.org"
EVENTS_URL = f"{BASE_URL}/events/"
OUTPUT_CSV = "talks_program.csv"


def fetch(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except:
        return None


def split_author_title(text):
    """
    Divide strings no formato:
    - "Autor - Título"
    - "Autor, Título"
    - "Autor – Título"
    """
    if " - " in text:
        return text.split(" - ", 1)
    if ", " in text:
        return text.split(", ", 1)
    if " – " in text:
        return text.split(" – ", 1)
    return ("", text)


def parse_legacy_program(url, year, event_name):
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    talks = []

    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if not text:
            continue
        if "://" not in text and ("," in text or " - " in text):
            author, title = split_author_title(text)
            talks.append({
                "year": year,
                "event": event_name,
                "author": author.strip(),
                "title": title.strip(),
                "link": url
            })

    return talks


def parse_modern_program(url, year, event_name):
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    talks = []

    for div in soup.find_all("div", class_="program-talk"):
        a = div.find("a")
        if not a:
            continue

        text = a.get_text(strip=True)
        link = a.get("href")

        author, title = split_author_title(text)

        talks.append({
            "year": year,
            "event": event_name,
            "author": author.strip(),
            "title": title.strip(),
            "link": BASE_URL + link if link.startswith("/") else link
        })

    return talks


def get_all_events():
    html = fetch(EVENTS_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    events = []
    year = None

    for tag in soup.find_all(["h4", "a"]):

        if tag.name == "h4" and "events-page-months" in tag.get("class", []):
            year = tag.text.strip()

        if tag.name == "a" and "events-page-event" in tag.get("class", []):
            event_name = tag.text.strip()
            link = tag.get("href")
            full_url = BASE_URL + link
            events.append({
                "year": year,
                "event": event_name,
                "url": full_url
            })

    return events


def main():
    events = get_all_events()
    if not events:
        print("Nenhum evento encontrado.")
        return

    file_exists = os.path.isfile(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            writer.writerow(["ano", "local", "autor", "titulo", "link"])

        for ev in events:
            year = ev["year"]
            event_name = ev["event"]
            event_url = ev["url"]

            program_url = event_url.rstrip("/") + "/program"

            print(f"\nEvento: {event_name} ({year})")
            print(f"Tentando moderno: {program_url}")

            html = fetch(program_url)

            if not html:
                legacy_url = event_url.replace(BASE_URL, LEGACY_BASE) + "/program"
                print(f"⚠️ Usando legacy: {legacy_url}")
                talks = parse_legacy_program(legacy_url, year, event_name)
            else:
                talks = parse_modern_program(program_url, year, event_name)

            for t in talks:
                writer.writerow([
                    t["year"],
                    t["event"],
                    t["author"],
                    t["title"],
                    t["link"]
                ])

            print(f"✔ {len(talks)} talks extraídas.")

    print("\nConcluído! Arquivo gerado:", OUTPUT_CSV)


if __name__ == "__main__":
    main()
