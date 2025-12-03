import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Base URL of DevOpsDays events
BASE_URL = "https://devopsdays.org/events/"

def download_pdf(pdf_url, save_path):
    """Download a PDF file."""
    response = requests.get(pdf_url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as pdf_file:
            for chunk in response.iter_content(chunk_size=1024):
                pdf_file.write(chunk)
        print(f"Downloaded: {save_path}")
    else:
        print(f"Failed to download: {pdf_url}")

def create_folder_structure(base_dir, year, event_name):
    """Create folder structure for year and event."""
    year_folder = os.path.join(base_dir, year)
    event_folder = os.path.join(year_folder, event_name)
    os.makedirs(event_folder, exist_ok=True)
    return event_folder

def find_pdfs_and_links(url, visited, base_dir):
    """Recursively find all PDFs and links on a webpage."""
    if url in visited:
        return
    visited.add(url)

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Extract event year and name from the URL
    event_parts = url.strip("/").split("/")[-3:]
    year, event_name = None, None
    if len(event_parts) >= 2 and event_parts[-2].isdigit():
        year = event_parts[-2]
        event_name = event_parts[-1]
        event_folder = create_folder_structure(base_dir, year, event_name)
    else:
        event_folder = base_dir

    # Download all PDF links on the page
    for link in soup.find_all("a", href=True):
        href = link['href']
        full_url = urljoin(url, href)

        if href.lower().endswith(".pdf"):
            filename = href.split("/")[-1]
            save_path = os.path.join(event_folder, filename)
            download_pdf(full_url, save_path)
        elif BASE_URL in full_url and full_url not in visited:
            # Recursively visit links within the base URL
            find_pdfs_and_links(full_url, visited, base_dir)

def main():
    """Main script to start crawling."""
    base_dir = "devopsdays_presentations"
    os.makedirs(base_dir, exist_ok=True)
    visited_links = set()
    find_pdfs_and_links(BASE_URL, visited_links, base_dir)

if __name__ == "__main__":
    main()
