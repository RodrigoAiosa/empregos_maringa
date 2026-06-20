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
            max_value=100,
            value=91,
            help="Quantas páginas de resultados serão extraídas (máximo 100)"
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
        # Container para status e progresso
        status_container = st.container()
        
        with status_container:
            st.subheader("📊 Status da Extração")
            
            # Cria colunas para métricas
            col_status1, col_status2, col_status3 = st.columns(3)
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            # Função de callback para atualizar o progresso
            def update_progress(current_page, total_pages, message):
                progress = current_page / total_pages
                progress_bar.progress(min(progress, 1.0))
                
                with col_status1:
                    st.metric("Página Atual", f"{current_page}/{total_pages}")
                with col_status2:
                    st.metric("Progresso", f"{int(progress * 100)}%")
                
                status_text.info(f"📌 {message}")
                
                # Força o update da interface
                st.session_state.update_progress = True
            
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
                    
                    if not df.empty:
                        # Reordena as colunas
                        column_order = ['empresa', 'cidade', 'estado', 'data_publicacao', 'url']
                        df = df[column_order]
                        
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
                            st.metric("Média por Página", f"{len(df)/max_pages:.1f}")
                        
                        # Exibe os dados
                        st.subheader("📊 Dados Extraídos")
                        
                        # Opção para baixar os dados
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
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
                                "empresa": st.column_config.TextColumn("Empresa"),
                                "cidade": st.column_config.TextColumn("Cidade"),
                                "estado": st.column_config.TextColumn("Estado"),
                                "data_publicacao": st.column_config.TextColumn("Data de Publicação"),
                                "url": st.column_config.LinkColumn("URL da Vaga"),
                            }
                        )
                        
                        # Exibe estatísticas adicionais
                        st.subheader("📈 Estatísticas")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            top_cities = df['cidade'].value_counts().head(5)
                            st.bar_chart(top_cities)
                            st.caption("Top 5 cidades com mais vagas")
                        
                        with col2:
                            top_companies = df['empresa'].value_counts().head(5)
                            st.bar_chart(top_companies)
                            st.caption("Top 5 empresas com mais vagas")
                        
                    else:
                        st.error("❌ Não foi possível extrair dados. Verifique a estrutura do site ou tente novamente.")
                        
            except Exception as e:
                st.error(f"❌ Ocorreu um erro durante a extração: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Exibe informações iniciais
    else:
        st.info("👆 Clique no botão 'Iniciar Extração' na barra lateral para começar.")
        
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
            ]
        }
        
        st.dataframe(
            pd.DataFrame(exemplo_data),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("""
        ### 📌 Sobre a Extração
        
        - **Total de páginas:** 91 páginas
        - **Colunas extraídas:** Empresa, Cidade, Estado, Data de Publicação, URL
        - **Formato de saída:** CSV com codificação UTF-8
        - **Tempo estimado:** Aproximadamente 3-5 minutos para 91 páginas
        
        A barra de progresso mostrará o andamento da extração em tempo real.
        """)

if __name__ == "__main__":
    main()
