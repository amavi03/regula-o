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
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================
# CONFIGURAÇÕES (MODIFIQUE AQUI)
# =============================================
VIVVER_USER = "123"       # Substitua pelo seu usuário
VIVVER_PASS = "123456"    # Substitua pela sua senha
BASE_URL = "https://itabira-mg.vivver.com"

# =============================================
# CONFIGURAÇÃO SSL SEGURA
# =============================================
class CustomHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        # Cria contexto SSL personalizado
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # Desativa verificação (CUIDADO!)
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# =============================================
# CONFIGURAÇÃO DE SESSÃO
# =============================================
session = requests.Session()

# Configura retentativas para falhas temporárias
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)

# Usa nosso adaptador customizado para SSL
adapter = CustomHTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# =============================================
# FUNÇÕES PRINCIPAIS
# =============================================
def fazer_login():
    """Realiza login no sistema Vivver com tratamento de SSL"""
    try:
        LOGIN_URL = urljoin(BASE_URL, "/login")
        
        # Primeira requisição para obter token CSRF
        try:
            response = session.get(LOGIN_URL, timeout=10)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            st.warning("Aviso: Verificação de certificado SSL desativada por necessidade")
            response = session.get(LOGIN_URL, timeout=10, verify=False)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': '_token'}).get('value', '')
        
        # Dados do login
        login_data = {
            'conta': VIVVER_USER,
            'password': VIVVER_PASS,
            '_token': csrf_token
        }
        
        # Headers para simular navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': LOGIN_URL
        }
        
        # Envia dados de login
        login_response = session.post(
            LOGIN_URL,
            data=login_data,
            headers=headers,
            timeout=10,
            verify=False  # Necessário para contornar erro SSL
        )
        
        if "login" in login_response.url:
            return False, "Falha no login - Verifique as credenciais"
        return True, "Login realizado com sucesso"
        
    except Exception as e:
        return False, f"Erro durante o login: {str(e)}"

@st.cache_data(ttl=3600)
def carregar_dados():
    """Carrega os dados de agendamentos"""
    try:
        success, message = fazer_login()
        if not success:
            st.error(message)
            return None
        
        DATA_URL = urljoin(BASE_URL, "/bit/gadget/view_paginate.json?id=225&draw=1&start=0&length=10000")
        response = session.get(DATA_URL, timeout=10, verify=False)
        
        if response.status_code != 200:
            st.error(f"Erro ao acessar dados (HTTP {response.status_code})")
            return None
            
        return response.json()
    except Exception as e:
        st.error(f"Erro crítico: {str(e)}")
        return None

# =============================================
# INTERFACE DO USUÁRIO (simplificada)
# =============================================
def main():
    st.title("Agenda de Consultas Vivver")
    
    with st.spinner("Conectando ao sistema Vivver..."):
        dados = carregar_dados()
        
    if dados:
        df = pd.DataFrame(dados["data"])
        st.dataframe(df.head())
        
        if st.button("Exportar para Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="Baixar arquivo",
                data=output.getvalue(),
                file_name="consultas.xlsx"
            )

if __name__ == "__main__":
    main()
