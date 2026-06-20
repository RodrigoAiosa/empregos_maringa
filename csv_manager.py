"""
Módulo para gerenciar operações com arquivos CSV
"""
import pandas as pd
import os
from typing import Optional, Tuple

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
        """
        try:
            if df is None or df.empty:
                return False, "❌ DataFrame vazio. Nada para salvar."
            
            save_file = filename or self.filename
            df.to_csv(save_file, index=False, encoding='utf-8-sig')
            
            return True, f"✅ Dados salvos com sucesso em '{save_file}'!"
            
        except Exception as e:
            return False, f"❌ Erro ao salvar arquivo: {str(e)}"
    
    def load_dataframe(self, filename: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Carrega um DataFrame de um arquivo CSV
        """
        try:
            load_file = filename or self.filename
            
            if not os.path.exists(load_file):
                return None, f"❌ Arquivo '{load_file}' não encontrado."
            
            df = pd.read_csv(load_file)
            
            if df.empty:
                return None, f"⚠️ Arquivo '{load_file}' está vazio."
            
            return df, f"✅ Carregadas {len(df)} vagas!"
            
        except Exception as e:
            return None, f"❌ Erro ao carregar arquivo: {str(e)}"
    
    def file_exists(self, filename: Optional[str] = None) -> bool:
        """Verifica se o arquivo CSV existe"""
        check_file = filename or self.filename
        return os.path.exists(check_file)
    
    def delete_file(self, filename: Optional[str] = None) -> Tuple[bool, str]:
        """Deleta o arquivo CSV"""
        try:
            delete_file = filename or self.filename
            
            if not os.path.exists(delete_file):
                return False, f"❌ Arquivo '{delete_file}' não encontrado."
            
            os.remove(delete_file)
            return True, f"✅ Arquivo deletado com sucesso!"
            
        except Exception as e:
            return False, f"❌ Erro ao deletar arquivo: {str(e)}"
    
    def get_download_data(self, df: pd.DataFrame) -> Tuple[str, str]:
        """Prepara os dados para download"""
        if df is None or df.empty:
            return "", "dados_vazios.csv"
        
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        filename = f"vagas_maringa_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return csv_data, filename


def create_csv_manager_widgets():
    """
    Cria widgets simplificados para gerenciamento de CSV no Streamlit
    """
    csv_manager = CSVManager()
    file_exists = csv_manager.file_exists()
    
    if file_exists:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Carregar CSV salvo", use_container_width=True):
                df, message = csv_manager.load_dataframe()
                if df is not None:
                    # Remove coluna título se existir
                    if 'título' in df.columns:
                        df = df.drop('título', axis=1)
                    if 'titulo' in df.columns:
                        df = df.drop('titulo', axis=1)
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
                    if 'loaded_df' in st.session_state:
                        st.session_state['loaded_df'] = None
                    if 'df' in st.session_state:
                        st.session_state['df'] = None
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info("ℹ️ Nenhum arquivo CSV encontrado.")
    
    return csv_manager


def save_current_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """Função auxiliar para salvar o DataFrame atual"""
    csv_manager = CSVManager()
    return csv_manager.save_dataframe(df)


# Import necessário para os widgets
import streamlit as st
