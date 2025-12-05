import os
import re
import csv
import string
import requests
import nltk
from nltk.corpus import stopwords
from PyPDF2 import PdfReader

OUTPUT_CSV = "words_from_pdfs.csv"
BASE_FOLDER = "Past_Events"
COUNTRY_CACHE = {}

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

LETTER_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:'[A-Za-zÀ-ÖØ-öø-ÿ]+)?", re.UNICODE)

def normalize_token(token: str) -> str:
    return token.strip(string.punctuation + " \t\n\r").lower()

def contains_digit(token: str) -> bool:
    return any(ch.isdigit() for ch in token)

def extract_words_from_text(text):
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

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        print(f"Erro ao ler PDF {file_path}: {e}")
        return ""

def save_words_to_csv(year, city, country, words, output_csv):
    file_exists = os.path.isfile(output_csv)
    location = f"{city} - {country}"

    with open(output_csv, "a", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            writer.writerow(["Ano", "Evento", "Palavra"])

        for word in words:
            writer.writerow([year, location, word])

    print(f"{len(words)} palavras salvas de → {city} ({year})")

def sort_csv_by_year(output_csv):
    if not os.path.isfile(output_csv):
        print("CSV ainda não existe.")
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

    print("CSV ordenado por ano!")


def get_country(city):
    city_key = city.lower().strip()

    if city_key in COUNTRY_CACHE:
        return COUNTRY_CACHE[city_key]

    country = "Unknown"

    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=10,
        )

        if r.status_code != 200:
            COUNTRY_CACHE[city_key] = "Unknown"
            return "Unknown"

        data = r.json()

        results = data.get("results", [])
        if not results:
            COUNTRY_CACHE[city_key] = "Unknown"
            return "Unknown"

        country = results[0].get("country", "Unknown")

    except:
        country = "Unknown"

    COUNTRY_CACHE[city_key] = country
    return country

def main():
    if not os.path.isdir(BASE_FOLDER):
        print(f"Pasta '{BASE_FOLDER}' não existe.")
        return

    for year in os.listdir(BASE_FOLDER):
        year_path = os.path.join(BASE_FOLDER, year)
        if not os.path.isdir(year_path):
            continue
        if not year.isdigit():
            continue

        for city in os.listdir(year_path):
            country = get_country(city)
            city_path = os.path.join(year_path, city)
            if not os.path.isdir(city_path):
                continue

            print(f"\nProcessando: {year}/{city}/{country}")

            for file in os.listdir(city_path):
                if not file.lower().endswith(".pdf"):
                    continue

                file_path = os.path.join(city_path, file)
                print(f"   → Lendo PDF: {file}")

                text = extract_text_from_pdf(file_path)
                if not text.strip():
                    print("   (PDF vazio ou ilegível)")
                    continue

                words = extract_words_from_text(text)
                save_words_to_csv(year, city, country, words, OUTPUT_CSV)

    sort_csv_by_year(OUTPUT_CSV)
    print("\nFinalizado!")

if __name__ == "__main__":
    main()
