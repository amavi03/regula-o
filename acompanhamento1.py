import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import io
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================
# CONFIGURAÇÕES INICIAIS (MODIFICAR AQUI)
# =============================================
VIVVER_USER = "123"       # <--- INSIRA SEU USUÁRIO AQUI
VIVVER_PASS = "123456"    # <--- INSIRA SUA SENHA AQUI
BASE_URL = "https://itabira-mg.vivver.com"

# =============================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================
st.set_page_config(layout="wide", page_title="Agenda de Consultas Vivver", page_icon="📅")

# =============================================
# ESTILOS CSS
# =============================================
st.markdown("""
<style>
    .calendar-day {
        border-radius: 5px;
        padding: 8px;
        min-height: 80px;
        margin: 2px;
        cursor: pointer;
    }
    .selected-day {
        border: 2px solid #FF4B4B !important;
    }
    .weekday-header {
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
    }
    .filter-active {
        background-color: #e6f7ff;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 4px solid #1890ff;
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# CONFIGURAÇÃO DE REQUESTS
# =============================================
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# =============================================
# FUNÇÕES PRINCIPAIS
# =============================================
def fazer_login():
    """Realiza login no sistema Vivver"""
    try:
        LOGIN_URL = urljoin(BASE_URL, "/login")
        
        # Primeira requisição para obter token CSRF
        login_page = session.get(LOGIN_URL, timeout=10)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # Extrair token CSRF
        csrf_token = soup.find('input', {'name': '_token'}).get('value', '')
        
        # Dados do login
        login_data = {
            'conta': VIVVER_USER,
            'password': VIVVER_PASS,
            '_token': csrf_token
        }
        
        # Fazer login
        response = session.post(LOGIN_URL, data=login_data, timeout=10)
        
        if "login" in response.url:
            return False, "Falha no login - Verifique as credenciais"
        return True, "Login realizado com sucesso"
        
    except Exception as e:
        return False, f"Erro durante o login: {str(e)}"

@st.cache_data(ttl=3600)
def carregar_dados():
    """Carrega os dados de agendamentos"""
    try:
        # Fazer login
        success, message = fazer_login()
        if not success:
            st.error(message)
            return None
        
        DATA_URL = urljoin(BASE_URL, "/bit/gadget/view_paginate.json?id=225&draw=1&start=0&length=10000")
        response = session.get(DATA_URL, timeout=10)
        
        if response.status_code != 200:
            st.error(f"Erro ao acessar dados: HTTP {response.status_code}")
            return None
            
        return response.json()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None

def processar_dados(dados):
    """Processa os dados brutos para DataFrame"""
    if not dados or "data" not in dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados["data"])
    df.columns = [
        "ID", "Unidade", "Especialidade", "Profissional", "Serviço",
        "Origem", "Tipo", "Hora", "Agenda", "Data",
        "Data_Cadastro", "Prof_Cadastro", "Tipo_Servico", "Obs"
    ]
    
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    return df.dropna(subset=["Data"])

# =============================================
# INTERFACE DO USUÁRIO
# =============================================
def main():
    st.title("📅 Agenda de Consultas Vivver")
    
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
    
    with st.spinner("Conectando ao Vivver..."):
        dados = carregar_dados()
        df = processar_dados(dados)
    
    if df.empty:
        st.warning("Nenhum dado encontrado. Verifique conexão e credenciais.")
        return
    
    # Filtros
    st.sidebar.header("Filtros")
    ano = st.sidebar.selectbox("Ano", sorted(df["Data"].dt.year.unique(), reverse=True))
    mes = st.sidebar.selectbox("Mês", range(1,13), format_func=lambda x: calendar.month_name[x])
    
    # Aplicar filtros
    df_filtrado = df[(df["Data"].dt.year == ano) & (df["Data"].dt.month == mes)]
    
    # Mostrar calendário
    st.subheader(f"{calendar.month_name[mes]} {ano}")
    # ... (código do calendário aqui)

    # Mostrar dados
    st.dataframe(df_filtrado)
    
    # Exportar
    if st.button("📤 Exportar para Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False)
        st.download_button(
            label="⬇️ Baixar Arquivo",
            data=output.getvalue(),
            file_name=f"consultas_{mes}_{ano}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
