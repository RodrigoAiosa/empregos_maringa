import re
from typing import Optional, Tuple

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
    pattern = r'([A-Za-zÀ-ú\s]+)\s*-\s*([A-Z]{2})'
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
