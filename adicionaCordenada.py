import csv
from geopy.geocoders import Nominatim
import time

# Nome do arquivo CSV
INPUT_CSV = "words_from_webpage.csv"
OUTPUT_CSV = "words_from_webpage_updated.csv"

def get_coordinates(location, cache):
    """Converte um nome de local em coordenadas geográficas, utilizando cache."""
    if location in cache:
        # Retorna coordenadas do cache, se disponíveis
        return cache[location]
    
    geolocator = Nominatim(user_agent="geo_converter")
    try:
        location_data = geolocator.geocode(location)
        if location_data:
            coords = f"{location_data.latitude}, {location_data.longitude}"
        else:
            coords = "Não encontrado"
    except Exception as e:
        print(f"Erro ao obter coordenadas para {location}: {e}")
        coords = "Erro"

    # Armazena no cache
    cache[location] = coords
    return coords

def process_csv(input_csv, output_csv):
    """Processa o CSV de entrada e escreve no CSV de saída linha por linha."""
    cache = {}  # Dicionário para armazenar eventos já processados

    with open(input_csv, 'r', encoding='utf-8') as infile, \
         open(output_csv, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['Coordenadas']  # Adiciona a nova coluna
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)

        # Escreve o cabeçalho no arquivo de saída
        writer.writeheader()

        for row in reader:
            evento = row['Evento']
            if evento not in cache:
                print(f"Obtendo coordenadas para: {evento}")
            coordenadas = get_coordinates(evento, cache)
            row['Coordenadas'] = coordenadas
            writer.writerow(row)  # Escreve a linha no arquivo de saída
            time.sleep(1)  # Evita excesso de consultas ao serviço de geocodificação

    print(f"Processamento concluído! CSV salvo como: {output_csv}")

if __name__ == "__main__":
    process_csv(INPUT_CSV, OUTPUT_CSV)
