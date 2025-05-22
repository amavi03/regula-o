import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import requests
import time  # Importação adicionada
from urllib3.exceptions import MaxRetryError, NewConnectionError
import os
import io

# Configuração da página
st.set_page_config(layout="wide", page_title="Agenda de Consultas", page_icon="🗕️")

# --- ESTILO CSS PERSONALIZADO ---
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
                allow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            
            # Verificar se o login foi bem-sucedido
            if "login" in response.url.lower():
                raise ValueError("Falha no login - verifique as credenciais")
            
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
                try:
                    start = response.text.find('{')
                    end = response.text.rfind('}') + 1
                    if start != -1 and end != 0:
                        return json.loads(response.text[start:end])
                except:
                    pass
                raise ValueError(f"Não foi possível decodificar a resposta. Status: {response.status_code}")
            
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
        if len(dados_lista) == 0:
            return pd.DataFrame()
        
        # Criar DataFrame com colunas dinâmicas
        colunas = [
            "DT_RowId", "Unidade", "Especialidade", "Profissional", "Serviço",
            "Origem", "Tipo", "Hora", "Agenda direta", "Data",
            "Data_Cadastro", "Profissional do Cadastro", "Tipo de Serviço", "Obs"
        ]
        
        df = pd.DataFrame(dados_lista)
        
        # Atribuir nomes às colunas disponíveis
        if len(df.columns) >= len(colunas):
            df.columns = colunas
            df = df.drop(columns=["DT_RowId"], errors='ignore')
        elif len(df.columns) > 0:
            # Se tiver menos colunas, usar os nomes que puder
            df.columns = colunas[:len(df.columns)]
        
        # Processar datas
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return pd.DataFrame()

def mostrar_calendario_mensal(df, origem_selecionada='Todos'):
    try:
        if origem_selecionada != 'Todos':
            df = df[df['Origem'] == origem_selecionada]
        
        # Ordenar por data e pegar os próximos 30 dias com vagas
        df = df.sort_values('Data')
        datas_unicas = df['Data'].dt.date.unique()
        proximos_30_dias = sorted(datas_unicas)[:30]
        
        # Configurações visuais
        hoje = datetime.now().date()
        st.subheader("Próximas Vagas Disponíveis (30 dias)")
        
        # Mostrar cada mês necessário
        meses_para_mostrar = {(data.month, data.year) for data in proximos_30_dias}
        for mes, ano in sorted(meses_para_mostrar):
            st.markdown(f"### {calendar.month_name[mes]} {ano}")
            
            # Filtrar dados para o mês atual
            df_mes = df[(df['Data'].dt.month == mes) & (df['Data'].dt.year == ano)]
            
            # Calendário
            cal = calendar.Calendar(firstweekday=6)
            dias_mes = cal.monthdays2calendar(ano, mes)
            
            # Cabeçalho dos dias da semana
            cols = st.columns(7)
            dias_semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            for i, dia in enumerate(dias_semana):
                cols[i].markdown(f"<div class='weekday-header'>{dia}</div>", unsafe_allow_html=True)
            
            # Mostrar cada semana
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
                        
                        # Estilo do dia
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
                        
                        # Mostrar o dia
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
        st.error(f"Erro ao gerar calendário: {str(e)}")

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
                
            # Mostrar calendário
            origens = ['Todos'] + sorted(df['Origem'].dropna().unique().tolist())
            origem_selecionada = st.sidebar.selectbox("Filtrar por Origem", origens)
            
            mostrar_calendario_mensal(df, origem_selecionada)
            
            # Mostrar dados detalhados
            if 'selected_date' in st.session_state and st.session_state.selected_date:
                st.subheader(f"Consultas em {st.session_state.selected_date.strftime('%d/%m/%Y')}")
                consultas_dia = df[df['Data'].dt.date == st.session_state.selected_date]
                st.dataframe(consultas_dia)
            
        except Exception as e:
            st.error(f"Falha crítica: {str(e)}")
            if debug_mode:
                st.exception(e)

if __name__ == "__main__":
    main()
