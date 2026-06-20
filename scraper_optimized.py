import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional, Callable
from lxml import etree
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import json
import os
from functools import lru_cache
import hashlib

class EmpregosMaringaScraperOptimized:
    """
    Classe otimizada para extrair dados de vagas de emprego do site empregos.maringa.com
    com suporte a multithreading e cache
    """
    
    BASE_URL = "https://empregos.maringa.com/"
    CACHE_DIR = "cache"
    
    def __init__(self, max_workers: int = 10, use_cache: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.total_vagas = 0
        self.pagina_atual = 0
        self.lock = Lock()
        
        # Cria diretório de cache se não existir
        if use_cache and not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)
    
    def fix_encoding(self, text: str) -> str:
        """Corrige problemas de codificação"""
        if not text:
            return text
        
        try:
            if any(char in text for char in ['Ã¡', 'Ã£', 'Ã§', 'Ã©', 'Ã³', 'Ã­', 'Ãº']):
                text_bytes = text.encode('latin-1')
                text = text_bytes.decode('utf-8')
            return text
        except:
            try:
                text = unicodedata.normalize('NFKC', text)
                return text
            except:
                return text
    
    def get_cache_key(self, page_number: int) -> str:
        """Gera chave de cache para uma página"""
        return f"page_{page_number}.json"
    
    def get_cached_page(self, page_number: int) -> Optional[List[Dict]]:
        """Recupera página do cache"""
        if not self.use_cache:
            return None
        
        cache_file = os.path.join(self.CACHE_DIR, self.get_cache_key(page_number))
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def save_to_cache(self, page_number: int, data: List[Dict]):
        """Salva página no cache"""
        if not self.use_cache:
            return
        
        cache_file = os.path.join(self.CACHE_DIR, self.get_cache_key(page_number))
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    @lru_cache(maxsize=128)
    def extract_vaga_data(self, element_hash: str) -> Optional[Dict]:
        """
        Extrai dados de um elemento de vaga com cache
        """
        # Este método é chamado com o hash do elemento para cache
        return None
    
    def extract_vaga_data_from_element(self, vaga_element) -> Optional[Dict]:
        """
        Extrai os dados de um único elemento de vaga.
        """
        try:
            # Tenta encontrar a empresa
            empresa_elem = vaga_element.find('div', class_='d-none d-md-block')
            empresa = empresa_elem.get_text(strip=True) if empresa_elem else "N/A"
            empresa = self.fix_encoding(empresa)
            
            # Tenta encontrar a data
            data = "N/A"
            date_elements = vaga_element.find_all(string=re.compile(r'\d{2}/\d{2}/\d{4}'))
            if date_elements:
                data = date_elements[0].strip()
                data = self.fix_encoding(data)
            
            if data == "N/A":
                data_elem = vaga_element.find('div', class_='text-nowrap ml-4')
                if data_elem:
                    data = data_elem.get_text(strip=True)
                    data = self.fix_encoding(data)
                    if ' ' in data:
                        data = data.split(' ')[0]
            
            if data == "N/A":
                data_spans = vaga_element.find_all('span', string=re.compile(r'\d{2}/\d{2}/\d{4}'))
                if data_spans:
                    data = data_spans[0].get_text(strip=True)
                    data = self.fix_encoding(data)
            
            # Extrai URL
            url = self.extract_url_with_xpath(vaga_element)
            
            # Extrai localização
            cidade = "N/A"
            estado = "N/A"
            
            local_elements = vaga_element.find_all(['div', 'span', 'p'], string=re.compile(r'.*\s+-\s+[A-Z]{2}'))
            if local_elements:
                localizacao = local_elements[0].get_text(strip=True)
                localizacao = self.fix_encoding(localizacao)
                if ' - ' in localizacao:
                    partes = localizacao.split(' - ')
                    if len(partes) == 2:
                        cidade = self.fix_encoding(partes[0].strip())
                        estado = self.fix_encoding(partes[1].strip())
            
            if cidade == "N/A":
                text_elements = vaga_element.find_all(string=re.compile(r'[A-Za-zÀ-ú]+\s*-\s*[A-Z]{2}'))
                for elem in text_elements:
                    text = elem.strip()
                    text = self.fix_encoding(text)
                    if ' - ' in text:
                        partes = text.split(' - ')
                        if len(partes) == 2:
                            cidade = self.fix_encoding(partes[0].strip())
                            estado = self.fix_encoding(partes[1].strip())
                        break
            
            if empresa == "N/A" and not url:
                return None
            
            return {
                'empresa': empresa,
                'cidade': cidade,
                'estado': estado,
                'data_publicacao': data,
                'url': url
            }
            
        except Exception as e:
            print(f"Erro ao extrair dados da vaga: {e}")
            return None
    
    def extract_url_with_xpath(self, vaga_element) -> str:
        """Extrai a URL usando XPath otimizado"""
        try:
            # Tenta encontrar o link diretamente com BeautifulSoup (mais rápido)
            link = vaga_element.find('a', href=re.compile(r'vaga|job|emprego'))
            if link and link.get('href'):
                url = link.get('href')
                if url.startswith('/'):
                    url = self.BASE_URL.rstrip('/') + url
                elif not url.startswith('http'):
                    url = self.BASE_URL.rstrip('/') + '/' + url
                return url
            
            # Fallback para lxml (mais lento, mas mais preciso)
            html_content = str(vaga_element)
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_content, parser)
            
            # Tenta diferentes XPaths
            xpaths = [
                '//*[@id="id-546313"]/div/div[3]/a',
                '//a[contains(@href, "vaga") or contains(@href, "job")]',
                '//div[contains(@class, "d-flex")]//a',
                '//div[contains(@class, "text-nowrap")]//a'
            ]
            
            for xpath in xpaths:
                link_elements = tree.xpath(xpath)
                if link_elements:
                    url = link_elements[0].get('href')
                    if url:
                        if url.startswith('/'):
                            url = self.BASE_URL.rstrip('/') + url
                        elif not url.startswith('http'):
                            url = self.BASE_URL.rstrip('/') + '/' + url
                        return url
            
            return "N/A"
            
        except Exception as e:
            return "N/A"
    
    def fetch_page(self, page_number: int) -> Optional[BeautifulSoup]:
        """Busca uma página com tratamento de erros e retry"""
        try:
            # Verifica cache primeiro
            cached_data = self.get_cached_page(page_number)
            if cached_data:
                # Cria um objeto BeautifulSoup fictício para processamento
                # Na verdade, retornamos os dados já extraídos
                return cached_data
            
            url = f"{self.BASE_URL}?vagas-de-emprego=1&page={page_number}"
            
            # Tenta com diferentes URLs em caso de falha
            urls_to_try = [
                url,
                f"{self.BASE_URL}pagina/{page_number}/?vagas-de-emprego=1" if page_number > 1 else None,
                f"{self.BASE_URL}?vagas-de-emprego=1&pagina={page_number}"
            ]
            
            for try_url in urls_to_try:
                if not try_url:
                    continue
                    
                response = self.session.get(try_url, timeout=10)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.content
                    
            return None
            
        except Exception as e:
            print(f"Erro ao buscar página {page_number}: {e}")
            return None
    
    def parse_page(self, page_content, page_number: int) -> List[Dict]:
        """Parseia o conteúdo de uma página e extrai as vagas"""
        try:
            # Se já são dados processados (cache), retorna direto
            if isinstance(page_content, list):
                return page_content
            
            soup = BeautifulSoup(page_content, 'html.parser')
            vagas = []
            
            # Estratégias para encontrar elementos de vaga
            vaga_elements = []
            
            # Estratégia 1: Divs com ID começando com 'id-'
            vaga_elements = soup.find_all('div', id=re.compile(r'^id-\d+'))
            
            # Estratégia 2: Classes específicas
            if not vaga_elements:
                possible_divs = soup.find_all('div', class_=re.compile(r'.*vaga.*|.*job.*|.*offer.*'))
                for div in possible_divs:
                    text = div.get_text()
                    if ' - PR' in text or re.search(r'\d{2}/\d{2}/\d{4}', text):
                        vaga_elements.append(div)
            
            # Estratégia 3: Elementos genéricos
            if not vaga_elements:
                for element in soup.find_all(['div', 'article', 'section']):
                    text = element.get_text()
                    if ' - PR' in text and re.search(r'\d{2}/\d{2}/\d{4}', text):
                        if len(text) < 5000:
                            vaga_elements.append(element)
            
            # Extrai dados de cada elemento
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data_from_element(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            # Se não encontrou nada, tenta parse de texto
            if not vagas:
                vagas = self.parse_from_text_content(soup)
            
            # Salva no cache
            if vagas:
                self.save_to_cache(page_number, vagas)
            
            return vagas
            
        except Exception as e:
            print(f"Erro ao parsear página {page_number}: {e}")
            return []
    
    def parse_from_text_content(self, soup: BeautifulSoup) -> List[Dict]:
        """Método alternativo de parse baseado em texto"""
        vagas = []
        text = soup.get_text()
        
        pattern = r'([A-Za-zÀ-ú\s\.]+)\s*([A-Za-zÀ-ú]+\s*-\s*[A-Z]{2})\s*(\d{2}/\d{2}/\d{4})'
        matches = re.findall(pattern, text)
        
        for match in matches:
            empresa, localizacao, data = match
            
            empresa = self.fix_encoding(empresa.strip())
            localizacao = self.fix_encoding(localizacao.strip())
            data = self.fix_encoding(data.strip())
            
            cidade = "N/A"
            estado = "N/A"
            if ' - ' in localizacao:
                partes = localizacao.split(' - ')
                if len(partes) == 2:
                    cidade = self.fix_encoding(partes[0].strip())
                    estado = self.fix_encoding(partes[1].strip())
            
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
                    'empresa': empresa,
                    'cidade': cidade,
                    'estado': estado,
                    'data_publicacao': data,
                    'url': url
                })
        
        return vagas
    
    def scrape_page_parallel(self, page_number: int) -> tuple:
        """Scrape uma página em paralelo"""
        try:
            content = self.fetch_page(page_number)
            if content:
                vagas = self.parse_page(content, page_number)
                return page_number, vagas
            else:
                return page_number, []
        except Exception as e:
            print(f"Erro ao processar página {page_number}: {e}")
            return page_number, []
    
    def scrape_all_pages(self, max_pages: int = 91, progress_callback: Optional[Callable] = None) -> pd.DataFrame:
        """
        Scrape todas as páginas usando multithreading para máxima velocidade
        """
        all_vagas = []
        self.total_vagas = 0
        
        if progress_callback:
            progress_callback(0, max_pages, "Iniciando extração com {} workers...".format(self.max_workers))
        
        # Usa ThreadPoolExecutor para processamento paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submete todas as tarefas
            future_to_page = {
                executor.submit(self.scrape_page_parallel, page): page 
                for page in range(1, max_pages + 1)
            }
            
            # Processa resultados conforme são concluídos
            completed = 0
            for future in as_completed(future_to_page):
                page_number = future_to_page[future]
                try:
                    _, vagas = future.result()
                    all_vagas.extend(vagas)
                    self.total_vagas += len(vagas)
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(
                            completed, 
                            max_pages, 
                            f"Página {page_number}: {len(vagas)} vagas (Total: {self.total_vagas})"
                        )
                    
                    print(f"Página {page_number}: {len(vagas)} vagas extraídas")
                    
                except Exception as e:
                    print(f"Erro ao processar página {page_number}: {e}")
                    completed += 1
        
        if progress_callback:
            progress_callback(max_pages, max_pages, f"Extração concluída! Total: {self.total_vagas} vagas")
        
        if all_vagas:
            df = pd.DataFrame(all_vagas)
            df = df.drop_duplicates(subset=['empresa', 'cidade', 'data_publicacao'])
            return df
        else:
            return pd.DataFrame()
    
    def clear_cache(self):
        """Limpa o cache"""
        if os.path.exists(self.CACHE_DIR):
            for file in os.listdir(self.CACHE_DIR):
                os.remove(os.path.join(self.CACHE_DIR, file))
