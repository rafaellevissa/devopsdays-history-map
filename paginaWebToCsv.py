import requests
from bs4 import BeautifulSoup
import re
import csv
import os

# URL da página
URL = "https://devopsdays.org/events/2021-tel-aviv/program"

# Arquivo de saída
OUTPUT_CSV = "words_from_webpage.csv"

# Informações fixas
YEAR = "2022"
EVENT = "Tel Aviv - Israel"

def fetch_page_content(url):
    """Faz o download do conteúdo HTML da página."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Erro ao acessar a página {url}: {e}")
        return ""

def extract_words_from_html(html_content):
    """Extrai palavras do conteúdo HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remover tags de script e estilo
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()

    # Obter apenas o texto visível
    text = soup.get_text()

    # Usar regex para capturar apenas palavras
    words = re.findall(r'\b\w+\b', text.lower())
    return words

def save_words_to_csv(words, output_csv):
    """Salva as palavras extraídas em um arquivo CSV."""
    # Verifica se o arquivo já existe
    file_exists = os.path.isfile(output_csv)

    with open(output_csv, 'a', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Escreve o cabeçalho apenas se o arquivo não existir
        if not file_exists:
            writer.writerow(['Ano', 'Evento', 'Palavra'])
        # Adiciona as palavras
        for word in words:
            writer.writerow([YEAR, EVENT, word])
    print(f"Palavras salvas no arquivo: {output_csv}")

def main():
    """Executa o script."""
    print("Acessando a página...")
    html_content = fetch_page_content(URL)

    if html_content:
        print("Extraindo palavras...")
        words = extract_words_from_html(html_content)

        print(f"Total de palavras extraídas: {len(words)}")
        save_words_to_csv(words, OUTPUT_CSV)
    else:
        print("Não foi possível acessar a página ou extrair conteúdo.")

if __name__ == "__main__":
    main()
