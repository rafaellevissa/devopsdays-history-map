import requests
from bs4 import BeautifulSoup
import csv
import time
import re

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


def get_country(city):
    try:
        r = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10
        )

        if r.status_code != 200:
            return "Unknown"

        data = r.json()
        if "results" not in data or not data["results"]:
            return "Unknown"

        return data["results"][0].get("country", "Unknown")
    except:
        return "Unknown"


def normalize_city(name):
    if not name:
        return name

    name = re.sub(r"\(.*?\)", "", name)

    name = name.strip()

    if "," in name:
        name = name.split(",")[0].strip()

    return name


def iter_events():
    html = fetch(BASE_URL)
    if not html:
        print("Erro ao acessar página de eventos.")
        return

    soup = BeautifulSoup(html, "html.parser")

    year_headers = soup.find_all("h4", class_="events-page-months")

    for year_h in year_headers:
        year = year_h.text.strip()

        next_tag = year_h.find_next_sibling()

        while next_tag and next_tag.name != "h4":
            if next_tag.name == "a" and "events-page-event" in next_tag.get("class", []):
                raw_name = next_tag.text.strip()
                city = normalize_city(raw_name)
                event_path = next_tag.get("href")
                event_url = "https://devopsdays.org" + event_path

                yield {
                    "year": year,
                    "city_raw": raw_name,
                    "city": city,
                    "url": event_url,
                }

            next_tag = next_tag.next_sibling


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
    return any(x in html.lower() for x in ["youtube.com", "youtu.be", "vimeo.com"])


def detect_slides(html):
    if not html:
        return False
    return any(x in html.lower() for x in [
        ".pdf", "slideshare.net", "speakerdeck.com", "docs.google.com/presentation"
    ])


def process_event(event):
    year = event["year"]
    city = event["city"]
    url = event["url"]

    print(f"Verificando {year} - {city} ...")

    country = get_country(city)

    display_name = f"{city} - {country}"

    html_main = fetch(url)
    haveSite = html_main is not None

    haveProgram, program_url = check_program(url)

    html_program = fetch(program_url) if haveProgram else None

    haveVideo = detect_video(html_main) or detect_video(html_program)
    haveSlide = detect_slides(html_main) or detect_slides(html_program)

    return [
        year,
        display_name,
        program_url,
        haveSite,
        haveProgram,
        haveVideo,
        haveSlide,
        True
    ]


def main():
    print("Buscando eventos...\n")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "Ano", "Evento", "Link",
            "haveSite", "haveProgram", "haveVideo",
            "haveSlide", "considered"
        ])

        for ev in iter_events():
            row = process_event(ev)
            writer.writerow(row)
            csvfile.flush()
            time.sleep(0.3)

    print(f"\nArquivo gerado: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
