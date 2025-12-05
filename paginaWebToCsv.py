import requests
from bs4 import BeautifulSoup
import re
import csv
import os
import nltk
from nltk.corpus import stopwords

BASE_URL = "https://devopsdays.org"
EVENTS_URL = f"{BASE_URL}/events/"
OUTPUT_CSV = "words_from_webpage.csv"

nltk.download("stopwords")

STOPWORDS = set(stopwords.words("portuguese")) | set(stopwords.words("english"))

STOPWORDS.update(
    [
        "devopsdays",
        "event",
        "events",
        "program",
        "www",
        "http",
        "https",

        "a",
        "the",
        "program",
        "contact",
        "events",
        "presentations",
        "blog",
        "welcome",
        "reactions",
        "speakers",
        "participants",
        "intro",
        "video",
        "slideshare",
        "for",
        "with",
        "in",
        "and",
        "not",
        "only",
        "ppt",
        "pdf",
        "detail",
        "non",
        "do",
        "is",
        "all",
        "so",
        "how",
        "t",
        "of",
        "to",
        "non",
        "not",
        "an",
    ]
)


def fetch_page_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Erro ao acessar {url}: {e}")
        return ""


def extract_words_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    text = soup.get_text()

    words = re.findall(r"\b\w+\b", text.lower())

    filtered = [w for w in words if w not in STOPWORDS and len(w) > 1]

    return filtered


def save_words_to_csv(year, event_name, words, output_csv):
    file_exists = os.path.isfile(output_csv)

    with open(output_csv, "a", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            writer.writerow(["Ano", "Evento", "Palavra"])

        for word in words:
            writer.writerow([year, event_name, word])

    print(f"✔ {len(words)} palavras úteis salvas para '{event_name}' ({year})")


def get_all_events():
    print("Buscando eventos em devopsdays.org...")

    html = fetch_page_content(EVENTS_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    events = []
    current_year = None

    for tag in soup.find_all(["h4", "a"]):

        if tag.name == "h4" and "events-page-months" in tag.get("class", []):
            current_year = tag.get_text(strip=True)

        if tag.name == "a" and "events-page-event" in tag.get("class", []):
            event_name = tag.get_text(strip=True)
            event_link = tag.get("href")

            if current_year and event_link:
                full_link = BASE_URL + event_link
                events.append(
                    {"year": current_year, "event": event_name, "url": full_link}
                )

    print(f"Encontrados {len(events)} eventos.")
    return events


def main():
    events = get_all_events()
    if not events:
        print("Nenhum evento encontrado.")
        return

    for ev in events:
        program_url = ev["url"].rstrip("/") + "/program"

        print(f"\nAcessando programa do evento: {ev['event']} ({ev['year']})")
        print(f"URL: {program_url}")

        html_content = fetch_page_content(program_url)

        if not html_content:
            print("Programa não disponível, pulando...")
            continue

        words = extract_words_from_html(html_content)
        save_words_to_csv(ev["year"], ev["event"], words, OUTPUT_CSV)

    print("\nFinalizado! Todas as palavras úteis foram coletadas.")


if __name__ == "__main__":
    main()
