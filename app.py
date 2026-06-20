import streamlit as st
import pandas as pd
from scraper import EmpregosMaringaScraper
from utils import extract_city_state, clean_date, format_vaga_title
from csv_manager import CSVManager, create_csv_manager_widgets, save_current_dataframe
import time
import os

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
    
    # Inicializa o gerenciador de CSV
    csv_manager = CSVManager()
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        max_pages = st.slider(
            "Número de páginas para extrair",
            min_value=1,
            max_value=200,
            value=50,
            help="Quantas páginas de resultados serão extraídas"
        )
        
        extract_button = st.button(
            "🚀 Iniciar Extração",
            type="primary",
            use_container_width=True
        )
        
        st.divider()
        
        # Widgets de gerenciamento de CSV
        create_csv_manager_widgets()
        
        # Botão para salvar os dados atuais manualmente
        if st.session_state['df'] is not None and not st.session_state['df'].empty:
            st.divider()
            st.subheader("💾 Salvar dados atuais")
            if st.button("💾 Salvar CSV atual", use_container_width=True):
                success, message = save_current_dataframe(st.session_state['df'])
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        st.divider()
        st.caption("Desenvolvido com ❤️ usando Streamlit")
    
    # Área principal
    if extract_button:
        # Container para status e progresso
        status_container = st.container()
        
        with status_container:
            st.subheader("📊 Status da Extração")
            
            # Apenas barra de progresso e texto de status
            progress_bar = st.progress(0)
            status_text = st.empty()
            vaga_count_text = st.empty()
            
            # Função de callback para atualizar o progresso
            def update_progress(current_page, total_pages, message):
                progress = current_page / total_pages
                progress_bar.progress(min(progress, 1.0))
                status_text.info(f"📌 {message}")
                
                # Atualiza contagem de vagas
                if hasattr(scraper, 'total_vagas'):
                    vaga_count_text.info(f"📊 Total de vagas encontradas: {scraper.total_vagas}")
            
            try:
                with st.spinner("🚀 Iniciando extração de dados..."):
                    scraper = EmpregosMaringaScraper()
                    start_time = time.time()
                    
                    # Extrai os dados
                    df = scraper.scrape_all_pages(
                        max_pages=max_pages,
                        progress_callback=update_progress
                    )
                    
                    end_time = time.time()
                    
                    # Limpa os elementos de progresso
                    progress_bar.empty()
                    status_text.empty()
                    vaga_count_text.empty()
                    
                    if not df.empty:
                        # Processa os dados com as funções utils
                        if 'empresa' in df.columns:
                            df['empresa'] = df['empresa'].apply(format_vaga_title)
                        if 'cidade' in df.columns:
                            df['cidade'] = df['cidade'].apply(format_vaga_title)
                        if 'data_publicacao' in df.columns:
                            df['data_publicacao'] = df['data_publicacao'].apply(clean_date)
                        
                        # Reordena as colunas
                        column_order = ['empresa', 'cidade', 'estado', 'data_publicacao', 'url', 'titulo']
                        available_columns = [col for col in column_order if col in df.columns]
                        df = df[available_columns]
                        
                        # Salva no estado da sessão
                        st.session_state['df'] = df
                        
                        # Salva automaticamente em CSV usando o gerenciador
                        success, message = csv_manager.save_dataframe(df)
                        if success:
                            st.success(message)
                        else:
                            st.warning(message)
                        
                        # Exibe estatísticas finais
                        st.success("✅ Extração concluída com sucesso!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total de Vagas", len(df))
                        with col2:
                            st.metric("Páginas Processadas", max_pages)
                        with col3:
                            st.metric("Tempo de Execução", f"{end_time - start_time:.2f}s")
                        with col4:
                            empresas_unicas = df['empresa'].nunique() if 'empresa' in df.columns else 0
                            st.metric("Empresas Únicas", empresas_unicas)
                        
                        # Exibe os dados
                        st.subheader("📊 Dados Extraídos")
                        
                        # Botão para download
                        csv_data, filename = csv_manager.get_download_data(df)
                        st.download_button(
                            label="📥 Baixar dados em CSV",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Exibe a tabela
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "empresa": st.column_config.TextColumn("Empresa"),
                                "cidade": st.column_config.TextColumn("Cidade"),
                                "estado": st.column_config.TextColumn("Estado"),
                                "data_publicacao": st.column_config.TextColumn("Data de Publicação"),
                                "url": st.column_config.LinkColumn("URL da Vaga"),
                                "titulo": st.column_config.TextColumn("Título da Vaga"),
                            }
                        )
                        
                        # Exibe estatísticas adicionais
                        if 'cidade' in df.columns and 'empresa' in df.columns:
                            st.subheader("📈 Estatísticas")
                            
                            col_est1, col_est2 = st.columns(2)
                            
                            with col_est1:
                                top_cities = df['cidade'].value_counts().head(10)
                                st.bar_chart(top_cities)
                                st.caption("Top 10 cidades com mais vagas")
                            
                            with col_est2:
                                top_companies = df['empresa'].value_counts().head(10)
                                st.bar_chart(top_companies)
                                st.caption("Top 10 empresas com mais vagas")
                        
                    else:
                        st.error("❌ Não foi possível extrair dados. Verifique a estrutura do site ou tente novamente.")
                        
            except Exception as e:
                st.error(f"❌ Ocorreu um erro durante a extração: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Exibe informações iniciais ou dados carregados
    else:
        # Verifica se há dados carregados ou se já foram extraídos anteriormente
        if st.session_state['df'] is not None and not st.session_state['df'].empty:
            df = st.session_state['df']
            st.success(f"✅ Dados carregados com sucesso! Total: {len(df)} vagas")
            
            # Mostra informações resumidas
            st.subheader("📊 Resumo dos Dados Carregados")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Vagas", len(df))
            with col2:
                empresas_unicas = df['empresa'].nunique() if 'empresa' in df.columns else 0
                st.metric("Empresas Únicas", empresas_unicas)
            with col3:
                cidades_unicas = df['cidade'].nunique() if 'cidade' in df.columns else 0
                st.metric("Cidades Representadas", cidades_unicas)
            
            # Exibe os dados
            st.subheader("📊 Dados Carregados")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # Botão para download dos dados carregados
            csv_data, filename = csv_manager.get_download_data(df)
            st.download_button(
                label="📥 Baixar dados em CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
        
        elif st.session_state['loaded_df'] is not None and not st.session_state['loaded_df'].empty:
            # Fallback para compatibilidade
            df = st.session_state['loaded_df']
            st.success(f"✅ Dados carregados com sucesso! Total: {len(df)} vagas")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        
        else:
            st.info("👆 Clique no botão 'Iniciar Extração' na barra lateral para começar ou use o gerenciador de CSV para carregar dados existentes.")
            
            # Exibe um exemplo do que será extraído
            st.subheader("📋 Exemplo dos dados a serem extraídos")
            
            exemplo_data = {
                "Empresa": ["Bianchi Distribuidora", "Ferallyn Imoveis", "Holandesa Padaria"],
                "Cidade": ["Maringá", "Maringá", "Maringá"],
                "Estado": ["PR", "PR", "PR"],
                "Data de Publicação": ["19/06/2026", "16/06/2026", "16/06/2026"],
                "URL": [
                    "https://empregos.maringa.com/vaga/123",
                    "https://empregos.maringa.com/vaga/456",
                    "https://empregos.maringa.com/vaga/789"
                ],
                "Título": ["Vaga 1", "Vaga 2", "Vaga 3"]
            }
            
            st.dataframe(
                pd.DataFrame(exemplo_data),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("""
            ### 📌 Sobre a Extração
            
            - **Total de páginas:** Até 200 páginas
            - **Colunas extraídas:** Empresa, Cidade, Estado, Data de Publicação, URL, Título
            - **Formato de saída:** CSV com codificação UTF-8
            - **Tempo estimado:** Aproximadamente 2-5 minutos para 100 páginas
            - **Arquivo salvo automaticamente:** `vagas_extraidas.csv`
            
            A barra de progresso mostrará o andamento da extração em tempo real.
            """)

if __name__ == "__main__":
    main()
