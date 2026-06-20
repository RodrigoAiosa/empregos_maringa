import streamlit as st
import pandas as pd
from scraper import EmpregosMaringaScraper
from utils import extract_city_state, clean_date, format_vaga_title
from csv_manager import CSVManager, create_csv_manager_widgets, save_current_dataframe
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
    
    # Inicializa o estado da sessão
    if 'loaded_df' not in st.session_state:
        st.session_state['loaded_df'] = None
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    
    csv_manager = CSVManager()
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        max_pages = st.slider(
            "Número de páginas para extrair",
            min_value=1,
            max_value=200,
            value=100,
            help="Quantas páginas de resultados serão extraídas"
        )
        
        extract_button = st.button(
            "🚀 Iniciar Extração",
            type="primary",
            use_container_width=True
        )
        
        st.divider()
        
        # Widgets simplificados de gerenciamento de CSV
        create_csv_manager_widgets()
        
        # Botão para salvar os dados atuais
        if st.session_state['df'] is not None and not st.session_state['df'].empty:
            st.divider()
            if st.button("💾 Salvar CSV", use_container_width=True):
                success, message = save_current_dataframe(st.session_state['df'])
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        st.divider()
        st.caption("Desenvolvido com ❤️ usando Streamlit")
    
    # Área principal
    if extract_button:
        status_container = st.container()
        
        with status_container:
            st.subheader("📊 Status da Extração")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            vaga_count_text = st.empty()
            
            def update_progress(current_page, total_pages, message):
                progress = current_page / total_pages
                progress_bar.progress(min(progress, 1.0))
                status_text.info(f"📌 {message}")
                
                if hasattr(scraper, 'total_vagas'):
                    vaga_count_text.info(f"📊 Total de vagas: {scraper.total_vagas}")
            
            try:
                with st.spinner("🚀 Iniciando extração..."):
                    scraper = EmpregosMaringaScraper()
                    start_time = time.time()
                    
                    df = scraper.scrape_all_pages(
                        max_pages=max_pages,
                        progress_callback=update_progress
                    )
                    
                    end_time = time.time()
                    
                    progress_bar.empty()
                    status_text.empty()
                    vaga_count_text.empty()
                    
                    if not df.empty:
                        # Remove coluna título se existir
                        if 'título' in df.columns:
                            df = df.drop('título', axis=1)
                        if 'titulo' in df.columns:
                            df = df.drop('titulo', axis=1)
                        
                        st.session_state['df'] = df
                        csv_manager.save_dataframe(df)
                        
                        st.success(f"✅ Extração concluída! {len(df)} vagas encontradas.")
                        
                        # Métricas
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total de Vagas", len(df))
                        with col2:
                            st.metric("Páginas Processadas", scraper.pagina_atual)
                        with col3:
                            st.metric("Tempo", f"{end_time - start_time:.1f}s")
                        with col4:
                            empresas_unicas = df['empresa'].nunique() if 'empresa' in df.columns else 0
                            st.metric("Empresas", empresas_unicas)
                        
                        # Dados
                        st.subheader("📊 Dados Extraídos")
                        
                        csv_data, filename = csv_manager.get_download_data(df)
                        st.download_button(
                            label="📥 Baixar CSV",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "empresa": st.column_config.TextColumn("Empresa"),
                                "cidade": st.column_config.TextColumn("Cidade"),
                                "estado": st.column_config.TextColumn("Estado"),
                                "data_publicacao": st.column_config.TextColumn("Data"),
                                "url": st.column_config.LinkColumn("URL"),
                            }
                        )
                        
                        # Estatísticas
                        if 'cidade' in df.columns and 'empresa' in df.columns:
                            st.subheader("📈 Estatísticas")
                            col_est1, col_est2 = st.columns(2)
                            
                            with col_est1:
                                top_cities = df['cidade'].value_counts().head(10)
                                st.bar_chart(top_cities)
                                st.caption("Top 10 cidades")
                            
                            with col_est2:
                                top_companies = df['empresa'].value_counts().head(10)
                                st.bar_chart(top_companies)
                                st.caption("Top 10 empresas")
                    else:
                        st.error("❌ Nenhuma vaga encontrada.")
                        
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    else:
        # Mostra dados carregados ou estado inicial
        if st.session_state['df'] is not None and not st.session_state['df'].empty:
            df = st.session_state['df']
            
            # Remove coluna título se existir
            if 'título' in df.columns:
                df = df.drop('título', axis=1)
            if 'titulo' in df.columns:
                df = df.drop('titulo', axis=1)
            
            st.success(f"✅ Dados carregados! {len(df)} vagas")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", len(df))
            with col2:
                empresas = df['empresa'].nunique() if 'empresa' in df.columns else 0
                st.metric("Empresas", empresas)
            with col3:
                cidades = df['cidade'].nunique() if 'cidade' in df.columns else 0
                st.metric("Cidades", cidades)
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.info("👆 Clique em 'Iniciar Extração' ou carregue um CSV salvo.")
            
            # Exemplo
            st.subheader("📋 Exemplo")
            exemplo = {
                "Empresa": ["Bianchi Distribuidora", "Ferallyn Imoveis"],
                "Cidade": ["Maringá", "Maringá"],
                "Estado": ["PR", "PR"],
                "Data": ["19/06/2026", "16/06/2026"],
                "URL": ["https://empregos.maringa.com/vaga/1", "https://empregos.maringa.com/vaga/2"]
            }
            st.dataframe(pd.DataFrame(exemplo), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
