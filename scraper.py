import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional

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
    
    def extract_vaga_data(self, vaga_element) -> Optional[Dict]:
        """
        Extrai os dados de um único elemento de vaga.
        Adaptado para funcionar com a estrutura observada no site.
        """
        try:
            # Tenta encontrar o título da vaga
            titulo_elem = vaga_element.find('div', class_='d-flex flex-column flex-md-row')
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "N/A"
            
            # Tenta encontrar a empresa
            empresa_elem = vaga_element.find('div', class_='d-none d-md-block')
            empresa = empresa_elem.get_text(strip=True) if empresa_elem else "N/A"
            
            # Tenta encontrar localização e data
            # A localização e data podem estar em diferentes estruturas
            # Vamos procurar por spans com classes específicas
            
            # Primeiro, tenta encontrar a localização (cidade - estado)
            localizacao = "N/A"
            cidade = "N/A"
            estado = "N/A"
            
            # Procura por elementos que contenham " - PR" ou similar
            local_elements = vaga_element.find_all(['div', 'span', 'p'], string=re.compile(r'.*\s+-\s+[A-Z]{2}'))
            if local_elements:
                localizacao = local_elements[0].get_text(strip=True)
                # Tenta separar cidade e estado
                if ' - ' in localizacao:
                    partes = localizacao.split(' - ')
                    if len(partes) == 2:
                        cidade = partes[0].strip()
                        estado = partes[1].strip()
            
            # Se não encontrou com a primeira estratégia, tenta outra abordagem
            if localizacao == "N/A":
                # Procura por padrões como "Maringá - PR"
                text_elements = vaga_element.find_all(string=re.compile(r'[A-Za-zÀ-ú]+\s*-\s*[A-Z]{2}'))
                for elem in text_elements:
                    text = elem.strip()
                    if ' - ' in text:
                        localizacao = text
                        partes = text.split(' - ')
                        if len(partes) == 2:
                            cidade = partes[0].strip()
                            estado = partes[1].strip()
                        break
            
            # Tenta encontrar a data
            data = "N/A"
            # Procura por padrões de data (dd/mm/aaaa)
            date_elements = vaga_element.find_all(string=re.compile(r'\d{2}/\d{2}/\d{4}'))
            if date_elements:
                data = date_elements[0].strip()
            
            # Se ainda não encontrou data, tenta outra abordagem
            if data == "N/A":
                # Procura por elementos com classe text-nowrap ml-4
                data_elem = vaga_element.find('div', class_='text-nowrap ml-4')
                if data_elem:
                    data = data_elem.get_text(strip=True)
                    # Limpa a data se necessário
                    if ' ' in data:
                        data = data.split(' ')[0]  # Pega apenas a data, não o horário
            
            # Se ainda não encontrou data, tenta encontrar em spans
            if data == "N/A":
                # Procura por spans com data
                data_spans = vaga_element.find_all('span', string=re.compile(r'\d{2}/\d{2}/\d{4}'))
                if data_spans:
                    data = data_spans[0].get_text(strip=True)
            
            # Verifica se encontrou dados mínimos
            if titulo == "N/A" and empresa == "N/A":
                return None
            
            return {
                'titulo': titulo,
                'empresa': empresa,
                'cidade': cidade,
                'estado': estado,
                'localizacao': localizacao,
                'data_publicacao': data
            }
            
        except Exception as e:
            print(f"Erro ao extrair dados da vaga: {e}")
            return None
    
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
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tenta diferentes seletores para encontrar os elementos das vagas
            vagas = []
            
            # Estratégia 1: procura por divs com id começando com 'id-'
            vaga_elements = soup.find_all('div', id=re.compile(r'^id-\d+'))
            
            # Estratégia 2: se não encontrou, procura por divs com classes específicas
            if not vaga_elements:
                # Tenta encontrar divs que possam conter informações de vaga
                # Baseado no conteúdo fornecido, as vagas parecem estar em divs estruturadas
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
                # Muitos sites usam article, section ou div comuns
                for element in soup.find_all(['div', 'article', 'section']):
                    # Verifica se o elemento contém texto que parece ser de vaga
                    text = element.get_text()
                    if ' - PR' in text or re.search(r'\d{2}/\d{2}/\d{4}', text):
                        # Verifica se não é um elemento muito grande (pode ser a página toda)
                        if len(text) < 5000:  # Limita o tamanho para não pegar a página inteira
                            vaga_elements.append(element)
            
            print(f"Encontrados {len(vaga_elements)} elementos de vaga na página {page_number}")
            
            # Extrai dados de cada elemento
            for element in vaga_elements:
                vaga_data = self.extract_vaga_data(element)
                if vaga_data:
                    vagas.append(vaga_data)
            
            # Se não encontrou vagas, tenta uma última abordagem baseada no conteúdo fornecido
            if not vagas and page_number == 1:
                # O conteúdo fornecido mostra que as vagas são listadas em uma estrutura específica
                # Vamos tentar parsear manualmente baseado no padrão observado
                vagas = self.parse_from_text_content(soup)
            
            return vagas
            
        except Exception as e:
            print(f"Erro ao scraper página {page_number}: {e}")
            return []
    
    def parse_from_text_content(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Método alternativo para extrair dados baseado no padrão de texto observado.
        Útil quando o HTML está mal estruturado.
        """
        vagas = []
        text = soup.get_text()
        
        # Padrão: Título da vaga, seguido por empresa, localização e data
        # Baseado no conteúdo fornecido:
        # "Auxiliar de Estoque Bianchi Distribuidora Maringá - PR 19/06/2026"
        # ou "Bianchi Distribuidora Auxiliar de Estoque Maringá - PR 19/06/2026"
        
        # Vamos usar regex para encontrar padrões de vaga
        # Padrão: Texto com cidade - PR e data
        pattern = r'(.*?)\s*([A-Za-zÀ-ú\s\.]+)\s*([A-Za-zÀ-ú]+\s*-\s*[A-Z]{2})\s*(\d{2}/\d{2}/\d{4})'
        
        matches = re.findall(pattern, text)
        
        for match in matches:
            # match: (titulo_ou_empresa, empresa_ou_titulo, localizacao, data)
            # Precisamos determinar qual é o título e qual é a empresa
            # Normalmente, o título é mais curto ou contém palavras-chave
            part1, part2, localizacao, data = match
            
            # Determina qual é o título e qual é a empresa
            # Palavras comuns em títulos de vaga
            titulo_keywords = ['auxiliar', 'vendedor', 'analista', 'operador', 'consultor', 'estoquista', 
                              'assistente', 'coordenador', 'gerente', 'técnico', 'zelador', 'balconista']
            
            titulo = ""
            empresa = ""
            
            # Verifica se part1 parece ser título ou empresa
            if any(keyword in part1.lower() for keyword in titulo_keywords):
                titulo = part1.strip()
                empresa = part2.strip()
            elif any(keyword in part2.lower() for keyword in titulo_keywords):
                titulo = part2.strip()
                empresa = part1.strip()
            else:
                # Se não conseguir determinar, assume que o primeiro é título
                titulo = part1.strip()
                empresa = part2.strip() if part2 else "N/A"
            
            # Extrai cidade e estado
            cidade = "N/A"
            estado = "N/A"
            if ' - ' in localizacao:
                partes = localizacao.split(' - ')
                if len(partes) == 2:
                    cidade = partes[0].strip()
                    estado = partes[1].strip()
            
            if titulo or empresa:
                vagas.append({
                    'titulo': titulo if titulo else "N/A",
                    'empresa': empresa if empresa else "N/A",
                    'cidade': cidade,
                    'estado': estado,
                    'localizacao': localizacao,
                    'data_publicacao': data
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
            # Remove duplicatas baseado no título + empresa + localização
            df = df.drop_duplicates(subset=['titulo', 'empresa', 'localizacao'])
            return df
        else:
            return pd.DataFrame()
