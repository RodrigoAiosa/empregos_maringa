import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional, Callable
import unicodedata

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
            # Procura por empresa
            empresa = "N/A"
            
            # Tenta encontrar empresa por diferentes padrões
            empresa_patterns = [
                r'<div[^>]*class="[^"]*empresa[^"]*"[^>]*>([^<]+)</div>',
                r'<span[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</span>',
                r'<div[^>]*class="[^"]*nome-empresa[^"]*"[^>]*>([^<]+)</div>',
            ]
            
            html_str = str(vaga_element)
            for pattern in empresa_patterns:
                match = re.search(pattern, html_str, re.I)
                if match:
                    empresa = self.fix_encoding(match.group(1).strip())
                    break
            
            # Se não encontrou, procura por texto que parece empresa
            if empresa == "N/A":
                text = vaga_element.get_text()
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if (len(line) > 3 and len(line) < 100 and 
                        not re.search(r'\d{2}/\d{2}/\d{4}', line) and 
                        not re.search(r'[A-Z]{2}', line) and
                        not re.search(r'R\$|Salário|Cidade|Estado|N/A', line, re.I)):
                        empresa = self.fix_encoding(line)
                        break
            
            # Procura por localização
            cidade = "N/A"
            estado = "N/A"
            
            local_patterns = [
                r'([A-Za-zÀ-ú\s]+)\s*[-–]\s*([A-Z]{2})',
                r'([A-Za-zÀ-ú\s]+)\s*/\s*([A-Z]{2})',
                r'([A-Za-zÀ-ú\s]+)\s*\(([A-Z]{2})\)'
            ]
            
            text = vaga_element.get_text()
            for pattern in local_patterns:
                match = re.search(pattern, text)
                if match:
                    cidade = self.fix_encoding(match.group(1).strip())
                    estado = self.fix_encoding(match.group(2).strip())
                    break
            
            # Procura por data
            data = "N/A"
            date_patterns = [
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{1,2}\s+de\s+[A-Za-zÀ-ú]+\s+de\s+\d{4})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    data = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    break
            
            # Extrai URL
            url = self.extract_url(vaga_element)
            
            # FIX #1: Aceita a vaga se tiver URL OU empresa (não precisa dos dois)
            if empresa == "N/A" and url == "N/A":
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
    
    def extract_url(self, vaga_element) -> str:
        """
        Extrai a URL da vaga.
        """
        try:
            # FIX #2: Aceita qualquer link dentro do elemento de vaga, não só 'vaga-empregos'
            for link in vaga_element.find_all('a'):
                href = link.get('href', '')
                if href and href not in ('#', '', '/'):
                    url = href
                    if url.startswith('/'):
                        url = self.BASE_URL.rstrip('/') + url
                    elif not url.startswith('http'):
                        url = self.BASE_URL.rstrip('/') + '/' + url
                    return url
            
            # Busca qualquer href no HTML do elemento
            text = str(vaga_element)
            url_pattern = r'href="([^"#][^"]*)"'
            match = re.search(url_pattern, text)
            if match:
                url = match.group(1)
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
            # URLs para tentar
            urls_to_try = [
                f"{self.BASE_URL}vagas-de-emprego/page/{page_number}/",
                f"{self.BASE_URL}?page={page_number}&vagas-de-emprego=1",
                f"{self.BASE_URL}pagina/{page_number}/?vagas-de-emprego=1",
                f"{self.BASE_URL}?pagina={page_number}",
                f"{self.BASE_URL}page/{page_number}/"
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
            
            # Procura por elementos que contêm vagas
            vaga_elements = []
            
            # Estratégia 1: Divs com ID id-XXXXX
            id_pattern = re.compile(r'^id-\d+$')
            elements_with_id = soup.find_all('div', id=id_pattern)
            if elements_with_id:
                vaga_elements = elements_with_id
                print(f"Encontrados {len(vaga_elements)} elementos com ID")
            
            # Estratégia 2: Divs com classes comuns
            if not vaga_elements:
                class_patterns = ['vaga', 'job', 'offer', 'listing', 'item', 'post', 'entry']
                for class_name in class_patterns:
                    elements = soup.find_all('div', class_=re.compile(class_name, re.I))
                    if elements:
                        # Filtra elementos que parecem vagas
                        for elem in elements:
                            text = elem.get_text()
                            if (re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) or 
                                re.search(r'\d{2}/\d{2}/\d{4}', text)):
                                vaga_elements.append(elem)
                        if vaga_elements:
                            break
            
            # Estratégia 3: Artigos
            if not vaga_elements:
                articles = soup.find_all('article')
                for article in articles:
                    text = article.get_text()
                    if (re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) and 
                        re.search(r'\d{2}/\d{2}/\d{4}', text)):
                        vaga_elements.append(article)
            
            # FIX #3: Estratégia 4 sem limite arbitrário de 20 elementos
            if not vaga_elements:
                all_divs = soup.find_all('div')
                for div in all_divs:
                    text = div.get_text()
                    if (re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) and 
                        re.search(r'\d{2}/\d{2}/\d{4}', text) and
                        len(text) < 2000):
                        vaga_elements.append(div)
                # REMOVIDO: limite de 20 que cortava as vagas da página
            
            # Estratégia 5: Linhas/células de tabela
            if not vaga_elements:
                rows = soup.find_all('tr')
                for row in rows:
                    text = row.get_text()
                    if (re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) and
                        re.search(r'\d{2}/\d{2}/\d{4}', text)):
                        vaga_elements.append(row)

            # Estratégia 6: Itens de lista (<li>)
            if not vaga_elements:
                items = soup.find_all('li')
                for item in items:
                    text = item.get_text()
                    if (re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', text) and
                        re.search(r'\d{2}/\d{2}/\d{4}', text)):
                        vaga_elements.append(item)

            print(f"Processando {len(vaga_elements)} elementos na página {page_number}")
            
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            # FIX #4: Remove duplicatas dentro da página pelo URL antes de retornar
            seen_urls = set()
            vagas_unicas = []
            for v in vagas:
                key = v.get('url', 'N/A')
                if key == 'N/A' or key not in seen_urls:
                    seen_urls.add(key)
                    vagas_unicas.append(v)
            vagas = vagas_unicas

            # Se não encontrou nada, tenta extrair do texto
            if not vagas:
                print(f"Nenhuma vaga encontrada na página {page_number}. Tentando extração de texto...")
                vagas = self.parse_from_text_content(soup)
            
            return vagas
            
        except Exception as e:
            print(f"Erro ao scraper página {page_number}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def parse_from_text_content(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Método alternativo para extrair dados do texto.
        """
        vagas = []
        text = soup.get_text()
        
        # Divide em blocos
        blocks = re.split(r'\n\s*\n', text)
        
        for block in blocks:
            if not block.strip():
                continue
            
            # Procura por padrão de localização e data
            if re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', block) and re.search(r'\d{2}/\d{2}/\d{4}', block):
                vaga = self.extract_vaga_from_text(block)
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
            
            # Extrai empresa
            empresa = "N/A"
            if local_match:
                # Pega texto antes da localização
                before = text[:local_match.start()].strip()
                # Remove números e caracteres especiais
                before = re.sub(r'\d+', '', before)
                before = re.sub(r'[^\w\sÀ-ú]', ' ', before)
                words = before.split()
                if words:
                    empresa = self.fix_encoding(' '.join(words[:3]))  # Pega até 3 palavras
            else:
                # Tenta encontrar nome no início do texto
                words = text.split()
                for i, word in enumerate(words):
                    if len(word) > 3 and not re.search(r'\d', word):
                        empresa = self.fix_encoding(word)
                        break
            
            if empresa == "N/A" or len(empresa) < 2:
                return None
            
            # Tenta encontrar URL
            url = "N/A"
            url_match = re.search(r'https?://[^\s<>"]+', text)
            if url_match:
                url = url_match.group(0)
            
            return {
                'empresa': empresa,
                'cidade': cidade,
                'estado': estado,
                'data_publicacao': data,
                'url': url
            }
            
        except Exception as e:
            print(f"Erro ao extrair vaga do texto: {e}")
            return None
    
    def scrape_all_pages(self, max_pages: int = 200, progress_callback: Optional[Callable] = None) -> pd.DataFrame:
        """
        Scrape todas as páginas especificadas e retorna um DataFrame.
        """
        all_vagas = []
        self.total_vagas = 0
        self.pagina_atual = 0
        paginas_sem_vagas = 0
        max_paginas_sem_vagas = 5  # Para após 5 páginas consecutivas sem vagas
        
        for page in range(1, max_pages + 1):
            self.pagina_atual = page
            
            if progress_callback:
                progress_callback(page, max_pages, f"Extraindo página {page}/{max_pages}")
            
            print(f"Scraping página {page}...")
            
            vagas = self.scrape_page(page)
            
            if vagas:
                all_vagas.extend(vagas)
                self.total_vagas += len(vagas)
                paginas_sem_vagas = 0
                print(f"Extraídas {len(vagas)} vagas da página {page}. Total: {self.total_vagas}")
                
                if progress_callback:
                    progress_callback(page, max_pages, f"Extraídas {len(vagas)} vagas. Total: {self.total_vagas}")
            else:
                paginas_sem_vagas += 1
                print(f"Nenhuma vaga na página {page}. ({paginas_sem_vagas}/{max_paginas_sem_vagas})")
                
                if paginas_sem_vagas >= max_paginas_sem_vagas:
                    print(f"Parando após {paginas_sem_vagas} páginas sem vagas.")
                    break
            
            # Delay entre requisições
            time.sleep(1)
        
        if all_vagas:
            df = pd.DataFrame(all_vagas)
            
            # FIX #5: Remove duplicatas APENAS pela URL (não por empresa+cidade+data)
            # Vagas sem URL (N/A) são mantidas normalmente
            df_com_url = df[df['url'] != 'N/A'].drop_duplicates(subset=['url'], keep='first')
            df_sem_url = df[df['url'] == 'N/A'].drop_duplicates(
                subset=['empresa', 'cidade', 'data_publicacao'], keep='first'
            )
            df = pd.concat([df_com_url, df_sem_url], ignore_index=True)
            
            # Tenta ordenar por data
            try:
                df['data_publicacao'] = pd.to_datetime(df['data_publicacao'], format='%d/%m/%Y', errors='coerce')
                df = df.sort_values('data_publicacao', ascending=False)
                df['data_publicacao'] = df['data_publicacao'].dt.strftime('%d/%m/%Y')
            except:
                pass
            
            # Salva em CSV
            df.to_csv('vagas_extraidas.csv', index=False, encoding='utf-8-sig')
            print(f"Total de vagas extraídas: {len(df)}")
            
            if progress_callback:
                progress_callback(max_pages, max_pages, f"Extração concluída! Total: {len(df)} vagas")
            return df
        else:
            if progress_callback:
                progress_callback(max_pages, max_pages, "Nenhuma vaga encontrada.")
            return pd.DataFrame()
