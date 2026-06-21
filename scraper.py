import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional, Callable
import unicodedata

class EmpregosMaringaScraper:
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
        if not text:
            return text
        try:
            if any(x in text for x in ['Ã¡', 'Ã£', 'Ã§', 'Ã©', 'Ã³']):
                text = text.encode('latin-1').decode('utf-8')
            return text
        except:
            try:
                return unicodedata.normalize('NFKC', text)
            except:
                return text

    def extract_url(self, vaga_element) -> str:
        try:
            for link in vaga_element.find_all('a'):
                href = link.get('href', '').strip()
                if href and href not in ('#', '', '/'):
                    if href.startswith('/'):
                        href = self.BASE_URL.rstrip('/') + href
                    elif not href.startswith('http'):
                        href = self.BASE_URL.rstrip('/') + '/' + href
                    return href
            return "N/A"
        except:
            return "N/A"

    def extract_vaga_data(self, vaga_element) -> Optional[Dict]:
        try:
            html_str = str(vaga_element)
            text = vaga_element.get_text(separator=' ', strip=True)

            # Empresa
            empresa = "N/A"
            for pattern in [
                r'<div[^>]*class="[^"]*empresa[^"]*"[^>]*>([^<]+)</div>',
                r'<span[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</span>',
                r'<div[^>]*class="[^"]*nome-empresa[^"]*"[^>]*>([^<]+)</div>',
            ]:
                m = re.search(pattern, html_str, re.I)
                if m:
                    empresa = self.fix_encoding(m.group(1).strip())
                    break

            if empresa == "N/A":
                for line in text.split('\n'):
                    line = line.strip()
                    if (3 < len(line) < 100
                            and not re.search(r'\d{2}/\d{2}/\d{4}', line)
                            and not re.search(r'\b[A-Z]{2}\b', line)
                            and not re.search(r'R\$|Sal.rio|Cidade|Estado', line, re.I)):
                        empresa = self.fix_encoding(line)
                        break

            # Localização
            cidade = estado = "N/A"
            for pattern in [
                r'([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{1,40}?)\s*[-–]\s*([A-Z]{2})\b',
                r'([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{1,40}?)\s*/\s*([A-Z]{2})\b',
                r'([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{1,40}?)\s*\(([A-Z]{2})\)',
            ]:
                m = re.search(pattern, text)
                if m:
                    cidade = self.fix_encoding(m.group(1).strip())
                    estado = self.fix_encoding(m.group(2).strip())
                    break

            # Data
            data = "N/A"
            for pattern in [r'(\d{2}/\d{2}/\d{4})', r'(\d{1,2}\s+de\s+[A-Za-zÀ-ú]+\s+de\s+\d{4})']:
                m = re.search(pattern, text)
                if m:
                    data = m.group(1)
                    break

            # URL
            url = self.extract_url(vaga_element)

            if empresa == "N/A" and url == "N/A":
                return None

            return {'empresa': empresa, 'cidade': cidade, 'estado': estado, 'data_publicacao': data, 'url': url}

        except Exception as e:
            print(f"Erro ao extrair vaga: {e}")
            return None

    def scrape_page(self, page_number: int) -> List[Dict]:
        try:
            urls_to_try = [
                f"{self.BASE_URL}vagas-de-emprego/page/{page_number}/",
                f"{self.BASE_URL}?page={page_number}&vagas-de-emprego=1",
                f"{self.BASE_URL}pagina/{page_number}/?vagas-de-emprego=1",
                f"{self.BASE_URL}?pagina={page_number}",
                f"{self.BASE_URL}page/{page_number}/",
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

            if not response or response.status_code != 200:
                print(f"Erro ao acessar pagina {page_number}")
                return []

            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')

            # --- Detecta estrutura do site automaticamente ---
            vaga_elements = []

            # Estratégia 1: divs com id="id-XXXXX"
            id_pattern = re.compile(r'^id-\d+$')
            elements_with_id = soup.find_all(id=id_pattern)
            if elements_with_id:
                vaga_elements = elements_with_id
                print(f"Estrategia 1 (id-XXXXX): {len(vaga_elements)} elementos")

            # Estratégia 2: qualquer tag com classe contendo 'vaga'
            if not vaga_elements:
                found = soup.find_all(class_=re.compile(r'\bvaga\b', re.I))
                # Pega apenas folhas (elementos sem filhos do mesmo tipo)
                vaga_elements = [e for e in found if not e.find(class_=re.compile(r'\bvaga\b', re.I))]
                if vaga_elements:
                    print(f"Estrategia 2 (classe vaga): {len(vaga_elements)} elementos")

            # Estratégia 3: artigos
            if not vaga_elements:
                vaga_elements = soup.find_all('article')
                if vaga_elements:
                    print(f"Estrategia 3 (article): {len(vaga_elements)} elementos")

            # Estratégia 4: li com link de vaga
            if not vaga_elements:
                candidates = []
                for li in soup.find_all('li'):
                    if li.find('a', href=True):
                        t = li.get_text()
                        if re.search(r'\d{2}/\d{2}/\d{4}', t) or re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', t):
                            candidates.append(li)
                if candidates:
                    vaga_elements = candidates
                    print(f"Estrategia 4 (li): {len(vaga_elements)} elementos")

            # Estratégia 5: tr com dados de vaga
            if not vaga_elements:
                candidates = []
                for tr in soup.find_all('tr'):
                    t = tr.get_text()
                    if re.search(r'\d{2}/\d{2}/\d{4}', t) and re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', t):
                        candidates.append(tr)
                if candidates:
                    vaga_elements = candidates
                    print(f"Estrategia 5 (tr): {len(vaga_elements)} elementos")

            # Estratégia 6: divs folha com texto curto contendo dados de vaga
            if not vaga_elements:
                candidates = []
                for div in soup.find_all('div'):
                    # Só divs "folha" (sem divs filhos) - evita pegar containers
                    if div.find('div'):
                        continue
                    t = div.get_text(strip=True)
                    if (50 < len(t) < 800
                            and re.search(r'\d{2}/\d{2}/\d{4}', t)
                            and re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', t)):
                        candidates.append(div)
                if candidates:
                    vaga_elements = candidates
                    print(f"Estrategia 6 (div folha): {len(vaga_elements)} elementos")

            print(f"Total de elementos encontrados na pagina {page_number}: {len(vaga_elements)}")

            vagas = []
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)

            # Remove duplicatas dentro da página pela URL
            seen = set()
            vagas_unicas = []
            for v in vagas:
                key = v['url'] if v['url'] != 'N/A' else f"{v['empresa']}|{v['cidade']}|{v['data_publicacao']}"
                if key not in seen:
                    seen.add(key)
                    vagas_unicas.append(v)

            print(f"Vagas unicas na pagina {page_number}: {len(vagas_unicas)} (de {len(vagas)} extraidas)")

            if not vagas_unicas:
                print(f"Tentando extracao por texto na pagina {page_number}...")
                vagas_unicas = self.parse_from_text_content(soup)

            return vagas_unicas

        except Exception as e:
            print(f"Erro ao scraper pagina {page_number}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def parse_from_text_content(self, soup: BeautifulSoup) -> List[Dict]:
        vagas = []
        text = soup.get_text()
        blocks = re.split(r'\n\s*\n', text)
        for block in blocks:
            if not block.strip():
                continue
            if re.search(r'[A-Za-zÀ-ú]+\s*[-–]\s*[A-Z]{2}', block) and re.search(r'\d{2}/\d{2}/\d{4}', block):
                vaga = self.extract_vaga_from_text(block)
                if vaga:
                    vagas.append(vaga)
        return vagas

    def extract_vaga_from_text(self, text: str) -> Optional[Dict]:
        try:
            local_match = re.search(r'([A-Za-zÀ-ú\s]+)\s*[-–]\s*([A-Z]{2})', text)
            cidade = estado = "N/A"
            if local_match:
                cidade = self.fix_encoding(local_match.group(1).strip())
                estado = self.fix_encoding(local_match.group(2).strip())

            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
            data = date_match.group(1) if date_match else "N/A"

            empresa = "N/A"
            if local_match:
                before = re.sub(r'[\d\W]+', ' ', text[:local_match.start()]).strip()
                words = before.split()
                if words:
                    empresa = self.fix_encoding(' '.join(words[:3]))
            
            if empresa == "N/A" or len(empresa) < 2:
                return None

            url_match = re.search(r'https?://[^\s<>"]+', text)
            url = url_match.group(0) if url_match else "N/A"

            return {'empresa': empresa, 'cidade': cidade, 'estado': estado, 'data_publicacao': data, 'url': url}
        except:
            return None

    def scrape_all_pages(self, max_pages: int = 200, progress_callback: Optional[Callable] = None) -> pd.DataFrame:
        all_vagas = []
        self.total_vagas = 0
        self.pagina_atual = 0
        paginas_sem_vagas = 0
        max_paginas_sem_vagas = 5

        # Chave única por vaga para dedup em tempo real
        seen_global = set()

        for page in range(1, max_pages + 1):
            self.pagina_atual = page

            if progress_callback:
                progress_callback(page, max_pages, f"Extraindo pagina {page}/{max_pages}")

            print(f"Scraping pagina {page}...")
            vagas = self.scrape_page(page)

            if vagas:
                novas = 0
                for v in vagas:
                    key = v['url'] if v['url'] != 'N/A' else f"{v['empresa']}|{v['cidade']}|{v['data_publicacao']}"
                    if key not in seen_global:
                        seen_global.add(key)
                        all_vagas.append(v)
                        novas += 1

                self.total_vagas = len(all_vagas)
                paginas_sem_vagas = 0
                print(f"Pagina {page}: {novas} vagas novas. Total acumulado: {self.total_vagas}")

                if progress_callback:
                    progress_callback(page, max_pages, f"Pagina {page}: +{novas} vagas. Total: {self.total_vagas}")
            else:
                paginas_sem_vagas += 1
                print(f"Nenhuma vaga na pagina {page}. ({paginas_sem_vagas}/{max_paginas_sem_vagas})")
                if paginas_sem_vagas >= max_paginas_sem_vagas:
                    print(f"Parando apos {paginas_sem_vagas} paginas sem vagas.")
                    break

            time.sleep(1)

        if all_vagas:
            df = pd.DataFrame(all_vagas)

            try:
                df['data_publicacao'] = pd.to_datetime(df['data_publicacao'], format='%d/%m/%Y', errors='coerce')
                df = df.sort_values('data_publicacao', ascending=False)
                df['data_publicacao'] = df['data_publicacao'].dt.strftime('%d/%m/%Y')
            except:
                pass

            try:
                from csv_manager import CSVManager
                CSVManager().save_dataframe(df)
            except Exception:
                df.to_excel('vagas_extraidas.xlsx', index=False)

            print(f"Total de vagas salvas: {len(df)}")

            if progress_callback:
                progress_callback(max_pages, max_pages, f"Extracao concluida! Total: {len(df)} vagas")

            return df
        else:
            if progress_callback:
                progress_callback(max_pages, max_pages, "Nenhuma vaga encontrada.")
            return pd.DataFrame()
