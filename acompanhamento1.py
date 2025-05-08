import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import io
import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuração da página
st.set_page_config(layout="wide", page_title="Agenda de Consultas", page_icon="🗕️")

# --- CREDENCIAIS FIXAS ---
USERNAME = "123"  # Substitua pelo usuário real
PASSWORD = "123456"  # Substitua pela senha real

# --- CONFIGURAÇÃO SSL ---
# ATENÇÃO: Isso reduz a segurança, use apenas se necessário
ssl._create_default_https_context = ssl._create_unverified_context

# --- CONFIGURAÇÃO DE REQUESTS ---
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# (Manter todo o CSS personalizado original aqui)

# --- CONSTANTES ---
BASE_URL = "https://itabira-mg.vivver.com"
LOGIN_URL = urljoin(BASE_URL, "/login")
DATA_URL = urljoin(BASE_URL, "/bit/gadget/view_paginate.json?id=225&draw=1&start=0&length=10000")

# --- FUNÇÕES PRINCIPAIS ---
def fazer_login_vivver():
    """Realiza o login no sistema Vivver e retorna a sessão autenticada"""
    try:
        # Primeira requisição para obter cookies e tokens
        try:
            login_page = session.get(LOGIN_URL, verify=False, timeout=10)
            login_page.raise_for_status()
        except requests.exceptions.SSLError:
            # Tentar novamente sem verificação SSL
            login_page = session.get(LOGIN_URL, verify=False, timeout=10)
        
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # Extrair token CSRF
        csrf_token = ""
        csrf_input = soup.find('input', {'name': '_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value', '')
        
        # Dados do formulário de login
        login_data = {
            'conta': USERNAME,
            'password': PASSWORD,
            '_token': csrf_token
        }
        
        # Headers para simular um navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': LOGIN_URL,
            'Origin': BASE_URL
        }
        
        # Fazer login (com tratamento de SSL)
        try:
            response = session.post(LOGIN_URL, data=login_data, headers=headers, 
                                 verify=False, timeout=10, allow_redirects=True)
        except requests.exceptions.SSLError:
            response = session.post(LOGIN_URL, data=login_data, headers=headers,
                                 verify=False, timeout=10, allow_redirects=True)
        
        # Verificar se o login foi bem-sucedido
        if "login" in response.url:
            return None, "Falha no login - Verifique as credenciais no script"
        
        return session, "Login realizado com sucesso"
        
    except Exception as e:
        return None, f"Erro durante o login: {str(e)}"

@st.cache_data(ttl=3600)
def carregar_dados_reais():
    """Carrega os dados do Vivver após autenticação"""
    try:
        # Fazer login
        session, mensagem = fazer_login_vivver()
        if not session:
            st.error(mensagem)
            return None
        
        # Acessar a URL dos dados (com tratamento de SSL)
        try:
            response = session.get(DATA_URL, verify=False, timeout=10)
        except requests.exceptions.SSLError:
            response = session.get(DATA_URL, verify=False, timeout=10)
        
        if response.status_code != 200:
            st.error(f"Erro ao acessar dados: HTTP {response.status_code}")
            return None
            
        try:
            return response.json()
        except ValueError:
            st.error("Resposta não é um JSON válido. Página de login pode ter sido retornada.")
            return None
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None

# (Manter todas as outras funções originais: processar_dados, gerar_excel, 
# mostrar_calendario_mensal, show_start_screen, main_app)

# --- CONTROLE DE FLUXO ---
if 'started' not in st.session_state:
    st.session_state.started = False

if st.session_state.started:
    main_app()
else:
    show_start_screen()
