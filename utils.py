import re
from typing import Optional, Tuple
import pandas as pd
from datetime import datetime

def extract_city_state(location_text: str) -> Tuple[str, str]:
    """
    Extrai cidade e estado de um texto de localização.
    Exemplo: "Maringá - PR" -> ("Maringá", "PR")
    """
    city = "N/A"
    state = "N/A"
    
    if not location_text:
        return city, state
    
    # Tenta encontrar padrão "Cidade - UF"
    pattern = r'([A-Za-zÀ-ú\s]+)\s*[-–]\s*([A-Z]{2})'
    match = re.search(pattern, location_text)
    
    if match:
        city = match.group(1).strip()
        state = match.group(2).strip()
    
    return city, state

def clean_date(date_text: str) -> str:
    """
    Limpa e formata a data extraída.
    Exemplo: "19/06/2026 (Hoje às 15:16)" -> "19/06/2026"
    """
    if not date_text:
        return "N/A"
    
    # Tenta extrair apenas a data no formato dd/mm/aaaa
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_text)
    if date_match:
        return date_match.group(1)
    
    return date_text.strip()

def format_vaga_title(title: str) -> str:
    """
    Formata o título da vaga, removendo espaços extras e caracteres especiais.
    """
    if not title:
        return "N/A"
    
    # Remove espaços extras e caracteres especiais
    cleaned = re.sub(r'\s+', ' ', title).strip()
    return cleaned

def extract_company_from_text(text: str) -> str:
    """
    Tenta extrair o nome da empresa de um texto.
    """
    if not text:
        return "N/A"
    
    # Remove padrões comuns
    text = re.sub(r'Vaga|Emprego|Oportunidade|Job', '', text, flags=re.I)
    text = re.sub(r'\([^)]*\)', '', text)  # Remove parênteses
    text = re.sub(r'[^\w\sÀ-ú]', ' ', text)  # Remove caracteres especiais
    
    # Pega a primeira palavra que parece ser um nome
    words = text.split()
    for word in words:
        if len(word) > 2 and not re.search(r'\d', word):
            return word.strip()
    
    return "N/A"

def validate_vaga_data(vaga: dict) -> bool:
    """
    Valida se um dicionário de vaga contém dados mínimos.
    """
    if not vaga:
        return False
    
    # Verifica se tem pelo menos empresa ou título
    has_company = vaga.get('empresa', 'N/A') != 'N/A'
    has_title = vaga.get('titulo', 'N/A') != 'N/A'
    has_url = vaga.get('url', 'N/A') != 'N/A'
    
    return has_company or has_title or has_url

def deduplicate_vagas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove vagas duplicadas baseado em empresa, cidade e data.
    """
    if df.empty:
        return df
    
    # Cria uma chave composta
    df['_key'] = df['empresa'].str.lower() + '|' + df['cidade'].str.lower() + '|' + df['data_publicacao']
    
    # Remove duplicatas mantendo a primeira ocorrência
    df = df.drop_duplicates(subset=['_key'], keep='first')
    df = df.drop('_key', axis=1)
    
    return df

def parse_date_safely(date_str: str) -> Optional[datetime]:
    """
    Tenta parsear uma data de forma segura.
    """
    if not date_str or date_str == 'N/A':
        return None
    
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None
