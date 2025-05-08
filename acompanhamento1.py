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
VIVVER_USER = "123"       # Substitua pelo seu usuário real
VIVVER_PASS = "123456"    # Substitua pela sua senha real
BASE_URL = "https://itabira-mg.vivver.com"

# =============================================
# CONFIGURAÇÃO DE SESSÃO SEGURA
# =============================================
session = requests.Session()

# Configuração de retentativas para falhas temporárias
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)

# Adaptador customizado para tratamento SSL
class VivverAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

session.mount("https://", VivverAdapter(max_retries=retry_strategy))
session.mount("http://", VivferAdapter(max_retries=retry_strategy))

# =============================================
# FUNÇÕES PRINCIPAIS COM TRATAMENTO DE ERROS
# =============================================
def fazer_login():
    """Realiza login no sistema Vivver com tratamento robusto de erros"""
    try:
        LOGIN_URL = urljoin(BASE_URL, "/login")
        
        # 1. Obter página de login e token CSRF
        try:
            response = session.get(LOGIN_URL, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            return False, f"Falha ao acessar página de login: {str(e)}"

        # 2. Extrair token CSRF com verificação
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': '_token'})
        
        if not csrf_input:
            return False, "Não foi possível encontrar o token CSRF na página"
            
        csrf_token = csrf_input.get('value')
        if not csrf_token:
            return False, "Token CSRF está vazio"

        # 3. Preparar dados do login
        login_data = {
            'conta': VIVVER_USER,
            'password': VIVVER_PASS,
            '_token': csrf_token
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': LOGIN_URL,
            'Origin': BASE_URL
        }

        # 4. Enviar dados de login
        try:
            login_response = session.post(
                LOGIN_URL,
                data=login_data,
                headers=headers,
                timeout=15,
                verify=False
            )
        except requests.RequestException as e:
            return False, f"Falha ao enviar dados de login: {str(e)}"

        # 5. Verificar se login foi bem-sucedido
        if "login" in login_response.url:
            return False, "Credenciais incorretas ou problema na autenticação"
            
        return True, "Login realizado com sucesso"

    except Exception as e:
        return False, f"Erro inesperado durante o login: {str(e)}"

@st.cache_data(ttl=3600)
def carregar_dados():
    """Carrega dados de agendamentos com tratamento completo de erros"""
    try:
        # 1. Fazer login
        success, message = fazer_login()
        if not success:
            st.error(f"Erro no login: {message}")
            return None

        # 2. Acessar dados
        DATA_URL = urljoin(BASE_URL, "/bit/gadget/view_paginate.json?id=225&draw=1&start=0&length=10000")
        
        try:
            response = session.get(DATA_URL, timeout=15, verify=False)
            response.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Falha ao acessar dados: {str(e)}")
            return None

        # 3. Verificar e retornar dados
        try:
            return response.json()
        except ValueError:
            st.error("Resposta não é um JSON válido")
            return None

    except Exception as e:
        st.error(f"Erro crítico: {str(e)}")
        return None

# =============================================
# INTERFACE DO USUÁRIO
# =============================================
def main():
    st.title("Agenda de Consultas Vivver")
    
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
    
    with st.spinner("Conectando ao sistema Vivver..."):
        dados = carregar_dados()
        
    if dados:
        try:
            df = pd.DataFrame(dados["data"])
            df.columns = [
                "ID", "Unidade", "Especialidade", "Profissional", 
                "Serviço", "Origem", "Tipo", "Hora", "Agenda", 
                "Data", "Data_Cadastro", "Prof_Cadastro", "Tipo_Servico", "Obs"
            ]
            
            st.dataframe(df)
            
            if st.button("📤 Exportar para Excel"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                st.download_button(
                    label="⬇️ Baixar arquivo",
                    data=output.getvalue(),
                    file_name="consultas_vivver.xlsx"
                )
                
        except Exception as e:
            st.error(f"Erro ao processar dados: {str(e)}")

if __name__ == "__main__":
    st.warning("AVISO: Verificação SSL desativada por necessidade técnica")
    main()
