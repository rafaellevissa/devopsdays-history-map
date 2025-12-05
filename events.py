import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://devopsdays.org/events/"
OUTPUT_CSV = "events_check.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
}

def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.text
        return None
    except:
        return None


def extract_all_events():
    html = fetch(BASE_URL)
    if not html:
        print("Erro ao acessar página de eventos.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    events = []

    year_headers = soup.find_all("h4", class_="events-page-months")

    for year_h in year_headers:
        year = year_h.text.strip()

        next_tag = year_h.find_next_sibling()
        while next_tag and next_tag.name != "h4":
            if next_tag.name == "a" and "events-page-event" in next_tag.get("class", []):
                event_name = next_tag.text.strip()
                event_path = next_tag.get("href")
                event_url = "https://devopsdays.org" + event_path

                events.append({
                    "year": year,
                    "name": event_name,
                    "url": event_url
                })
            next_tag = next_tag.next_sibling

    return events


def check_program(event_url):
    if "legacy" in event_url:
        return True, event_url

    program_url = event_url.rstrip("/") + "/program"
    html = fetch(program_url)
    if html:
        return True, program_url
    return False, program_url


def detect_video(html):
    if not html:
        return False
    return any(
        x in html.lower()
        for x in ["youtube.com", "youtu.be", "vimeo.com"]
    )


def detect_slides(html):
    if not html:
        return False
    return any(
        x in html.lower()
        for x in [
            ".pdf",
            "slideshare.net",
            "speakerdeck.com",
            "docs.google.com/presentation"
        ]
    )


def process_event(event):
    year = event["year"]
    name = event["name"]
    url = event["url"]

    print(f"Verificando {year} - {name} ...")

    html_main = fetch(url)
    haveSite = html_main is not None

    haveProgram, program_url = check_program(url)

    html_program = fetch(program_url) if haveProgram else None

    haveVideo = detect_video(html_main) or detect_video(html_program)

    haveSlide = detect_slides(html_main) or detect_slides(html_program)

    return [
        year,
        name,
        program_url,
        haveSite,
        haveProgram,
        haveVideo,
        haveSlide,
        True
    ]


def main():
    print("📡 Buscando lista completa de eventos...")
    events = extract_all_events()
    print(f"Total encontrado: {len(events)} eventos\n")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Ano", "Evento", "Link",
            "haveSite", "haveProgram",
            "haveVideo", "haveSlide", "considered"
        ])

        for ev in events:
            row = process_event(ev)
            writer.writerow(row)
            time.sleep(0.3)

    print(f"\nArquivo gerado: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
