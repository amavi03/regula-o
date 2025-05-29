import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import requests
import time
from urllib3.exceptions import MaxRetryError, NewConnectionError
import os
import io
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

# Page configuration
st.set_page_config(layout="wide", page_title="Agenda de Consultas", page_icon="🗕️")

# Custom CSS
st.markdown("""
<style>
    .calendar-day {
        border-radius: 5px;
        padding: 8px;
        min-height: 80px;
        margin: 2px;
        cursor: pointer;
    }
    .calendar-day:hover {
        opacity: 0.8;
    }
    .selected-day {
        border: 2px solid #FF4B4B !important;
    }
    .weekday-header {
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
        color: #333;
    }
    .stAlert {
        padding: 10px;
        border-radius: 5px;
    }
    .filter-active {
        background-color: #e6f7ff;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 4px solid #1890ff;
    }
    .connection-test {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    .connection-success {
        background-color: #e6ffed;
        border-left: 4px solid #52c41a;
    }
    .connection-warning {
        background-color: #fffbe6;
        border-left: 4px solid #faad14;
    }
    .connection-error {
        background-color: #fff2f0;
        border-left: 4px solid #ff4d4f;
    }
    .error-details {
        background-color: #fff2f0;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        border-left: 4px solid #ff4d4f;
    }
</style>
""", unsafe_allow_html=True)

def safe_split(text, separator=None, maxsplit=-1):
    if text is None:
        return []
    try:
        return str(text).split(separator, maxsplit)
    except:
        return []

def testar_conexao():
    try:
        response = requests.get("https://itabira-mg.vivver.com", timeout=10, verify=False)
        if response.status_code == 200:
            return "success", "✅ Conexão com o site estabelecida com sucesso!"
        else:
            return "warning", f"⚠️ O site respondeu com status {response.status_code}"
    except Exception as e:
        return "error", f"❌ Erro na conexão: {str(e)}"

@st.cache_data(ttl=36000)
def carregar_dados_reais(debug_mode=False):
    max_tentativas = 3
    tentativa = 0
    
    while tentativa < max_tentativas:
        try:
            session = requests.Session()
            
            # Credentials - show in debug mode
            username = os.getenv('VIVVER_USER', '123')
            password = os.getenv('VIVVER_PASS', '38355212')
            
            if debug_mode:
                st.sidebar.write(f"Tentando login com usuário: {username}")
            
            # Get login page first to capture cookies
            login_page = session.get(
                "https://itabira-mg.vivver.com/login",
                timeout=10,
                verify=False,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            
            # Login data with all required fields
            login_data = {
                'conta': username,
                'password': password,
                'remember': 'on',
                # Add any additional fields required by the form
            }
            
            # Perform login
            response = session.post(
                "https://itabira-mg.vivver.com/login",
                data=login_data,
                timeout=30,
                allow_redirects=True,
                verify=False,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://itabira-mg.vivver.com/login',
                    'Origin': 'https://itabira-mg.vivver.com',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            # Improved login verification
            if response.status_code != 200:
                raise ValueError(f"Login failed with status code {response.status_code}")
                
            if 'login' in response.url.lower():
                raise ValueError("Login failed - redirected back to login page")
            
            # Access the API endpoint
            url_api = "https://itabira-mg.vivver.com/bit/gadget/view_paginate.json?id=228&draw=1&start=0&length=10000"
            api_response = session.get(
                url_api,
                timeout=30,
                verify=False,
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': response.url
                }
            )
            
            api_response.raise_for_status()
            
            try:
                dados = api_response.json()
                if not dados or not isinstance(dados, dict):
                    raise ValueError("Invalid API response format")
                return dados
            except json.JSONDecodeError:
                raise ValueError("Failed to decode API response")
            
        except Exception as e:
            tentativa += 1
            if tentativa >= max_tentativas:
                error_details = {
                    'error': str(e),
                    'attempt': tentativa,
                    'last_url': response.url if 'response' in locals() else None,
                    'status_code': response.status_code if 'response' in locals() else None
                }
                if debug_mode:
                    st.error("Error details:")
                    st.json(error_details)
                    if 'response' in locals():
                        st.error("Response content (first 2000 chars):")
                        st.text(response.text[:2000])
                raise Exception(f"Failed after {tentativa} attempts. Last error: {str(e)}")
            time.sleep(2)

def processar_dados(dados):
    try:
        if not dados or not isinstance(dados, dict):
            return pd.DataFrame()
        
        dados_lista = dados.get('data', [])
        if not isinstance(dados_lista, list):
            return pd.DataFrame()
        
        if len(dados_lista) == 0:
            return pd.DataFrame()
        
        colunas = [
            "DT_RowId", "Unidade", "Especialidade", "Profissional", "Serviço",
            "Origem", "Tipo", "Hora", "Agenda direta", "Data",
            "Data_Cadastro", "Profissional do Cadastro", "Tipo de Serviço", "Obs"
        ]
        
        df = pd.DataFrame(dados_lista)
        
        if len(df.columns) >= len(colunas):
            df.columns = colunas
            df = df.drop(columns=["DT_RowId"], errors='ignore')
        elif len(df.columns) > 0:
            df.columns = colunas[:len(df.columns)]
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
        
        return df
    
    except Exception as e:
        st.error(f"Data processing error: {str(e)}")
        return pd.DataFrame()

def mostrar_calendario_mensal(df, origem_selecionada='Todos'):
    try:
        if origem_selecionada != 'Todos':
            df = df[df['Origem'] == origem_selecionada]
        
        df = df.sort_values('Data')
        datas_unicas = df['Data'].dt.date.unique()
        proximos_30_dias = sorted(datas_unicas)[:30]
        
        hoje = datetime.now().date()
        st.subheader("Próximas Vagas Disponíveis (30 dias)")
        
        meses_para_mostrar = {(data.month, data.year) for data in proximos_30_dias}
        for mes, ano in sorted(meses_para_mostrar):
            st.markdown(f"### {calendar.month_name[mes]} {ano}")
            
            df_mes = df[(df['Data'].dt.month == mes) & (df['Data'].dt.year == ano)]
            
            cal = calendar.Calendar(firstweekday=6)
            dias_mes = cal.monthdays2calendar(ano, mes)
            
            cols = st.columns(7)
            dias_semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            for i, dia in enumerate(dias_semana):
                cols[i].markdown(f"<div class='weekday-header'>{dia}</div>", unsafe_allow_html=True)
            
            for semana in dias_mes:
                cols = st.columns(7)
                for i, (dia, _) in enumerate(semana):
                    with cols[i]:
                        if dia == 0:
                            st.write("")
                            continue
                            
                        data_atual = datetime(ano, mes, dia).date()
                        if data_atual not in proximos_30_dias:
                            st.write("")
                            continue
                            
                        eventos_dia = df_mes[df_mes['Data'].dt.date == data_atual]
                        num_eventos = len(eventos_dia)
                        
                        bg_color = "#ffffff" if num_eventos == 0 else "#bbdefb"
                        text_color = "#333333" if num_eventos == 0 else "#0d47a1"
                        border_color = "#e0e0e0" if num_eventos == 0 else "#90caf9"
                        
                        if num_eventos >= 50:
                            bg_color = "#64b5f6"
                            text_color = "#ffffff"
                            border_color = "#42a5f5"
                        
                        if num_eventos >= 200:
                            bg_color = "#fff9c4"
                            text_color = "#f57f17"
                            border_color = "#fff176"
                        
                        border_width = "2px" if data_atual == hoje else "1px"
                        border_color = "#2196F3" if data_atual == hoje else border_color
                        
                        st.markdown(f"""
                        <div class='calendar-day' 
                            style='border: {border_width} solid {border_color}; 
                            background-color: {bg_color}; color: {text_color}'>
                            <div style='font-weight: bold;'>{dia}</div>
                            <div style='font-size: 0.8em;'>{num_eventos} consulta(s)</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("", key=f"day_{dia}_{mes}_{ano}"):
                            st.session_state.selected_date = data_atual
                            st.rerun()
    except Exception as e:
        st.error(f"Calendar error: {str(e)}")

def main():
    st.title("📅 Acompanhamento de Vagas")

    debug_mode = st.sidebar.checkbox("🔍 Modo de Depuração", value=False)
    
    with st.sidebar.expander("🔧 Diagnóstico do Sistema", expanded=False):
        if st.button("🧪 Testar Conexão com Vivver"):
            with st.spinner("Testando conexão..."):
                status, mensagem = testar_conexao()
                st.markdown(f"""
                <div class='connection-test connection-{status}'>
                    {mensagem}
                </div>
                """, unsafe_allow_html=True)

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
                
            origens = ['Todos'] + sorted(df['Origem'].dropna().unique().tolist())
            origem_selecionada = st.sidebar.selectbox("Filtrar por Origem", origens)
            
            mostrar_calendario_mensal(df, origem_selecionada)
            
            if 'selected_date' in st.session_state and st.session_state.selected_date:
                st.subheader(f"Consultas em {st.session_state.selected_date.strftime('%d/%m/%Y')}")
                consultas_dia = df[df['Data'].dt.date == st.session_state.selected_date]
                st.dataframe(consultas_dia)
            
        except Exception as e:
            st.error(f"Critical error: {str(e)}")
            if debug_mode:
                st.exception(e)

if __name__ == "__main__":
    main()
