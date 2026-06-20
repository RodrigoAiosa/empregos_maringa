import streamlit as st
import pandas as pd
from scraper_optimized import EmpregosMaringaScraperOptimized
import time

def main():
    st.set_page_config(
        page_title="Web Scraping - Vagas Maringá (Otimizado)",
        page_icon="⚡",
        layout="wide"
    )
    
    st.title("⚡ Extrator de Vagas - Empregos Maringá (Versão Otimizada)")
    st.markdown("""
    Versão otimizada com **multithreading** para extração mais rápida!
    """)
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        max_pages = st.slider(
            "Número de páginas para extrair",
            min_value=1,
            max_value=100,
            value=91,
            help="Quantas páginas de resultados serão extraídas"
        )
        
        max_workers = st.slider(
            "Número de workers (threads)",
            min_value=1,
            max_value=20,
            value=10,
            help="Mais workers = extração mais rápida, mas pode sobrecarregar o servidor"
        )
        
        use_cache = st.checkbox(
            "Usar cache",
            value=True,
            help="Armazena resultados em cache para acelerar próximas execuções"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            extract_button = st.button(
                "🚀 Iniciar Extração",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            clear_cache_button = st.button(
                "🗑️ Limpar Cache",
                use_container_width=True
            )
        
        if clear_cache_button:
            scraper = EmpregosMaringaScraperOptimized()
            scraper.clear_cache()
            st.success("Cache limpo com sucesso!")
        
        st.divider()
        st.caption("Desenvolvido com ❤️ usando Streamlit")
        
        # Mostra informações de performance
        st.info("""
        **💡 Dicas de Performance:**
        - 10 workers: ~1-2 minutos para 91 páginas
        - 20 workers: ~30-60 segundos
        - Use cache para re-extrações rápidas
        """)
    
    # Área principal
    if extract_button:
        # Container para status e progresso
        status_container = st.container()
        
        with status_container:
            st.subheader("📊 Status da Extração")
            
            # Cria colunas para métricas
            col_status1, col_status2, col_status3, col_status4 = st.columns(4)
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            # Métricas de performance
            start_time = time.time()
            pages_processed = 0
            total_vagas_encontradas = 0
            
            # Função de callback para atualizar o progresso
            def update_progress(current_page, total_pages, message):
                nonlocal pages_processed, total_vagas_encontradas
                
                progress = current_page / total_pages if total_pages > 0 else 0
                progress_bar.progress(min(progress, 1.0))
                
                # Atualiza métricas
                with col_status1:
                    st.metric("Páginas Processadas", f"{current_page}/{total_pages}")
                with col_status2:
                    st.metric("Progresso", f"{int(progress * 100)}%")
                with col_status3:
                    # Extrai número de vagas da mensagem
                    import re
                    match = re.search(r'Total: (\d+)', message)
                    if match:
                        total_vagas_encontradas = int(match.group(1))
                    st.metric("Vagas Encontradas", total_vagas_encontradas)
                with col_status4:
                    elapsed = time.time() - start_time
                    st.metric("Tempo Decorrido", f"{elapsed:.1f}s")
                
                status_text.info(f"📌 {message}")
                
                # Força o update da interface
                st.session_state.update_progress = True
            
            try:
                with st.spinner("🚀 Iniciando extração otimizada..."):
                    # Cria scraper otimizado
                    scraper = EmpregosMaringaScraperOptimized(
                        max_workers=max_workers,
                        use_cache=use_cache
                    )
                    
                    # Extrai os dados
                    df = scraper.scrape_all_pages(
                        max_pages=max_pages,
                        progress_callback=update_progress
                    )
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    if not df.empty:
                        # Reordena as colunas
                        column_order = ['empresa', 'cidade', 'estado', 'data_publicacao', 'url']
                        df = df[column_order]
                        
                        # Exibe estatísticas finais
                        st.success(f"✅ Extração concluída em {total_time:.1f} segundos!")
                        
                        # Comparação de performance
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            st.metric("Total de Vagas", len(df))
                        with col2:
                            st.metric("Páginas Processadas", max_pages)
                        with col3:
                            st.metric("Tempo Total", f"{total_time:.1f}s")
                        with col4:
                            st.metric("Velocidade", f"{max_pages/total_time:.1f} páginas/s")
                        with col5:
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
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### ⚡ Otimizações Implementadas
            
            1. **Multithreading** - 10+ workers paralelos
            2. **Cache** - Armazena resultados
            3. **Session Reuse** - Conexões persistentes
            4. **Parsing Otimizado** - BeautifulSoup + lxml
            5. **Sem delays** - Downloads simultâneos
            """)
        
        with col2:
            st.markdown("""
            ### 📊 Performance Esperada
            
            - **91 páginas**: 30-90 segundos
            - **Cache ativo**: 5-10 segundos
            - **Economia**: ~95% do tempo
            - **Workers**: Ajustável de 1 a 20
            """)
        
        st.info("""
        **💡 Comparação de Performance:**
        - Versão original (sequencial): ~3-5 minutos
        - Versão otimizada (10 workers): ~45-90 segundos
        - Versão otimizada (20 workers): ~30-60 segundos
        - Com cache: ~5-10 segundos (re-extração)
        """)

if __name__ == "__main__":
    main()
