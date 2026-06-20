import streamlit as st
import pandas as pd
from scraper import EmpregosMaringaScraper
import time

def main():
    st.set_page_config(
        page_title="Web Scraping - Vagas Maringá",
        page_icon="💼",
        layout="wide"
    )
    
    st.title("💼 Extrator de Vagas - Empregos Maringá")
    st.markdown("""
    Este aplicativo extrai informações de vagas de emprego do site [empregos.maringa.com](https://empregos.maringa.com/)
    """)
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        max_pages = st.slider(
            "Número de páginas para extrair",
            min_value=1,
            max_value=10,
            value=5,
            help="Quantas páginas de resultados serão extraídas"
        )
        
        extract_button = st.button(
            "🚀 Iniciar Extração",
            type="primary",
            use_container_width=True
        )
        
        st.divider()
        st.caption("Desenvolvido com ❤️ usando Streamlit")
    
    # Área principal
    if extract_button:
        with st.spinner("Extraindo dados... Isso pode levar alguns segundos."):
            scraper = EmpregosMaringaScraper()
            
            # Cria um placeholder para o progresso
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Extrai os dados
            start_time = time.time()
            
            # Simula o progresso
            progress_bar = st.progress(0)
            
            # Extrai os dados usando o scraper
            df = scraper.scrape_all_pages(max_pages)
            
            progress_bar.progress(100)
            end_time = time.time()
            
            if not df.empty:
                # Exibe estatísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Vagas Extraídas", len(df))
                with col2:
                    st.metric("Páginas Processadas", max_pages)
                with col3:
                    st.metric("Tempo de Execução", f"{end_time - start_time:.2f}s")
                
                # Exibe os dados
                st.subheader("📊 Dados Extraídos")
                
                # Opção para baixar os dados
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Baixar dados em CSV",
                    data=csv,
                    file_name=f"vagas_maringa_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Exibe a tabela
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "titulo": st.column_config.TextColumn("Título da Vaga"),
                        "empresa": st.column_config.TextColumn("Empresa"),
                        "cidade": st.column_config.TextColumn("Cidade"),
                        "estado": st.column_config.TextColumn("Estado"),
                        "localizacao": st.column_config.TextColumn("Localização Completa"),
                        "data_publicacao": st.column_config.TextColumn("Data de Publicação"),
                    }
                )
                
                # Exibe algumas estatísticas adicionais
                st.subheader("📈 Estatísticas")
                col1, col2 = st.columns(2)
                
                with col1:
                    # Top 5 cidades com mais vagas
                    top_cities = df['cidade'].value_counts().head(5)
                    st.bar_chart(top_cities)
                    st.caption("Top 5 cidades com mais vagas")
                
                with col2:
                    # Top 5 empresas com mais vagas
                    top_companies = df['empresa'].value_counts().head(5)
                    st.bar_chart(top_companies)
                    st.caption("Top 5 empresas com mais vagas")
                
            else:
                st.error("❌ Não foi possível extrair dados. Verifique a estrutura do site ou tente novamente.")
    
    # Exibe informações iniciais
    else:
        st.info("👆 Clique no botão 'Iniciar Extração' na barra lateral para começar.")
        
        # Exibe um exemplo do que será extraído
        st.subheader("📋 Exemplo dos dados a serem extraídos")
        
        exemplo_data = {
            "Título da Vaga": ["Auxiliar de Estoque", "Corretor de Imóveis", "Balconista"],
            "Empresa": ["Bianchi Distribuidora", "Ferallyn Imoveis", "Holandesa Padaria"],
            "Cidade": ["Maringá", "Maringá", "Maringá"],
            "Estado": ["PR", "PR", "PR"],
            "Localização Completa": ["Maringá - PR", "Maringá - PR", "Maringá - PR"],
            "Data de Publicação": ["19/06/2026", "16/06/2026", "16/06/2026"]
        }
        
        st.dataframe(
            pd.DataFrame(exemplo_data),
            use_container_width=True,
            hide_index=True
        )

if __name__ == "__main__":
    main()
