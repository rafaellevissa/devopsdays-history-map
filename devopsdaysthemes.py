import requests
from bs4 import BeautifulSoup
import csv
import os
import re
import time
from datetime import datetime
import json
from openai import OpenAI

BASE_URL = "https://devopsdays.org"
LEGACY_BASE = "https://legacy.devopsdays.org"
EVENTS_URL = f"{BASE_URL}/events/"
OUTPUT_CSV = "talks_program.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

COUNTRY_CACHE = {}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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



def build_link(base, link):
    if not link:
        return ""
    url = base + link if link.startswith("/") else link
    return url


def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.text
        return None
    except:
        return None


def split_author_title(text):
    if " - " in text:
        return text.split(" - ", 1)
    if ", " in text:
        return text.split(", ", 1)
    if " – " in text:
        return text.split(" – ", 1)
    return ("", text)

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


def parse_legacy_complex(html, year, event_name, program_url):
    soup = BeautifulSoup(html, "html.parser")
    talks = []

    for box in soup.find_all("div", class_="span-6"):
        titles = [s.get_text(strip=True) for s in box.find_all("strong")]
        if not titles:
            continue

        author = ""
        for a in box.find_all("a"):
            href = a.get("href", "")
            if "/speakers/" in href:
                author = a.get_text(strip=True)

        if not author:
            continue

        for title in titles:
            talks.append(
                {
                    "year": year,
                    "event": event_name,
                    "author": author,
                    "title": title,
                    "link": program_url,
                }
            )

    return talks


def parse_legacy_program(url, year, event_name):
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    if soup.find("div", class_="span-6"):
        return parse_legacy_complex(html, year, event_name, url)

    talks = []

    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if not text:
            continue
        if "://" not in text and ("," in text or " - " in text):
            author, title = split_author_title(text)
            talks.append(
                {
                    "year": year,
                    "event": event_name,
                    "author": author.strip(),
                    "title": title.strip(),
                    "link": url,
                }
            )

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

        talks.append(
            {
                "year": year,
                "event": event_name,
                "author": author.strip(),
                "title": title.strip(),
                "link": BASE_URL + link if link.startswith("/") else link,
            }
        )

    return talks


def iter_events():
    print("Buscando eventos em devopsdays.org...")

    html = fetch(EVENTS_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    year = None

    for tag in soup.find_all(["h4", "a"]):

        if tag.name == "h4" and "events-page-months" in tag.get("class", []):
            year = extract_year(tag.get_text(strip=True))

        if tag.name == "a" and "events-page-event" in tag.get("class", []):
            raw_event = tag.text.strip()
            city = extract_city(raw_event)
            country = get_country(city)
            event_name = f"{city} - {country}"

            link = tag.get("href")
            full_url = BASE_URL + link


            yield {"year": year, "event": event_name, "url": full_url}
            time.sleep(0.25)


def extract_container_html(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("div", class_="container")

        if container:
            return str(container)
        else:
            return html
    except:
        return html

def extract_talks_with_chatgpt(program_url: str, year: str, event_name: str):
    print("Extraindo via ChatGPT (fallback)...")

    html = fetch(program_url)
    if not html:
        return []

    cleaned_html = extract_container_html(html)
    cleaned_html = cleaned_html[:50000]

    prompt = f"""
Receba o HTML abaixo, procure qualquer programação de talks/palestras e retorne APENAS um JSON com:

- "author"
- "title"
- "link" (se existir; pode ser null)

NÃO ESCREVA NADA FORA DO JSON.

HTML PARA EXTRAÇÃO:

{cleaned_html}
"""
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Você extrai dados estruturados de HTML e devolve somente JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_completion_tokens=1500,
    )

    content = resp.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        return [
            {
                "year": year,
                "event": event_name,
                "author": t.get("author") or "",
                "title": t.get("title") or "",
                "link": build_link(BASE_URL, t.get("link")),
            }
            for t in data
        ]
    except Exception as e:
        print("Erro ao interpretar JSON recebido do ChatGPT:", e)
        print("Conteúdo bruto recebido:\n", content)
        return []


def main():
    file_exists = os.path.isfile(OUTPUT_CSV)

    with open(OUTPUT_CSV, "a", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            writer.writerow(["ano", "local", "autor", "titulo", "link"])

        for ev in iter_events():
            year = ev.get("year")
            event_name = ev.get("event")
            event_url = ev.get("url")

            try:
                year_int = int(year)
                if year_int > datetime.now().year:
                    print(f"\nPulando evento futuro: {event_name} ({year})")
                    continue
            except ValueError:
                print(f"\nAno inválido para o evento: {event_name} ({year})")
                continue

            print(f"\nEvento: {event_name} ({year})")

            program_url = event_url.rstrip("/") + "/program"
            print(f"Testando moderno: {program_url}")

            talks = parse_modern_program(program_url, year, event_name)

            if not talks:
                legacy_url = event_url.replace(BASE_URL, LEGACY_BASE) + "/program"
                print(f"Fallback: testando legacy → {legacy_url}")
                talks = parse_legacy_program(legacy_url, year, event_name)

            if not talks:
                legacy_url = event_url.replace(BASE_URL, LEGACY_BASE) + "/program"
                print("Nenhum talk encontrado — tentando com ChatGPT…")
                talks = extract_talks_with_chatgpt(legacy_url, year, event_name)

            if not talks:
                print("Nenhum talk encontrado para este evento.\n")
                continue

            for t in talks:
                writer.writerow([
                    t.get("year"),
                    t.get("event"),
                    t.get("author"),
                    t.get("title"),
                    t.get("link"),
                ])

            print(f"{len(talks)} talks extraídas.\n")


    print("\nConcluído! Arquivo gerado:", OUTPUT_CSV)

    sort_csv_by_year(OUTPUT_CSV)


if __name__ == "__main__":
    main()
