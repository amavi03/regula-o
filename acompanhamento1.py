import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
import io
import os
import requests

# Configuração da página
st.set_page_config(layout="wide", page_title="Agenda de Consultas", page_icon="🗕️")

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
<style>
    /* ESTILOS ORIGINAIS */
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
    .filter-active {
        background-color: #e6f7ff;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 4px solid #1890ff;
    }
    
    /* ESTILO TELA INICIAL */
    .start-screen {
        text-align: center;
        margin-bottom: 30px;
    }
    
    /* BOTÃO INICIAR */
    div[data-testid="stButton"] > button[kind="primary"] {
        padding: 20px 40px !important;
        font-size: 24px !important;
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        width: 300px !important;
        margin: 0 auto !important;
        display: block !important;
    }
    
    /* BOTÃO HISTÓRICO DE VERSÕES */
    .history-button {
        padding: 12px 24px;
        font-size: 16px;
        width: 200px;
        margin: 20px auto;
        display: block;
        background-color: #f0f2f6;
        color: #333;
        border: 1px solid #ccc;
        border-radius: 4px;
        text-align: center;
        text-decoration: none;
        cursor: pointer;
    }
    .history-button:hover {
        background-color: #e6e9ef;
    }
    
    /* BOTÃO DETALHES ORIGEM (SIDEBAR) */
    div[data-testid="stSidebar"] button[kind="secondary"] {
        padding: 12px 24px !important;
        font-size: 16px !important;
        width: 100% !important;
        margin: 10px 0 !important;
        background-color: #f0f2f6 !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
    }
    
    /* CRÉDITOS */
    .creditos {
        text-align: center;
        margin-top: 20px;
        color: #666;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# --- DADOS MOCKADOS PARA DEMONSTRAÇÃO ---
def criar_dados_mockados():
    """Cria dados de exemplo para demonstração quando não houver conexão com a API"""
    base_date = datetime.now().date()
    dados = {
        "data": []
    }
    
    especialidades = ["Cardiologia", "Pediatria", "Ortopedia", "Dermatologia", "Oftalmologia"]
    origens = ["Sistema", "Telefone", "WhatsApp", "Presencial", "Site"]
    unidades = ["Unidade Centro", "Unidade Norte", "Unidade Sul"]
    profissionais = ["Dr. Silva", "Dra. Souza", "Dr. Oliveira", "Dra. Costa", "Dr. Santos"]
    
    for i in range(100):
        day = (base_date.day + i % 20) % 28 + 1  # Garante dias entre 1-28
        month = base_date.month + (i // 28)
        if month > 12:
            month = month - 12
        
        dados["data"].append([
            f"row_{i}",
            unidades[i % len(unidades)],
            especialidades[i % len(especialidades)],
            profissionais[i % len(profissionais)],
            "Consulta",
            origens[i % len(origens)],
            "Rotina",
            f"{8 + (i % 10)}:00",
            "Sim",
            f"{day:02d}/{month:02d}/{base_date.year}",
            f"{day:02d}/{month:02d}/{base_date.year}",
            profissionais[(i + 1) % len(profissionais)],
            "Eletiva",
            f"Observação {i}"
        ])
    
    return dados

# --- FUNÇÕES PRINCIPAIS ---
@st.cache_data(ttl=120)
def carregar_dados_reais():
    try:
        # Verifica se há variáveis de ambiente para autenticação
        api_url = os.getenv('API_URL', '')
        api_key = os.getenv('API_KEY', '')
        
        if not api_url or not api_key:
            st.warning("Usando dados de demonstração. Configure as variáveis de ambiente API_URL e API_KEY para acessar dados reais.")
            return criar_dados_mockados()
        
        # Se houver configuração de API, tenta fazer a requisição
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        st.error(f"Erro ao carregar dados da API: {str(e)}. Usando dados de demonstração.")
        return criar_dados_mockados()

def processar_dados(dados):
    if not dados or "data" not in dados:
        return pd.DataFrame()

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

        cal = calendar.Calendar(firstweekday=6)
        dias_mes = cal.monthdays2calendar(ano, mes)
        hoje = datetime.now().date()

        st.subheader(f"{calendar.month_name[mes]} {ano}")
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
                    else:
                        data_atual = datetime(ano, mes, dia).date()
                        eventos_dia = df_mes[df_mes['Data'].dt.date == data_atual]
                        num_eventos = len(eventos_dia)

                        if num_eventos == 0:
                            bg_color = "#ffffff"
                            text_color = "#333333"
                            border_color = "#e0e0e0"
                        elif num_eventos < 50:
                            bg_color = "#bbdefb"
                            text_color = "#0d47a1"
                            border_color = "#90caf9"
                        elif num_eventos < 200:
                            bg_color = "#64b5f6"
                            text_color = "#ffffff"
                            border_color = "#42a5f5"
                        else:
                            bg_color = "#fff9c4"
                            text_color = "#f57f17"
                            border_color = "#fff176"

                        border_width = "2px" if data_atual == hoje else "1px"
                        border_color = "#2196F3" if data_atual == hoje else border_color
                        selected_class = "selected-day" if 'selected_date' in st.session_state and st.session_state.selected_date == data_atual else ""

                        st.markdown(f"""
                        <div class='day-container'>
                            <div class='calendar-day {selected_class}' 
                                style='border: {border_width} solid {border_color}; 
                                border-radius: 5px; padding: 8px; min-height: 80px; margin: 2px; 
                                background-color: {bg_color}; color: {text_color}'>
                                <div style='font-weight: bold; font-size: 1.1em;'>{dia}</div>
                                <div style='font-size: 0.8em;'>{num_eventos} consulta(s)</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button("", key=f"day_{dia}_{mes}_{ano}"):
                            st.session_state.selected_date = data_atual
                            st.rerun()
    except Exception as e:
        st.error(f"Erro ao gerar calendário: {str(e)}")

# --- TELA INICIAL ---
def show_start_screen():
    st.markdown("""
    <div class="start-screen">
        <h1>📅 Agenda de Consultas</h1>
        <p>Sistema de acompanhamento de vagas e agendamentos</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão "Iniciar" grande e centralizado
    if st.button("INICIAR", key="start_button", type="primary"):
        st.session_state.started = True
        st.rerun()
    
    # Botão "Histórico de Versões" (abre em nova aba)
    st.markdown("""
    <div style="text-align: center;">
        <a href="https://exemplo.com/historico-versoes" target="_blank" class="history-button">
            Histórico de Versões
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Créditos
    st.markdown("""
    <div class="creditos">
        <p>Elaborado por: <strong>Vinicius Viana</strong></p>
        <p>Versão: 25.05.05 (Cloud)</p>
    </div>
    """, unsafe_allow_html=True)

# --- APLICATIVO PRINCIPAL ---
def main_app():
    st.title("📅 Acompanhamento de Vagas")

    # Botão para recarregar os dados
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.session_state.selected_date = None
        st.rerun()

    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None

    with st.spinner("Carregando dados..."):
        dados = carregar_dados_reais()
        df = processar_dados(dados)

    if df.empty:
        st.warning("Nenhum dado foi carregado. Verifique a conexão ou as credenciais.")
        return

    st.sidebar.header("Filtros")

    data_atual = datetime.now()
    ano_atual = data_atual.year
    mes_atual = data_atual.month

    anos_disponiveis = sorted(df['Data'].dt.year.unique(), reverse=True)
    if ano_atual not in anos_disponiveis:
        anos_disponiveis.insert(0, ano_atual)

    ano = st.sidebar.selectbox("Selecione o ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
    meses = {i: calendar.month_name[i] for i in range(1, 13)}
    mes_nome = st.sidebar.selectbox("Selecione o mês", list(meses.values()), index=mes_atual - 1)
    mes = list(meses.keys())[list(meses.values()).index(mes_nome)]

    origens_disponiveis = ['Todos'] + sorted(df['Origem'].dropna().unique().tolist())
    origem_selecionada = st.sidebar.selectbox("Filtrar por Origem", origens_disponiveis)
    
    # NOVO BOTÃO: Ver Detalhes da Origem (abre URL em nova aba)
    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 Ver Detalhes da Origem", key="origin_details_button"):
        # Substitua pela URL desejada - incluindo parâmetro da origem selecionada
        url_detalhes = f"https://exemplo.com/detalhes-origem?origem={origem_selecionada.replace(' ', '%20')}"
        st.markdown(f"""
        <script>
            window.open('{url_detalhes}', '_blank');
        </script>
        """, unsafe_allow_html=True)

    if origem_selecionada != 'Todos':
        st.markdown(f"""
        <div class='filter-active'>
            <strong>Filtro Ativo:</strong> Mostrando apenas agendamentos da origem <strong>{origem_selecionada}</strong>
        </div>
        """, unsafe_allow_html=True)

    mostrar_calendario_mensal(df, mes, ano, origem_selecionada)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Resumo de Vagas**")

    if st.session_state.selected_date:
        df_filtrado = df[df['Data'].dt.date == st.session_state.selected_date]
        periodo = f"no dia {st.session_state.selected_date.strftime('%d/%m/%Y')}"
    else:
        df_filtrado = df[(df['Data'].dt.month == mes) & (df['Data'].dt.year == ano)]
        periodo = f"em {mes_nome} {ano}"

    if origem_selecionada != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Origem'] == origem_selecionada]
        periodo += f" (Origem: {origem_selecionada})"

    st.sidebar.metric(label=f"Total de Vagas {periodo}", value=len(df_filtrado))
    st.sidebar.metric(label="Profissionais distintos", value=df_filtrado['Especialidade'].nunique())
    st.sidebar.metric(label="Unidades atendidas", value=df_filtrado['Unidade'].nunique())
    st.sidebar.markdown("---")

    st.sidebar.markdown(
        """
        <div style="text-align: right; font-size: 3em; color: #777;">
            Desenvolvido por<br>
            <strong>Vinicius Viana</strong><br>
            <strong>V25.05.05 (Cloud)</strong>
        </div>
        """, 
        unsafe_allow_html=True
    )

    if not df_filtrado.empty:
        st.markdown(f"### 📋 Consultas {periodo}")
        if st.session_state.selected_date and st.button("Mostrar todos os agendamentos do mês"):
            st.session_state.selected_date = None
            st.rerun()

        st.dataframe(
            df_filtrado.sort_values(['Data', 'Hora']),
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Hora": st.column_config.TimeColumn("Hora", format="HH:mm")
            },
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            label="📥 Exportar para Excel",
            data=gerar_excel(df_filtrado),
            file_name=f"consultas_{mes_nome.lower()}_{ano}.xlsx" if not st.session_state.selected_date else f"consultas_{st.session_state.selected_date.strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
