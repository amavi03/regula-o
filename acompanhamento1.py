# Verificação e instalação de dependências necessárias
try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import io
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib3

# Configuração para desenvolvimento (remover em produção)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração da página
st.set_page_config(layout="wide", page_title="Agenda de Consultas Vivver", page_icon="🗓️")

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* ESTILOS GERAIS */
    .calendar-day {
        border-radius: 5px;
        padding: 8px;
        min-height: 80px;
        margin: 2px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .calendar-day:hover {
        transform: scale(1.03);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .selected-day {
        border: 2px solid #FF4B4B !important;
        box-shadow: 0 0 0 2px rgba(255,75,75,0.3);
    }
    
    .weekday-header {
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
        color: #333;
        font-size: 0.9em;
    }
    
    .filter-active {
        background-color: #e6f7ff;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 4px solid #1890ff;
    }
    
    /* TELA INICIAL */
    .start-screen {
        text-align: center;
        margin: 30px 0;
        padding: 20px;
    }
    
    .start-screen h1 {
        color: #2c3e50;
        margin-bottom: 10px;
    }
    
    /* BOTÕES */
    .primary-button {
        padding: 20px 40px !important;
        font-size: 18px !important;
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        width: 300px !important;
        margin: 20px auto !important;
        display: block !important;
        transition: all 0.3s !important;
    }
    
    .primary-button:hover {
        background-color: #3e8e41 !important;
        transform: translateY(-2px);
    }
    
    .secondary-button {
        padding: 12px 24px !important;
        font-size: 16px !important;
        width: 100% !important;
        margin: 10px 0 !important;
        background-color: #f0f2f6 !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
        border-radius: 6px !important;
    }
    
    /* AVISOS */
    .ssl-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 12px;
        border-radius: 6px;
        margin: 15px 0;
        border-left: 4px solid #ffeeba;
        font-size: 0.9em;
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 12px;
        border-radius: 6px;
        margin: 15px 0;
        border-left: 4px solid #f5c6cb;
    }
    
    /* SIDEBAR */
    .sidebar-section {
        margin-bottom: 25px;
    }
    
    /* RESPONSIVIDADE */
    @media (max-width: 768px) {
        .calendar-day {
            min-height: 60px;
            padding: 5px;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES PRINCIPAIS ---
@st.cache_data(ttl=600)  # Cache de 10 minutos
def carregar_dados_reais():
    try:
        # Verifica se as credenciais estão configuradas
        username = os.getenv('VIVVER_USER', st.secrets.get("VIVVER_USER", ""))
        password = os.getenv('VIVVER_PASS', st.secrets.get("VIVVER_PASS", ""))
        
        if not username or not password:
            st.error("Credenciais não configuradas. Por favor, configure VIVVER_USER e VIVVER_PASS nas variáveis de ambiente.")
            return None

        session = requests.Session()
        login_url = 'https://itabira-mg.vivver.com/login'
        data_url = "https://itabira-mg.vivver.com/bit/gadget/view_paginate.json?id=225&draw=1&start=0&length=10000"
        
        # Primeiro obtém a página de login para pegar tokens CSRF se necessário
        try:
            # Tentativa com verificação SSL
            response = session.get(login_url, verify=True, timeout=10)
        except requests.exceptions.SSLError:
            # Se falhar, tenta sem verificação SSL
            response = session.get(login_url, verify=False, timeout=10)
            st.markdown("""
            <div class="ssl-warning">
                ⚠️ Aviso de Segurança: Conexão realizada sem verificação completa de certificado SSL.
                <br><small>Isso é necessário para compatibilidade com o sistema atual.</small>
            </div>
            """, unsafe_allow_html=True)
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao conectar ao servidor: {str(e)}")
            return None
            
        # Analisa a página de login para tokens CSRF
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': '_token'})['value'] if soup.find('input', {'name': '_token'}) else None
        
        # Prepara dados para login
        login_data = {
            'conta': username,
            'password': password,
        }
        
        if csrf_token:
            login_data['_token'] = csrf_token
        
        # Tentativa de login
        try:
            login_response = session.post(
                login_url,
                data=login_data,
                verify=False,  # Desativa verificação SSL para o login
                allow_redirects=True,
                timeout=15
            )
        except requests.exceptions.RequestException as e:
            st.error(f"Erro durante o login: {str(e)}")
            return None
            
        # Verifica se o login foi bem-sucedido
        if 'login' in login_response.url:
            st.error("Falha no login. Verifique suas credenciais.")
            return None
            
        # Obtém os dados após login
        try:
            response = session.get(data_url, verify=False, timeout=15)
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    st.error("Os dados retornados não estão no formato esperado.")
                    return None
            else:
                st.error(f"Erro ao obter dados: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao obter dados: {str(e)}")
            return None

    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        return None

def processar_dados(dados):
    if not dados or "data" not in dados:
        return pd.DataFrame()

    try:
        df = pd.DataFrame(dados["data"])
        df.columns = [
            "DT_RowId", "Unidade", "Especialidade", "Profissional", "Serviço",
            "Origem", "Tipo", "Hora", "Agenda direta", "Data",
            "Data_Cadastro", "Profissional do Cadastro", "Tipo de Serviço", "Obs"
        ]
        df = df.drop(columns=["DT_RowId"])
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Data"])
        return df
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return pd.DataFrame()

def gerar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Agendas')
        writer.save()
    return output.getvalue()

def mostrar_calendario_mensal(df, mes, ano, origem_selecionada='Todos'):
    try:
        if origem_selecionada != 'Todos':
            df = df[df['Origem'] == origem_selecionada]
        df_mes = df[(df['Data'].dt.month == mes) & (df['Data'].dt.year == ano)]

        cal = calendar.Calendar(firstweekday=6)  # Domingo como primeiro dia
        dias_mes = cal.monthdays2calendar(ano, mes)
        hoje = datetime.now().date()

        st.subheader(f"{calendar.month_name[mes]} {ano}")
        
        # Cabeçalho com dias da semana
        cols = st.columns(7)
        dias_semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        for i, dia in enumerate(dias_semana):
            cols[i].markdown(f"<div class='weekday-header'>{dia}</div>", unsafe_allow_html=True)

        # Dias do mês
        for semana in dias_mes:
            cols = st.columns(7)
            for i, (dia, _) in enumerate(semana):
                with cols[i]:
                    if dia == 0:
                        st.write("")  # Dia vazio (fora do mês)
                    else:
                        data_atual = datetime(ano, mes, dia).date()
                        eventos_dia = df_mes[df_mes['Data'].dt.date == data_atual]
                        num_eventos = len(eventos_dia)

                        # Define cores com base no número de consultas
                        if num_eventos == 0:
                            bg_color = "#f8f9fa"
                            text_color = "#6c757d"
                            border_color = "#dee2e6"
                        elif num_eventos < 20:
                            bg_color = "#d1e7dd"
                            text_color = "#0a3622"
                            border_color = "#a3cfbb"
                        elif num_eventos < 50:
                            bg_color = "#fff3bf"
                            text_color = "#664d03"
                            border_color = "#ffec99"
                        else:
                            bg_color = "#f8d7da"
                            text_color = "#842029"
                            border_color = "#f5c2c7"

                        # Estilo para o dia atual
                        border_width = "2px" if data_atual == hoje else "1px"
                        border_color = "#0d6efd" if data_atual == hoje else border_color
                        
                        # Classe para dia selecionado
                        selected_class = "selected-day" if 'selected_date' in st.session_state and st.session_state.selected_date == data_atual else ""

                        # HTML do dia do calendário
                        st.markdown(f"""
                        <div class='day-container'>
                            <div class='calendar-day {selected_class}' 
                                style='border: {border_width} solid {border_color}; 
                                background-color: {bg_color}; color: {text_color}'>
                                <div style='font-weight: bold;'>{dia}</div>
                                <div style='font-size: 0.8em;'>{num_eventos} consulta(s)</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Botão invisível para selecionar o dia
                        if st.button("", key=f"day_{dia}_{mes}_{ano}"):
                            st.session_state.selected_date = data_atual
                            st.rerun()
    except Exception as e:
        st.error(f"Erro ao gerar calendário: {str(e)}")

# --- TELA INICIAL ---
def show_start_screen():
    st.markdown("""
    <div class="start-screen">
        <h1>📅 Agenda de Consultas Vivver</h1>
        <p style="font-size: 1.1em; color: #495057;">Sistema de acompanhamento de vagas e agendamentos</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("INICIAR SISTEMA", key="start_button", type="primary", help="Clique para acessar o painel de agendamentos"):
        st.session_state.started = True
        st.rerun()
    
    st.markdown("""
    <div style="text-align: center; margin-top: 40px;">
        <a href="https://exemplo.com/historico-versoes" target="_blank" class="history-button">
            📚 Histórico de Versões
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="creditos" style="margin-top: 50px;">
        <p style="color: #6c757d;">Desenvolvido por <strong style="color: #2c3e50;">Vinicius Viana</strong></p>
        <p style="font-size: 0.9em; color: #adb5bd;">Versão: 25.06.15</p>
    </div>
    """, unsafe_allow_html=True)

# --- APLICATIVO PRINCIPAL ---
def main_app():
    st.title("📊 Painel de Agendamentos Vivver")
    
    # Verificação de conexão
    with st.spinner("Verificando conexão com o servidor..."):
        try:
            test_conn = requests.get('https://itabira-mg.vivver.com', timeout=5, verify=False)
            if test_conn.status_code != 200:
                st.error("Não foi possível conectar ao servidor da Vivver. Verifique sua conexão com a internet.")
                st.stop()
        except:
            st.error("Erro ao tentar conectar ao servidor da Vivver.")
            st.stop()

    # Botão para recarregar os dados
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Atualizar Dados", help="Recarregar os dados mais recentes"):
            st.cache_data.clear()
            st.session_state.selected_date = None
            st.rerun()

    # Inicializa a data selecionada se não existir
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None

    # Carrega os dados
    with st.spinner("Carregando dados da Vivver..."):
        dados = carregar_dados_reais()
        df = processar_dados(dados)

    if df.empty:
        st.warning("Nenhum dado foi carregado. Verifique a conexão ou as credenciais.")
        return

    # --- SIDEBAR ---
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por período
    st.sidebar.markdown("### Período")
    data_atual = datetime.now()
    ano_atual = data_atual.year
    mes_atual = data_atual.month

    anos_disponiveis = sorted(df['Data'].dt.year.unique(), reverse=True)
    if ano_atual not in anos_disponiveis:
        anos_disponiveis.insert(0, ano_atual)

    ano = st.sidebar.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
    meses = {i: calendar.month_name[i] for i in range(1, 13)}
    mes_nome = st.sidebar.selectbox("Mês", list(meses.values()), index=mes_atual - 1)
    mes = list(meses.keys())[list(meses.values()).index(mes_nome)]

    # Filtro por origem
    st.sidebar.markdown("### Origem")
    origens_disponiveis = ['Todos'] + sorted(df['Origem'].dropna().unique().tolist())
    origem_selecionada = st.sidebar.selectbox("Selecione a origem", origens_disponiveis)
    
    # Botão para detalhes
    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 Detalhes da Origem", key="origin_details_button"):
        url_detalhes = f"https://exemplo.com/detalhes-origem?origem={origem_selecionada.replace(' ', '%20')}"
        st.markdown(f"""
        <script>
            window.open('{url_detalhes}', '_blank');
        </script>
        """, unsafe_allow_html=True)

    # Mostra calendário
    if origem_selecionada != 'Todos':
        st.markdown(f"""
        <div class='filter-active'>
            <strong>Filtro Ativo:</strong> Mostrando apenas agendamentos da origem <strong>{origem_selecionada}</strong>
        </div>
        """, unsafe_allow_html=True)

    mostrar_calendario_mensal(df, mes, ano, origem_selecionada)

    # Resumo na sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Resumo")
    
    if st.session_state.selected_date:
        df_filtrado = df[df['Data'].dt.date == st.session_state.selected_date]
        periodo = f"no dia {st.session_state.selected_date.strftime('%d/%m/%Y')}"
    else:
        df_filtrado = df[(df['Data'].dt.month == mes) & (df['Data'].dt.year == ano)]
        periodo = f"em {mes_nome} {ano}"

    if origem_selecionada != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Origem'] == origem_selecionada]
        periodo += f" (Origem: {origem_selecionada})"

    st.sidebar.metric(label=f"Total de Consultas {periodo}", value=len(df_filtrado))
    st.sidebar.metric(label="Profissionais Ativos", value=df_filtrado['Profissional'].nunique())
    st.sidebar.metric(label="Unidades Atendidas", value=df_filtrado['Unidade'].nunique())
    
    # Créditos na sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <small style="color: #6c757d;">Desenvolvido por</small>
        <br>
        <strong style="color: #2c3e50;">Vinicius Viana</strong>
        <br>
        <small style="color: #adb5bd;">v25.06.15</small>
    </div>
    """, unsafe_allow_html=True)

    # --- ÁREA PRINCIPAL ---
    if not df_filtrado.empty:
        st.markdown(f"### 📋 Detalhes das Consultas {periodo}")
        
        if st.session_state.selected_date and st.button("Mostrar todos os agendamentos do mês"):
            st.session_state.selected_date = None
            st.rerun()

        # Mostra dataframe com os agendamentos
        st.dataframe(
            df_filtrado.sort_values(['Data', 'Hora']),
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Hora": st.column_config.TimeColumn("Hora", format="HH:mm"),
                "Profissional": st.column_config.TextColumn("Profissional"),
                "Unidade": st.column_config.TextColumn("Unidade", width="medium")
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )

        # Botão para exportar
        st.download_button(
            label="📤 Exportar para Excel",
            data=gerar_excel(df_filtrado),
            file_name=f"consultas_vivver_{mes_nome.lower()}_{ano}.xlsx" if not st.session_state.selected_date else f"consultas_vivver_{st.session_state.selected_date.strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Exportar todos os dados filtrados para um arquivo Excel"
        )
    else:
        st.info(f"Nenhuma consulta agendada {periodo}.")

# --- CONTROLE DE FLUXO ---
if 'started' not in st.session_state:
    st.session_state.started = False

if st.session_state.started:
    main_app()
else:
    show_start_screen()
