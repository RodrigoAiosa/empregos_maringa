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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
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
            title_elem = vaga_element.find(['h2', 'h3', 'h4', 'h5'])
            titulo = title_elem.get_text(strip=True) if title_elem else "N/A"
            titulo = self.fix_encoding(titulo)
            
            # Procura por empresa
            empresa = "N/A"
            
            # Tenta encontrar empresa por diferentes classes
            empresa_classes = ['empresa', 'company', 'nome-empresa', 'company-name', 'nome-da-empresa']
            for classe in empresa_classes:
                empresa_elem = vaga_element.find('div', class_=re.compile(classe, re.I))
                if empresa_elem:
                    empresa = empresa_elem.get_text(strip=True)
                    empresa = self.fix_encoding(empresa)
                    break
            
            # Se não encontrou, procura por spans com texto que parece ser empresa
            if empresa == "N/A":
                for span in vaga_element.find_all(['span', 'div', 'p']):
                    text = span.get_text(strip=True)
                    # Verifica se parece um nome de empresa (não tem data, não tem UF)
                    if (len(text) > 2 and len(text) < 100 and 
                        not re.search(r'\d{2}/\d{2}/\d{4}', text) and 
                        not re.search(r'[A-Z]{2}', text) and
                        not re.search(r'R\$|Salário|Cidade|Estado', text, re.I)):
                        empresa = self.fix_encoding(text)
                        break
            
            # Procura por localização
            cidade = "N/A"
            estado = "N/A"
            
            # Procura por padrão de localização: Cidade - UF ou Cidade – UF
            local_patterns = [
                r'([A-Za-zÀ-ú\s]+)\s*[-–]\s*([A-Z]{2})',
                r'([A-Za-zÀ-ú\s]+)\s*/\s*([A-Z]{2})',
                r'([A-Za-zÀ-ú\s]+)\s*\(([A-Z]{2})\)'
            ]
            
            for pattern in local_patterns:
                local_elements = vaga_element.find_all(string=re.compile(pattern))
                if local_elements:
                    local_text = self.fix_encoding(local_elements[0].strip())
                    match = re.search(pattern, local_text)
                    if match:
                        cidade = self.fix_encoding(match.group(1).strip())
                        estado = self.fix_encoding(match.group(2).strip())
                        break
            
            # Procura por data
            data = "N/A"
            
            # Procura por padrões de data
            date_patterns = [
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{1,2}\s+de\s+[A-Za-zÀ-ú]+\s+de\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ]
            
            for pattern in date_patterns:
                date_elements = vaga_element.find_all(string=re.compile(pattern))
                if date_elements:
                    data_text = self.fix_encoding(date_elements[0].strip())
                    match = re.search(pattern, data_text)
                    if match:
                        data = match.group(1) if len(match.groups()) > 0 else match.group(0)
                        break
            
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
                if href and any(keyword in href for keyword in ['vaga', 'job', 'emprego', 'detalhes', 'view']):
                    url = href
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
            # Tenta diferentes formatos de URL
            urls_to_try = [
                f"{self.BASE_URL}vagas-de-emprego/page/{page_number}/",
                f"{self.BASE_URL}?page={page_number}&vagas-de-emprego=1",
                f"{self.BASE_URL}pagina/{page_number}/?vagas-de-emprego=1",
                f"{self.BASE_URL}page/{page_number}/",
                f"{self.BASE_URL}?page={page_number}",
                f"{self.BASE_URL}?pagina={page_number}",
                f"{self.BASE_URL}vagas/page/{page_number}/"
            ]
            
            response = None
            for url in urls_to_try:
                try:
                    print(f"Tentando URL: {url}")
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        print(f"URL com sucesso: {url}")
                        break
                except Exception as e:
                    print(f"Erro na URL {url}: {e}")
                    continue
            
            if not response or response.status_code != 200:
                print(f"Erro ao acessar página {page_number}")
                return []
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            
            vagas = []
            
            # Estratégia 1: Procura por elementos de vaga usando diferentes seletores
            selectors = [
                ('div', {'class': re.compile(r'vaga|job|offer|listing|card|item', re.I)}),
                ('div', {'id': re.compile(r'^id-\d+')}),
                ('article', {}),
                ('div', {'class': re.compile(r'post|entry|content', re.I)}),
                ('li', {'class': re.compile(r'vaga|job', re.I)}),
                ('div', {'class': re.compile(r'result|search-result', re.I)})
            ]
            
            vaga_elements = []
            for tag, attrs in selectors:
                try:
                    if attrs:
                        elements = soup.find_all(tag, attrs)
                    else:
                        elements = soup.find_all(tag)
                    
                    if elements:
                        # Filtra elementos que contêm padrões de vaga
                        for elem in elements:
                            text = elem.get_text()
                            if (re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) or 
                                re.search(r'\d{2}/\d{2}/\d{4}', text)):
                                vaga_elements.append(elem)
                        if vaga_elements:
                            break
                except:
                    continue
            
            print(f"Encontrados {len(vaga_elements)} elementos de vaga na página {page_number}")
            
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            # Se não encontrou nada, tenta extrair do texto da página
            if not vagas:
                print(f"Nenhuma vaga encontrada com os métodos padrão. Tentando extração de texto...")
                vagas = self.parse_from_text_content(soup)
            
            return vagas
            
        except Exception as e:
            print(f"Erro ao scraper página {page_number}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def parse_from_text_content(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Método alternativo para extrair dados baseado no padrão de texto observado.
        """
        vagas = []
        text = soup.get_text()
        
        # Divide o texto em blocos
        lines = text.split('\n')
        current_block = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Procura por padrões de vaga
            if re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', line) or re.search(r'\d{2}/\d{2}/\d{4}', line):
                current_block.append(line)
            elif current_block and len(current_block) > 0:
                # Verifica se o bloco anterior contém informações de vaga
                block_text = ' '.join(current_block)
                if re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', block_text) and re.search(r'\d{2}/\d{2}/\d{4}', block_text):
                    vaga = self.extract_vaga_from_text(block_text)
                    if vaga:
                        vagas.append(vaga)
                current_block = []
        
        # Processa o último bloco
        if current_block:
            block_text = ' '.join(current_block)
            if re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', block_text) and re.search(r'\d{2}/\d{2}/\d{4}', block_text):
                vaga = self.extract_vaga_from_text(block_text)
                if vaga:
                    vagas.append(vaga)
        
        return vagas
    
    def extract_vaga_from_text(self, text: str) -> Optional[Dict]:
        """
        Extrai informações de vaga de um bloco de texto.
        """
        try:
            # Extrai localização
            local_match = re.search(r'([A-Za-zÀ-ú\s]+)\s*[-–]\s*([A-Z]{2})', text)
            cidade = "N/A"
            estado = "N/A"
            if local_match:
                cidade = self.fix_encoding(local_match.group(1).strip())
                estado = self.fix_encoding(local_match.group(2).strip())
            
            # Extrai data
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
            data = date_match.group(1) if date_match else "N/A"
            
            # Extrai empresa (tenta pegar o texto antes da localização)
            empresa = "N/A"
            if local_match:
                # Pega o texto antes da localização
                empresa_match = re.search(r'^([^\-–]+)', text[:local_match.start()].strip())
                if empresa_match:
                    empresa = self.fix_encoding(empresa_match.group(1).strip())
            
            if empresa == "N/A":
                # Tenta encontrar um nome de empresa no texto
                words = text.split()
                for word in words:
                    if len(word) > 3 and not re.search(r'\d', word):
                        empresa = self.fix_encoding(word)
                        break
            
            return {
                'titulo': 'N/A',
                'empresa': empresa,
                'cidade': cidade,
                'estado': estado,
                'data_publicacao': data,
                'url': 'N/A'
            }
            
        except Exception as e:
            print(f"Erro ao extrair vaga do texto: {e}")
            return None
    
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
            
            if vagas:
                all_vagas.extend(vagas)
                self.total_vagas += len(vagas)
                print(f"Extraídas {len(vagas)} vagas da página {page}. Total acumulado: {self.total_vagas}")
                
                if progress_callback:
                    progress_callback(page, max_pages, f"Extraídas {len(vagas)} vagas da página {page}")
            else:
                print(f"Nenhuma vaga encontrada na página {page}.")
                # Se não encontrou nada, tenta a próxima página
                if progress_callback:
                    progress_callback(page, max_pages, f"Nenhuma vaga na página {page}")
            
            # Delay para não sobrecarregar o servidor
            time.sleep(1)
        
        if all_vagas:
            df = pd.DataFrame(all_vagas)
            
            # Remove duplicatas baseadas em empresa, cidade e data
            df = df.drop_duplicates(subset=['empresa', 'cidade', 'data_publicacao'], keep='first')
            
            # Tenta ordenar por data
            try:
                df['data_publicacao'] = pd.to_datetime(df['data_publicacao'], format='%d/%m/%Y', errors='coerce')
                df = df.sort_values('data_publicacao', ascending=False)
                df['data_publicacao'] = df['data_publicacao'].dt.strftime('%d/%m/%Y')
            except:
                pass
            
            # Salva em CSV para debug
            df.to_csv('vagas_extraidas.csv', index=False, encoding='utf-8-sig')
            print(f"Total de vagas extraídas: {len(df)}")
            
            if progress_callback:
                progress_callback(max_pages, max_pages, f"Extração concluída! Total: {len(df)} vagas")
            return df
        else:
            if progress_callback:
                progress_callback(max_pages, max_pages, "Nenhuma vaga encontrada.")
            return pd.DataFrame()
