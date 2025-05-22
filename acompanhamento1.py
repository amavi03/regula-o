import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import requests
from urllib3.exceptions import MaxRetryError, NewConnectionError
import os
import io

# Configuração da página
st.set_page_config(layout="wide", page_title="Agenda de Consultas", page_icon="🗕️")

# --- ESTILO CSS PERSONALIZADO ---
# (Mantenha seu CSS existente)

def safe_split(text, separator=None, maxsplit=-1):
    """Versão segura do split que trata None e outros casos"""
    if text is None:
        return []
    try:
        return str(text).split(separator, maxsplit)
    except:
        return []

def testar_conexao():
    try:
        response = requests.get("https://itabira-mg.vivver.com", timeout=10)
        if response.status_code == 200:
            return "success", "✅ Conexão com o site estabelecida com sucesso!"
        else:
            return "warning", f"⚠️ O site respondeu com status {response.status_code}"
    except (requests.exceptions.Timeout, MaxRetryError, NewConnectionError):
        return "error", "❌ Falha na conexão. Verifique sua internet ou firewall."
    except Exception as e:
        return "error", f"❌ Erro inesperado: {str(e)}"

@st.cache_data(ttl=36000)
def carregar_dados_reais(debug_mode=False):
    max_tentativas = 3
    tentativa = 0
    
    while tentativa < max_tentativas:
        try:
            session = requests.Session()
            
            # Credenciais
            username = os.getenv('VIVVER_USER', '123')
            password = os.getenv('VIVVER_PASS', '38355212')
            
            # Primeira requisição para obter cookies
            session.get("https://itabira-mg.vivver.com/login", timeout=10)
            
            # Dados do formulário de login
            login_data = {
                'conta': username,
                'password': password,
                'remember': 'on'
            }
            
            # Enviar login
            response = session.post(
                "https://itabira-mg.vivver.com/login",
                data=login_data,
                timeout=30,
                allow_redirects=True
            )
            
            # Verificar se o login foi bem-sucedido
            if "login" in response.url:
                raise ValueError("Falha no login - credenciais incorretas")
            
            # Acessar a API diretamente
            url_api = "https://itabira-mg.vivver.com/bit/gadget/view_paginate.json?id=228&draw=1&start=0&length=10000"
            response = session.get(url_api, timeout=30)
            response.raise_for_status()
            
            # Processar resposta
            try:
                dados = response.json()
                if not dados or not isinstance(dados, dict):
                    raise ValueError("Resposta da API inválida")
                
                return dados
            except json.JSONDecodeError:
                # Tentar extrair JSON de resposta malformada
                start = response.text.find('{')
                end = response.text.rfind('}') + 1
                if start != -1 and end != 0:
                    try:
                        return json.loads(response.text[start:end])
                    except:
                        pass
                raise ValueError("Não foi possível decodificar a resposta da API")
            
        except Exception as e:
            tentativa += 1
            if tentativa >= max_tentativas:
                error_msg = f"Falha na tentativa {tentativa}: {str(e)}"
                if debug_mode:
                    st.error(error_msg)
                    if 'response' in locals():
                        st.text("Conteúdo da resposta:")
                        st.text(response.text[:1000])
                raise Exception(error_msg)
            time.sleep(2)

def processar_dados(dados):
    try:
        if not dados or not isinstance(dados, dict):
            return pd.DataFrame()
        
        # Extrair dados de forma segura
        dados_lista = dados.get('data', [])
        if not isinstance(dados_lista, list):
            return pd.DataFrame()
        
        # Verificar estrutura mínima
        if len(dados_lista) == 0 or len(dados_lista[0]) < 10:
            return pd.DataFrame()
        
        # Criar DataFrame com colunas dinâmicas
        colunas = [
            "DT_RowId", "Unidade", "Especialidade", "Profissional", "Serviço",
            "Origem", "Tipo", "Hora", "Agenda direta", "Data"
        ]
        
        df = pd.DataFrame(dados_lista)
        
        # Atribuir nomes às colunas disponíveis
        if len(df.columns) >= len(colunas):
            df.columns = colunas[:len(df.columns)]
            df = df.drop(columns=["DT_RowId"], errors='ignore')
        else:
            df.columns = colunas[:len(df.columns)]
        
        # Processar datas
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return pd.DataFrame()

# (Mantenha as outras funções como mostrar_calendario_mensal, gerar_excel, etc)

def main():
    st.title("📅 Acompanhamento de Vagas")

    # Configuração de debug
    debug_mode = st.sidebar.checkbox("🔍 Modo de Depuração", value=False)
    
    # Seção de diagnóstico
    with st.sidebar.expander("🔧 Diagnóstico do Sistema", expanded=False):
        if st.button("🧪 Testar Conexão com Vivver"):
            with st.spinner("Testando conexão..."):
                status, mensagem = testar_conexao()
                st.markdown(f"""
                <div class='connection-test connection-{status}'>
                    {mensagem}
                </div>
                """, unsafe_allow_html=True)

    # Carregar dados
    with st.spinner("Carregando dados..."):
        try:
            dados = carregar_dados_reais(debug_mode)
            df = processar_dados(dados)
            
            if df.empty:
                st.error("""
                Não foi possível carregar dados válidos. Possíveis causas:
                1. Problema de autenticação
                2. Mudança na estrutura da API
                3. Limitações do servidor
                """)
                if debug_mode:
                    st.json(dados)
                return
                
            # (Continue com o resto da sua lógica de exibição)
            
        except Exception as e:
            st.error(f"Falha crítica: {str(e)}")
            if debug_mode:
                st.exception(e)

if __name__ == "__main__":
    main()
