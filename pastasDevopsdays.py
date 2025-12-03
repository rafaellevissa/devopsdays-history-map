import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Base URL for events
BASE_URL = "https://devopsdays.org/events/"

def fetch_and_parse_page(url):
    """Fetch the webpage and parse it with BeautifulSoup."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as e:
        print(f"Failed to fetch the page: {url} - {e}")
        return None

def download_file(file_url, save_path):
    """Download a file from a given URL."""
    try:
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"Downloaded: {save_path}")
    except requests.RequestException as e:
        print(f"Failed to download {file_url}: {e}")

def find_and_download_presentations(event_url, event_dir):
    """Find and download presentation files from the event page."""
    soup = fetch_and_parse_page(event_url)
    if not soup:
        return

    # Find all links on the event page
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        # Check if the link is a downloadable file (e.g., PDF, PPT, etc.)
        if href.lower().endswith(('.pdf', '.ppt', '.pptx')):
            file_url = urljoin(event_url, href)
            file_name = os.path.basename(href)
            save_path = os.path.join(event_dir, file_name)
            download_file(file_url, save_path)

def create_folder_structure_and_download_presentations():
    """Create folder structure and download presentations for each event."""
    soup = fetch_and_parse_page(BASE_URL)
    if not soup:
        print("Failed to fetch the main events page.")
        return

    # Find the "Past" section
    past_section = soup.find('h2', string='Past')
    if not past_section:
        print("The 'Past' section was not found.")
        return

    # Locate the parent container of the "Past" section
    parent_container = past_section.find_next('div', class_='row')

    # Create a base directory for past events
    base_dir = 'Past_Events'
    os.makedirs(base_dir, exist_ok=True)

    # Iterate through year sections and events
    event_columns = parent_container.find_all('div', class_='col-md-6 col-lg-3 events-page-col')
    for column in event_columns:
        # Extract year
        year_header = column.find('h4', class_='events-page-months')
        if not year_header:
            continue
        year = year_header.text.strip()

        # Create a folder for the year
        year_dir = os.path.join(base_dir, year)
        os.makedirs(year_dir, exist_ok=True)

        # Extract events for the year
        event_links = column.find_all('a', class_='events-page-event')
        for link in event_links:
            event_name = link.text.strip().replace(':', '-').replace('/', '-')
            event_url = urljoin(BASE_URL, link['href'])

            # Create a folder for the event
            event_dir = os.path.join(year_dir, event_name)
            os.makedirs(event_dir, exist_ok=True)
            print(f"Created folder: {event_dir}")

            # Download presentations for the event
            print(f"Checking presentations for event: {event_name}")
            find_and_download_presentations(event_url, event_dir)

    print("Folder structure and downloads completed!")

if __name__ == "__main__":
    create_folder_structure_and_download_presentations()
