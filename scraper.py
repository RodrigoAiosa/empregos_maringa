import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional
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
    
    def fix_encoding(self, text: str) -> str:
        """
        Corrige problemas de codificação como 'MaringÃ¡' para 'Maringá'
        """
        if not text:
            return text
        
        # Tenta corrigir codificação comum
        try:
            # Se o texto contém caracteres mal codificados, tenta recodificar
            if 'Ã¡' in text or 'Ã£' in text or 'Ã§' in text:
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
        Adaptado para funcionar com a estrutura observada no site.
        """
        try:
            # Tenta encontrar a empresa
            empresa_elem = vaga_element.find('div', class_='d-none d-md-block')
            empresa = empresa_elem.get_text(strip=True) if empresa_elem else "N/A"
            empresa = self.fix_encoding(empresa)
            
            # Tenta encontrar a data
            data = "N/A"
            # Procura por padrões de data (dd/mm/aaaa)
            date_elements = vaga_element.find_all(string=re.compile(r'\d{2}/\d{2}/\d{4}'))
            if date_elements:
                data = date_elements[0].strip()
                data = self.fix_encoding(data)
            
            # Se ainda não encontrou data, tenta outra abordagem
            if data == "N/A":
                # Procura por elementos com classe text-nowrap ml-4
                data_elem = vaga_element.find('div', class_='text-nowrap ml-4')
                if data_elem:
                    data = data_elem.get_text(strip=True)
                    data = self.fix_encoding(data)
                    # Limpa a data se necessário
                    if ' ' in data:
                        data = data.split(' ')[0]  # Pega apenas a data, não o horário
            
            # Se ainda não encontrou data, tenta encontrar em spans
            if data == "N/A":
                # Procura por spans com data
                data_spans = vaga_element.find_all('span', string=re.compile(r'\d{2}/\d{2}/\d{4}'))
                if data_spans:
                    data = data_spans[0].get_text(strip=True)
                    data = self.fix_encoding(data)
            
            # Extrai URL usando o XPath específico
            url = self.extract_url_with_xpath(vaga_element)
            
            # Extrai localização (cidade e estado)
            cidade = "N/A"
            estado = "N/A"
            
            # Procura por elementos que contenham " - PR" ou similar
            local_elements = vaga_element.find_all(['div', 'span', 'p'], string=re.compile(r'.*\s+-\s+[A-Z]{2}'))
            if local_elements:
                localizacao = local_elements[0].get_text(strip=True)
                localizacao = self.fix_encoding(localizacao)
                # Tenta separar cidade e estado
                if ' - ' in localizacao:
                    partes = localizacao.split(' - ')
                    if len(partes) == 2:
                        cidade = self.fix_encoding(partes[0].strip())
                        estado = self.fix_encoding(partes[1].strip())
            
            # Se não encontrou com a primeira estratégia, tenta outra abordagem
            if cidade == "N/A":
                # Procura por padrões como "Maringá - PR"
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
            
            # Verifica se encontrou dados mínimos
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
        Extrai a URL usando o XPath específico: //*[@id="id-546313"]/div/div[3]/a
        """
        try:
            # Converte o elemento BeautifulSoup para lxml para usar XPath
            # Primeiro, obtém o HTML do elemento
            html_content = str(vaga_element)
            
            # Parse com lxml para usar XPath
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_content, parser)
            
            # Tenta encontrar o link usando XPath
            # Como o ID específico pode variar, procuramos por padrões semelhantes
            # Primeiro tenta o XPath exato com ID específico
            link_elements = tree.xpath('//*[@id="id-546313"]/div/div[3]/a')
            
            # Se não encontrou, tenta um padrão mais genérico
            if not link_elements:
                # Tenta encontrar qualquer link que possa ser de vaga
                # Procura por links que contenham padrão de URL de vaga
                link_elements = tree.xpath('//a[contains(@href, "vaga") or contains(@href, "job") or contains(@href, "emprego")]')
            
            # Se ainda não encontrou, tenta encontrar qualquer link dentro da estrutura
            if not link_elements:
                # Procura por links que possam estar em divs com classes específicas
                link_elements = tree.xpath('//div[contains(@class, "d-flex")]//a | //div[contains(@class, "text-nowrap")]//a')
            
            if link_elements:
                url = link_elements[0].get('href')
                if url:
                    # Se for URL relativa, converte para absoluta
                    if url.startswith('/'):
                        url = self.BASE_URL.rstrip('/') + url
                    elif not url.startswith('http'):
                        url = self.BASE_URL.rstrip('/') + '/' + url
                    return url
            
            # Última tentativa: procura usando BeautifulSoup
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
            # Para o site empregos.maringa.com, a paginação parece ser feita via parâmetro GET
            # ou via URL com número de página
            # Vamos tentar a abordagem com parâmetro paginação
            params = {
                'vagas-de-emprego': '1',
                'page': page_number
            }
            
            # Tentativa 1: URL com parâmetro page
            url = f"{self.BASE_URL}?vagas-de-emprego=1&page={page_number}"
            
            # Tentativa 2: Se a primeira não funcionar, tentamos com paginação tradicional
            # Alguns sites usam /page/2/ ou similar
            response = self.session.get(url)
            
            if response.status_code != 200:
                # Tenta uma URL alternativa
                if page_number == 1:
                    url = self.BASE_URL + "?vagas-de-emprego=1"
                else:
                    url = self.BASE_URL + f"pagina/{page_number}/?vagas-de-emprego=1"
                response = self.session.get(url)
                
                if response.status_code != 200:
                    print(f"Erro ao acessar página {page_number}: Status {response.status_code}")
                    return []
            
            # Força o encoding para UTF-8
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tenta diferentes seletores para encontrar os elementos das vagas
            vagas = []
            
            # Estratégia 1: procura por divs com id começando com 'id-'
            vaga_elements = soup.find_all('div', id=re.compile(r'^id-\d+'))
            
            # Estratégia 2: se não encontrou, procura por divs com classes específicas
            if not vaga_elements:
                # Tenta encontrar divs que possam conter informações de vaga
                possible_vaga_divs = soup.find_all('div', class_=re.compile(r'.*vaga.*|.*job.*|.*offer.*|.*anuncio.*|.*listing.*'))
                if not possible_vaga_divs:
                    # Última tentativa: procura por divs que contenham padrões de texto específicos
                    for div in soup.find_all('div'):
                        text = div.get_text()
                        if ' - PR' in text and re.search(r'\d{2}/\d{2}/\d{4}', text):
                            vaga_elements.append(div)
                else:
                    # Filtra os elementos que realmente parecem ser vagas
                    for div in possible_vaga_divs:
                        # Verifica se contém padrões comuns de vagas
                        text = div.get_text()
                        if ' - PR' in text or re.search(r'\d{2}/\d{2}/\d{4}', text):
                            vaga_elements.append(div)
            
            # Se ainda não encontrou nada, tenta uma abordagem mais genérica
            if not vaga_elements:
                # Procura por blocos que contenham informações de vaga
                for element in soup.find_all(['div', 'article', 'section']):
                    # Verifica se o elemento contém texto que parece ser de vaga
                    text = element.get_text()
                    if ' - PR' in text or re.search(r'\d{2}/\d{2}/\d{4}', text):
                        # Verifica se não é um elemento muito grande
                        if len(text) < 5000:
                            vaga_elements.append(element)
            
            print(f"Encontrados {len(vaga_elements)} elementos de vaga na página {page_number}")
            
            # Extrai dados de cada elemento
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            # Se não encontrou vagas, tenta uma última abordagem baseada no conteúdo fornecido
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
        
        # Padrão: Empresa e Localização
        # Baseado no conteúdo fornecido:
        # "Bianchi Distribuidora Maringá - PR 19/06/2026"
        
        # Vamos usar regex para encontrar padrões de vaga
        # Padrão: Texto com cidade - PR e data
        pattern = r'([A-Za-zÀ-ú\s\.]+)\s*([A-Za-zÀ-ú]+\s*-\s*[A-Z]{2})\s*(\d{2}/\d{2}/\d{4})'
        
        matches = re.findall(pattern, text)
        
        for match in matches:
            empresa, localizacao, data = match
            
            empresa = self.fix_encoding(empresa.strip())
            localizacao = self.fix_encoding(localizacao.strip())
            data = self.fix_encoding(data.strip())
            
            # Extrai cidade e estado
            cidade = "N/A"
            estado = "N/A"
            if ' - ' in localizacao:
                partes = localizacao.split(' - ')
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
                    'empresa': empresa,
                    'cidade': cidade,
                    'estado': estado,
                    'data_publicacao': data,
                    'url': url
                })
        
        return vagas
    
    def scrape_all_pages(self, max_pages: int = 5) -> pd.DataFrame:
        """
        Scrape todas as páginas especificadas e retorna um DataFrame.
        """
        all_vagas = []
        
        for page in range(1, max_pages + 1):
            print(f"Scraping página {page}...")
            
            vagas = self.scrape_page(page)
            
            if not vagas:
                print(f"Nenhuma vaga encontrada na página {page}. Parando...")
                break
            
            all_vagas.extend(vagas)
            print(f"Extraídas {len(vagas)} vagas da página {page}")
            
            # Delay para não sobrecarregar o servidor
            time.sleep(2)
        
        if all_vagas:
            df = pd.DataFrame(all_vagas)
            # Remove duplicatas baseado na empresa + cidade + data
            df = df.drop_duplicates(subset=['empresa', 'cidade', 'data_publicacao'])
            return df
        else:
            return pd.DataFrame()
