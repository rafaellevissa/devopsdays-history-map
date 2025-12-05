import requests
from bs4 import BeautifulSoup
import re
import csv
import os
import nltk
from nltk.corpus import stopwords
import string

BASE_URL = "https://devopsdays.org"
EVENTS_URL = f"{BASE_URL}/events/"
OUTPUT_CSV = "words_from_webpage.csv"

nltk.download("stopwords", quiet=True)

STOPWORDS = set(w.lower() for w in stopwords.words("portuguese")) | set(
    w.lower() for w in stopwords.words("english")
)

STOPWORDS.update(
    [
        "devopsdays", "event", "events", "program", "www", "http", "https",
        "a", "the", "program", "contact", "events", "presentations", "blog",
        "welcome", "reactions", "speakers", "participants", "intro", "video",
        "slideshare", "for", "with", "in", "and", "not", "only", "ppt", "pdf",
        "detail", "non", "do", "is", "all", "so", "how", "t", "of", "to", "non",
        "not", "an",
    ]
)

STOPWORDS = set(s.strip().lower() for s in STOPWORDS if s)

def extract_year(text: str) -> str:
    match = re.search(r"\b(20\d{2}|19\d{2})\b", text)
    return match.group(1) if match else text.strip()


def extract_city(event_name: str) -> str:
    name = re.sub(r"\s+", " ", event_name).strip()

    if " - " in name:
        name = name.split(" - ")[0].strip()

    if ":" in name:
        parts = name.split(":")
        name = parts[-1].strip()

    name = re.sub(r"\(.*?\)", "", name).strip()

    name = re.sub(r"\d+", "", name).strip()

    name = re.sub(r"\s+", " ", name)

    return name


def contains_digit(token: str) -> bool:
    return any(ch.isdigit() for ch in token)


def normalize_token(token: str) -> str:
    return token.strip(string.punctuation + " \t\n\r").lower()

LETTER_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:'[A-Za-zÀ-ÖØ-öø-ÿ]+)?", re.UNICODE)

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

    text = soup.get_text(separator=" ")

    raw_words = LETTER_WORD_RE.findall(text)

    filtered = []
    for w in raw_words:
        w_norm = normalize_token(w)
        if not w_norm:
            continue
        if contains_digit(w_norm):
            continue
        if len(w_norm) <= 1:
            continue
        if w_norm in STOPWORDS:
            continue
        filtered.append(w_norm)

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
            current_year = extract_year(tag.get_text(strip=True))

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

def sort_csv_by_year(output_csv):
    if not os.path.isfile(output_csv):
        print("CSV ainda não existe, nada para ordenar.")
        return

    rows = []
    with open(output_csv, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        for row in reader:
            rows.append(row)

    rows.sort(key=lambda r: int(r[0]))

    with open(output_csv, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(rows)

    print("CSV ordenado por ano com sucesso!")

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
        city = extract_city(ev["event"])
        save_words_to_csv(ev["year"], city, words, OUTPUT_CSV)

    print("\nFinalizado! Todas as palavras úteis foram coletadas.")

    sort_csv_by_year(OUTPUT_CSV)


if __name__ == "__main__":
    main()
