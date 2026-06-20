"""
Módulo para gerenciar operações com arquivos CSV
"""
import pandas as pd
import os
from typing import Optional, Tuple
import streamlit as st

class CSVManager:
    """
    Classe para gerenciar operações de leitura e escrita de arquivos CSV
    """
    
    DEFAULT_FILENAME = 'vagas_extraidas.csv'
    
    def __init__(self, filename: str = DEFAULT_FILENAME):
        """
        Inicializa o gerenciador de CSV
        
        Args:
            filename: Nome do arquivo CSV
        """
        self.filename = filename
    
    def save_dataframe(self, df: pd.DataFrame, filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Salva um DataFrame em arquivo CSV
        
        Args:
            df: DataFrame a ser salvo
            filename: Nome do arquivo (opcional)
            
        Returns:
            Tuple[bool, str]: (Sucesso, Mensagem)
        """
        try:
            if df is None or df.empty:
                return False, "❌ DataFrame vazio. Nada para salvar."
            
            save_file = filename or self.filename
            
            # Salva o arquivo com encoding UTF-8
            df.to_csv(save_file, index=False, encoding='utf-8-sig')
            
            return True, f"✅ Dados salvos com sucesso em '{save_file}'!"
            
        except Exception as e:
            return False, f"❌ Erro ao salvar arquivo: {str(e)}"
    
    def load_dataframe(self, filename: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Carrega um DataFrame de um arquivo CSV
        
        Args:
            filename: Nome do arquivo (opcional)
            
        Returns:
            Tuple[Optional[pd.DataFrame], str]: (DataFrame, Mensagem)
        """
        try:
            load_file = filename or self.filename
            
            if not os.path.exists(load_file):
                return None, f"❌ Arquivo '{load_file}' não encontrado."
            
            df = pd.read_csv(load_file)
            
            if df.empty:
                return None, f"⚠️ Arquivo '{load_file}' está vazio."
            
            return df, f"✅ Carregadas {len(df)} vagas do arquivo '{load_file}'!"
            
        except Exception as e:
            return None, f"❌ Erro ao carregar arquivo: {str(e)}"
    
    def file_exists(self, filename: Optional[str] = None) -> bool:
        """
        Verifica se o arquivo CSV existe
        
        Args:
            filename: Nome do arquivo (opcional)
            
        Returns:
            bool: True se o arquivo existe
        """
        check_file = filename or self.filename
        return os.path.exists(check_file)
    
    def get_file_info(self, filename: Optional[str] = None) -> dict:
        """
        Obtém informações sobre o arquivo CSV
        
        Args:
            filename: Nome do arquivo (opcional)
            
        Returns:
            dict: Informações do arquivo
        """
        check_file = filename or self.filename
        
        if not os.path.exists(check_file):
            return {
                'exists': False,
                'size': 0,
                'modified': None,
                'rows': 0
            }
        
        try:
            df = pd.read_csv(check_file)
            stats = os.stat(check_file)
            
            return {
                'exists': True,
                'size': stats.st_size,
                'modified': stats.st_mtime,
                'rows': len(df),
                'columns': list(df.columns)
            }
        except:
            return {
                'exists': True,
                'size': os.path.getsize(check_file),
                'modified': os.path.getmtime(check_file),
                'rows': 0,
                'columns': []
            }
    
    def delete_file(self, filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deleta o arquivo CSV
        
        Args:
            filename: Nome do arquivo (opcional)
            
        Returns:
            Tuple[bool, str]: (Sucesso, Mensagem)
        """
        try:
            delete_file = filename or self.filename
            
            if not os.path.exists(delete_file):
                return False, f"❌ Arquivo '{delete_file}' não encontrado."
            
            os.remove(delete_file)
            return True, f"✅ Arquivo '{delete_file}' deletado com sucesso!"
            
        except Exception as e:
            return False, f"❌ Erro ao deletar arquivo: {str(e)}"
    
    def get_download_data(self, df: pd.DataFrame) -> Tuple[str, str]:
        """
        Prepara os dados para download
        
        Args:
            df: DataFrame a ser baixado
            
        Returns:
            Tuple[str, str]: (Dados CSV, Nome do arquivo)
        """
        if df is None or df.empty:
            return "", "dados_vazios.csv"
        
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        filename = f"vagas_maringa_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return csv_data, filename


def create_csv_manager_widgets():
    """
    Cria widgets para gerenciamento de CSV no Streamlit
    Retorna os widgets e o estado atual
    """
    # Inicializa o gerenciador
    csv_manager = CSVManager()
    
    st.subheader("📂 Gerenciamento de CSV")
    
    # Verifica se o arquivo existe
    file_exists = csv_manager.file_exists()
    
    if file_exists:
        # Obtém informações do arquivo
        info = csv_manager.get_file_info()
        
        st.info(f"📄 Arquivo: **{csv_manager.filename}**")
        st.write(f"📊 Linhas: {info['rows']}")
        st.write(f"📏 Tamanho: {info['size'] / 1024:.2f} KB")
        st.write(f"📋 Colunas: {', '.join(info['columns']) if info['columns'] else 'N/A'}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Carregar CSV salvo", use_container_width=True):
                df, message = csv_manager.load_dataframe()
                if df is not None:
                    st.session_state['loaded_df'] = df
                    st.session_state['df'] = df
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            if st.button("🗑️ Deletar CSV", use_container_width=True):
                success, message = csv_manager.delete_file()
                if success:
                    st.success(message)
                    # Limpa os dados do estado
                    if 'loaded_df' in st.session_state:
                        st.session_state['loaded_df'] = None
                    if 'df' in st.session_state:
                        st.session_state['df'] = None
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info("ℹ️ Nenhum arquivo CSV encontrado. Execute uma extração primeiro.")
    
    return csv_manager


def save_current_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Função auxiliar para salvar o DataFrame atual
    
    Args:
        df: DataFrame a ser salvo
        
    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    csv_manager = CSVManager()
    return csv_manager.save_dataframe(df)


def load_dataframe_from_file(filename: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Função auxiliar para carregar DataFrame de um arquivo
    
    Args:
        filename: Nome do arquivo (opcional)
        
    Returns:
        Tuple[Optional[pd.DataFrame], str]: (DataFrame, Mensagem)
    """
    csv_manager = CSVManager(filename)
    return csv_manager.load_dataframe()


def get_csv_download(df: pd.DataFrame) -> Tuple[str, str]:
    """
    Função auxiliar para obter dados para download
    
    Args:
        df: DataFrame a ser baixado
        
    Returns:
        Tuple[str, str]: (Dados CSV, Nome do arquivo)
    """
    csv_manager = CSVManager()
    return csv_manager.get_download_data(df)
