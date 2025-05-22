import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import io
import os
import subprocess
import time
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from urllib3.exceptions import MaxRetryError, NewConnectionError

# Configuração inicial (mantenha seu CSS e imports)

def safe_get(dictionary, keys, default=None):
    """Acessa dicionários de forma segura"""
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys:
        try:
            dictionary = dictionary[key]
        except (KeyError, TypeError, AttributeError):
            return default
    return dictionary

def safe_split(text, separator=None, maxsplit=-1):
    """Versão segura do split que trata None e outros casos"""
    if text is None:
        return []
    try:
        if not isinstance(text, str):
            text = str(text)
        return text.split(separator, maxsplit)
    except:
        return []

@st.cache_data(ttl=36000)
def carregar_dados_reais(debug_mode=False):
    max_tentativas = 3
    tentativa = 0
    
    while tentativa < max_tentativas:
        navegador = None
        session = requests.Session()
        try:
            # Configuração otimizada para Streamlit Cloud
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            servico = Service(ChromeDriverManager().install())
            navegador = webdriver.Chrome(service=servico, options=chrome_options)
            navegador.set_page_load_timeout(45)
            
            # Fazer login com Selenium
            username = os.getenv('VIVVER_USER', '123')
            password = os.getenv('VIVVER_PASS', '38355212')
            
            navegador.get('https://itabira-mg.vivver.com/login')
            
            # Preencher login de forma mais robusta
            def safe_send_keys(element, text):
                if element:
                    element.clear()
                    element.send_keys(text)
            
            conta = WebDriverWait(navegador, 20).until(
                EC.presence_of_element_located((By.ID, 'conta')))
            safe_send_keys(conta, username)
            
            senha = WebDriverWait(navegador, 20).until(
                EC.presence_of_element_located((By.ID, 'password')))
            safe_send_keys(senha, password)
            
            # Clicar no botão de login
            navegador.find_element(By.XPATH, '//div[@role="button"]').click()
            
            # Esperar redirecionamento
            WebDriverWait(navegador, 20).until(
                lambda driver: driver.current_url != 'https://itabira-mg.vivver.com/login')
            
            # Obter cookies da sessão
            cookies = navegador.get_cookies()
            navegador.quit()
            
            # Configurar sessão requests com os cookies
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # Acessar API diretamente via requests
            url_api = "https://itabira-mg.vivver.com/bit/gadget/view_paginate.json?id=228&draw=1&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&start=0&length=10000"
            
            response = session.get(url_api, timeout=30)
            response.raise_for_status()
            
            try:
                dados = response.json()
                if not dados or not isinstance(dados, dict):
                    raise ValueError("Resposta da API inválida")
                
                return dados
            except json.JSONDecodeError:
                # Tentar extrair JSON manualmente se a resposta estiver malformada
                try:
                    dados = json.loads(response.text)
                    return dados
                except:
                    raise ValueError("Não foi possível decodificar a resposta da API")
            
        except Exception as e:
            tentativa += 1
            if navegador is not None:
                try:
                    navegador.quit()
                except:
                    pass
            
            if tentativa >= max_tentativas:
                error_msg = f"Falha na tentativa {tentativa}: {str(e)}"
                if "'NoneType' object has no attribute 'split'" in str(e):
                    error_msg += "\n\n🔍 **Solução**: O sistema não conseguiu extrair os dados corretamente da página. Isso pode ocorrer quando:"
                    error_msg += "\n1. A estrutura do site mudou"
                    error_msg += "\n2. O login não foi bem-sucedido"
                    error_msg += "\n3. A API retornou dados inválidos"
                
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
        
        # Acesso seguro aos dados
        dados_lista = safe_get(dados, ['data'], [])
        
        if not dados_lista or not isinstance(dados_lista, list):
            return pd.DataFrame()
        
        # Criar DataFrame com verificação de colunas
        colunas_esperadas = 14
        if len(dados_lista) > 0 and len(dados_lista[0]) < colunas_esperadas:
            st.warning(f"Dados com número insuficiente de colunas (esperado: {colunas_esperadas}, obtido: {len(dados_lista[0])}")
            return pd.DataFrame()
        
        df = pd.DataFrame(dados_lista)
        
        # Mapeamento de colunas com fallback
        nomes_colunas = [
            "DT_RowId", "Unidade", "Especialidade", "Profissional", "Serviço",
            "Origem", "Tipo", "Hora", "Agenda direta", "Data",
            "Data_Cadastro", "Profissional do Cadastro", "Tipo de Serviço", "Obs"
        ]
        
        if len(df.columns) >= len(nomes_colunas):
            df.columns = nomes_colunas
            df = df.drop(columns=["DT_RowId"])
        else:
            st.warning("Estrutura de dados diferente do esperado")
            return pd.DataFrame()
        
        # Converter datas com tratamento de erro
        df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
        df = df.dropna(subset=["Data"])
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return pd.DataFrame()

# (Mantenha o restante das suas funções como mostrar_calendario_mensal, gerar_excel, etc)

def main():
    # (Mantenha sua configuração inicial de página)
    
    try:
        # (Mantenha sua UI inicial)
        
        with st.spinner("Carregando dados..."):
            dados = carregar_dados_reais(debug_mode)
            df = processar_dados(dados)
            
            if df.empty:
                st.error("""
                Não foi possível carregar os dados. Possíveis causas:
                1. Problema de conexão com o servidor
                2. Credenciais inválidas
                3. Mudança na estrutura do site
                """)
                if debug_mode:
                    st.json(dados)
                return
        
        # (Mantenha o restante da sua lógica de exibição)
        
    except Exception as e:
        st.error(f"Erro crítico: {str(e)}")
        if debug_mode:
            st.exception(e)

if __name__ == "__main__":
    main()
