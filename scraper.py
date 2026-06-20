import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional, Callable
from lxml import etree
import unicodedata
import json

class EmpregosMaringaScraper:
    """
    Classe para extrair dados de vagas de emprego do site empregos.maringa.com
    """
    
    BASE_URL = "https://empregos.maringa.com/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.total_vagas = 0
        self.pagina_atual = 0
    
    def fix_encoding(self, text: str) -> str:
        """
        Corrige problemas de codificação como 'MaringÃ¡' para 'Maringá'
        """
        if not text:
            return text
        
        try:
            # Tenta corrigir codificação comum
            if 'Ã¡' in text or 'Ã£' in text or 'Ã§' in text or 'Ã©' in text or 'Ã³' in text:
                text_bytes = text.encode('latin-1')
                text = text_bytes.decode('utf-8')
            return text
        except:
            try:
                text = unicodedata.normalize('NFKC', text)
                return text
            except:
                return text
    
    def extract_vaga_data(self, vaga_element) -> Optional[Dict]:
        """
        Extrai os dados de um único elemento de vaga.
        """
        try:
            # Procura por título da vaga
            title_elem = vaga_element.find('h2')
            if not title_elem:
                title_elem = vaga_element.find('h3')
            if not title_elem:
                title_elem = vaga_element.find('h4')
                
            titulo = title_elem.get_text(strip=True) if title_elem else "N/A"
            titulo = self.fix_encoding(titulo)
            
            # Procura por empresa
            empresa = "N/A"
            empresa_elem = vaga_element.find('div', class_=re.compile(r'empresa|company|nome-empresa'))
            if empresa_elem:
                empresa = empresa_elem.get_text(strip=True)
                empresa = self.fix_encoding(empresa)
            
            # Se não encontrou, procura por spans com texto que parece ser empresa
            if empresa == "N/A":
                for span in vaga_element.find_all('span'):
                    text = span.get_text(strip=True)
                    if len(text) > 2 and not re.search(r'\d{2}/\d{2}/\d{4}', text) and not re.search(r'[A-Z]{2}', text):
                        if len(text) < 100 and ' - ' not in text:
                            empresa = self.fix_encoding(text)
                            break
            
            # Procura por localização
            cidade = "N/A"
            estado = "N/A"
            
            # Procura por padrão de localização: Cidade - UF
            local_elements = vaga_element.find_all(string=re.compile(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}'))
            if local_elements:
                localizacao = self.fix_encoding(local_elements[0].strip())
                if ' - ' in localizacao or '–' in localizacao:
                    separador = ' - ' if ' - ' in localizacao else '–'
                    partes = localizacao.split(separador)
                    if len(partes) == 2:
                        cidade = self.fix_encoding(partes[0].strip())
                        estado = self.fix_encoding(partes[1].strip())
            
            # Procura por data
            data = "N/A"
            date_elements = vaga_element.find_all(string=re.compile(r'\d{2}/\d{2}/\d{4}'))
            if date_elements:
                data = self.fix_encoding(date_elements[0].strip())
            
            # Se ainda não encontrou data, procura em elementos com classe específica
            if data == "N/A":
                data_elem = vaga_element.find('div', class_=re.compile(r'data|date|publicacao'))
                if data_elem:
                    data = self.fix_encoding(data_elem.get_text(strip=True))
                    match = re.search(r'\d{2}/\d{2}/\d{4}', data)
                    if match:
                        data = match.group()
            
            # Extrai URL
            url = self.extract_url(vaga_element)
            
            # Se não encontrou dados mínimos, retorna None
            if empresa == "N/A" and titulo == "N/A" and url == "N/A":
                return None
            
            return {
                'titulo': titulo,
                'empresa': empresa,
                'cidade': cidade,
                'estado': estado,
                'data_publicacao': data,
                'url': url
            }
            
        except Exception as e:
            print(f"Erro ao extrair dados da vaga: {e}")
            return None
    
    def extract_url(self, vaga_element) -> str:
        """
        Extrai a URL da vaga.
        """
        try:
            # Procura por links comuns
            for link in vaga_element.find_all('a'):
                href = link.get('href', '')
                if href and ('vaga' in href or 'job' in href or 'emprego' in href or 'detalhes' in href):
                    url = href
                    if url.startswith('/'):
                        url = self.BASE_URL.rstrip('/') + url
                    elif not url.startswith('http'):
                        url = self.BASE_URL.rstrip('/') + '/' + url
                    return url
            
            # Procura por qualquer link dentro do elemento
            link = vaga_element.find('a')
            if link and link.get('href'):
                url = link.get('href')
                if url.startswith('/'):
                    url = self.BASE_URL.rstrip('/') + url
                elif not url.startswith('http'):
                    url = self.BASE_URL.rstrip('/') + '/' + url
                return url
            
            return "N/A"
            
        except Exception as e:
            print(f"Erro ao extrair URL: {e}")
            return "N/A"
    
    def scrape_page(self, page_number: int) -> List[Dict]:
        """
        Scrape uma página específica de resultados.
        """
        try:
            url = f"{self.BASE_URL}vagas-de-emprego/page/{page_number}/"
            print(f"Acessando: {url}")
            
            response = self.session.get(url)
            
            if response.status_code != 200:
                # Tenta formato alternativo
                url = f"{self.BASE_URL}?page={page_number}&vagas-de-emprego=1"
                print(f"Tentando URL alternativa: {url}")
                response = self.session.get(url)
                
                if response.status_code != 200:
                    print(f"Erro ao acessar página {page_number}: Status {response.status_code}")
                    return []
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            
            vagas = []
            
            # Estratégia 1: Procura por cards de vaga
            vaga_elements = soup.find_all('div', class_=re.compile(r'card|item|post|listing|job'))
            
            # Estratégia 2: Procura por divs com padrão de ID
            if not vaga_elements:
                vaga_elements = soup.find_all('div', id=re.compile(r'^id-\d+'))
            
            # Estratégia 3: Procura por divs que contêm informações de vaga
            if not vaga_elements:
                for div in soup.find_all('div'):
                    text = div.get_text()
                    if re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) and re.search(r'\d{2}/\d{2}/\d{4}', text):
                        if len(text) < 2000:  # Evita elementos muito grandes
                            vaga_elements.append(div)
            
            # Estratégia 4: Procura por artigos
            if not vaga_elements:
                vaga_elements = soup.find_all('article')
            
            print(f"Encontrados {len(vaga_elements)} elementos de vaga na página {page_number}")
            
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            # Se ainda não encontrou nada, tenta extrair do texto da página
            if not vagas:
                print(f"Nenhuma vaga encontrada com os métodos padrão. Tentando extração de texto...")
                vagas = self.parse_from_text_content(soup)
            
            return vagas
            
        except Exception as e:
            print(f"Erro ao scraper página {page_number}: {e}")
            return []
    
    def parse_from_text_content(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Método alternativo para extrair dados baseado no padrão de texto observado.
        """
        vagas = []
        
        # Busca por padrões de localização e data
        text = soup.get_text()
        
        # Padrão para encontrar blocos de vagas
        pattern = r'([A-Za-zÀ-ú\s\.]+?)\s*([A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2})\s*(\d{2}/\d{2}/\d{4})'
        matches = re.findall(pattern, text)
        
        for match in matches:
            empresa, localizacao, data = match
            
            empresa = self.fix_encoding(empresa.strip())
            localizacao = self.fix_encoding(localizacao.strip())
            data = self.fix_encoding(data.strip())
            
            cidade = "N/A"
            estado = "N/A"
            if ' - ' in localizacao or '–' in localizacao:
                separador = ' - ' if ' - ' in localizacao else '–'
                partes = localizacao.split(separador)
                if len(partes) == 2:
                    cidade = self.fix_encoding(partes[0].strip())
                    estado = self.fix_encoding(partes[1].strip())
            
            # Tenta encontrar URL
            url = "N/A"
            link = soup.find('a', href=re.compile(r'vaga|job|emprego'))
            if link and link.get('href'):
                url = link.get('href')
                if url.startswith('/'):
                    url = self.BASE_URL.rstrip('/') + url
                elif not url.startswith('http'):
                    url = self.BASE_URL.rstrip('/') + '/' + url
            
            if empresa or url:
                vagas.append({
                    'titulo': 'N/A',
                    'empresa': empresa,
                    'cidade': cidade,
                    'estado': estado,
                    'data_publicacao': data,
                    'url': url
                })
        
        return vagas
    
    def scrape_all_pages(self, max_pages: int = 100, progress_callback: Optional[Callable] = None) -> pd.DataFrame:
        """
        Scrape todas as páginas especificadas e retorna um DataFrame.
        """
        all_vagas = []
        self.total_vagas = 0
        self.pagina_atual = 0
        
        for page in range(1, max_pages + 1):
            self.pagina_atual = page
            
            if progress_callback:
                progress_callback(page, max_pages, f"Extraindo página {page}/{max_pages}")
            
            print(f"Scraping página {page}...")
            
            vagas = self.scrape_page(page)
            
            if not vagas:
                print(f"Nenhuma vaga encontrada na página {page}. Tentando próxima página...")
                # Se não encontrou nada na página atual, continua para a próxima
                # pois pode ser que algumas páginas estejam vazias
                if page > 3:  # Se já passou de 3 páginas sem resultados, para
                    break
                continue
            
            all_vagas.extend(vagas)
            self.total_vagas += len(vagas)
            print(f"Extraídas {len(vagas)} vagas da página {page}. Total acumulado: {self.total_vagas}")
            
            if progress_callback:
                progress_callback(page, max_pages, f"Extraídas {len(vagas)} vagas da página {page}")
            
            # Delay para não sobrecarregar o servidor
            time.sleep(1)
        
        if all_vagas:
            df = pd.DataFrame(all_vagas)
            # Remove duplicatas
            df = df.drop_duplicates(subset=['empresa', 'cidade', 'data_publicacao'])
            
            # Salva em CSV para debug
            df.to_csv('vagas_extraidas.csv', index=False, encoding='utf-8')
            print(f"Total de vagas extraídas: {len(df)}")
            
            if progress_callback:
                progress_callback(max_pages, max_pages, f"Extração concluída! Total: {len(df)} vagas")
            return df
        else:
            if progress_callback:
                progress_callback(max_pages, max_pages, "Nenhuma vaga encontrada.")
            return pd.DataFrame()

# Função para executar o scraping com callback de progresso
def run_scraper():
    scraper = EmpregosMaringaScraper()
    
    def progress_callback(current, total, message):
        print(f"Progresso: {current}/{total} - {message}")
    
    # Scrape das primeiras 100 páginas
    df = scraper.scrape_all_pages(max_pages=100, progress_callback=progress_callback)
    
    print(f"\nResumo final:")
    print(f"Total de vagas extraídas: {len(df)}")
    print(f"Primeiras 5 vagas:")
    print(df.head())
    
    return df

if __name__ == "__main__":
    df = run_scraper()
