import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional, Callable
from lxml import etree
import unicodedata

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
        
        # Tenta corrigir codificação comum
        try:
            # Se o texto contém caracteres mal codificados, tenta recodificar
            if 'Ã¡' in text or 'Ã£' in text or 'Ã§' in text or 'Ã©' in text or 'Ã³' in text:
                # Tenta converter de Latin-1 para UTF-8
                text_bytes = text.encode('latin-1')
                text = text_bytes.decode('utf-8')
            return text
        except:
            # Se falhar, tenta outras abordagens
            try:
                # Tenta normalizar caracteres Unicode
                text = unicodedata.normalize('NFKC', text)
                return text
            except:
                return text
    
    def extract_vaga_data(self, vaga_element) -> Optional[Dict]:
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
            
            # Extrai localização (cidade e estado)
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
        """
        Extrai a URL usando o XPath específico.
        """
        try:
            html_content = str(vaga_element)
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_content, parser)
            
            # Tenta o XPath exato com ID específico
            link_elements = tree.xpath('//*[@id="id-546313"]/div/div[3]/a')
            
            if not link_elements:
                link_elements = tree.xpath('//a[contains(@href, "vaga") or contains(@href, "job") or contains(@href, "emprego")]')
            
            if not link_elements:
                link_elements = tree.xpath('//div[contains(@class, "d-flex")]//a | //div[contains(@class, "text-nowrap")]//a')
            
            if link_elements:
                url = link_elements[0].get('href')
                if url:
                    if url.startswith('/'):
                        url = self.BASE_URL.rstrip('/') + url
                    elif not url.startswith('http'):
                        url = self.BASE_URL.rstrip('/') + '/' + url
                    return url
            
            link = vaga_element.find('a', href=re.compile(r'vaga|job|emprego'))
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
            url = f"{self.BASE_URL}?vagas-de-emprego=1&page={page_number}"
            response = self.session.get(url)
            
            if response.status_code != 200:
                if page_number == 1:
                    url = self.BASE_URL + "?vagas-de-emprego=1"
                else:
                    url = self.BASE_URL + f"pagina/{page_number}/?vagas-de-emprego=1"
                response = self.session.get(url)
                
                if response.status_code != 200:
                    print(f"Erro ao acessar página {page_number}: Status {response.status_code}")
                    return []
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            
            vagas = []
            vaga_elements = []
            
            # Tenta diferentes estratégias para encontrar os elementos
            vaga_elements = soup.find_all('div', id=re.compile(r'^id-\d+'))
            
            if not vaga_elements:
                possible_vaga_divs = soup.find_all('div', class_=re.compile(r'.*vaga.*|.*job.*|.*offer.*|.*anuncio.*|.*listing.*'))
                if not possible_vaga_divs:
                    for div in soup.find_all('div'):
                        text = div.get_text()
                        if ' - PR' in text and re.search(r'\d{2}/\d{2}/\d{4}', text):
                            vaga_elements.append(div)
                else:
                    for div in possible_vaga_divs:
                        text = div.get_text()
                        if ' - PR' in text or re.search(r'\d{2}/\d{2}/\d{4}', text):
                            vaga_elements.append(div)
            
            if not vaga_elements:
                for element in soup.find_all(['div', 'article', 'section']):
                    text = element.get_text()
                    if ' - PR' in text or re.search(r'\d{2}/\d{2}/\d{4}', text):
                        if len(text) < 5000:
                            vaga_elements.append(element)
            
            print(f"Encontrados {len(vaga_elements)} elementos de vaga na página {page_number}")
            
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            if not vagas and page_number == 1:
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
    
    def scrape_all_pages(self, max_pages: int = 91, progress_callback: Optional[Callable] = None) -> pd.DataFrame:
        """
        Scrape todas as páginas especificadas e retorna um DataFrame.
        """
        all_vagas = []
        self.total_vagas = 0
        self.pagina_atual = 0
        
        for page in range(1, max_pages + 1):
            self.pagina_atual = page
            
            # Atualiza o progresso
            if progress_callback:
                progress_callback(page, max_pages, "Extraindo página {}/{}".format(page, max_pages))
            
            print(f"Scraping página {page}...")
            
            vagas = self.scrape_page(page)
            
            if not vagas:
                print(f"Nenhuma vaga encontrada na página {page}. Parando...")
                if progress_callback:
                    progress_callback(page, max_pages, "Nenhuma vaga encontrada na página {}".format(page))
                break
            
            all_vagas.extend(vagas)
            self.total_vagas += len(vagas)
            print(f"Extraídas {len(vagas)} vagas da página {page}")
            
            if progress_callback:
                progress_callback(page, max_pages, "Extraídas {} vagas da página {}".format(len(vagas), page))
            
            # Delay para não sobrecarregar o servidor
            time.sleep(2)
        
        if all_vagas:
            df = pd.DataFrame(all_vagas)
            df = df.drop_duplicates(subset=['empresa', 'cidade', 'data_publicacao'])
            if progress_callback:
                progress_callback(max_pages, max_pages, "Extração concluída! Total: {} vagas".format(len(df)))
            return df
        else:
            if progress_callback:
                progress_callback(max_pages, max_pages, "Nenhuma vaga encontrada.")
            return pd.DataFrame()
