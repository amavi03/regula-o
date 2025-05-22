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
import io
import os
import subprocess
import time
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from urllib3.exceptions import MaxRetryError, NewConnectionError

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
    .invisible-button {
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        opacity: 0;
        cursor: pointer;
    }
    .day-container {
        position: relative;
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
    .debug-info {
        font-family: monospace;
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def get_chrome_version():
    try:
        # Tentativa para Windows
        if os.name == 'nt':
            try:
                process = subprocess.Popen(
                    ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
                )
                output, _ = process.communicate()
                version = output.decode('utf-8').split()[-1]
                return version.split('.')[0]
            except Exception as e:
                st.warning(f"Erro ao detectar versão no Windows: {str(e)}")
                pass
        
        # Tentativa para macOS
        if os.name == 'posix':
            try:
                process = subprocess.Popen(
                    ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
                )
                output, _ = process.communicate()
                version = output.decode('utf-8').split()[-1]
                return version.split('.')[0]
            except Exception as e:
                st.warning(f"Erro ao detectar versão no macOS: {str(e)}")
                pass
        
        # Tentativa para Linux
        try:
            process = subprocess.Popen(
                ['google-chrome', '--version'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
            )
            output, _ = process.communicate()
            version = output.decode('utf-8').split()[-1]
            return version.split('.')[0]
        except Exception as e:
            st.warning(f"Erro ao detectar versão no Linux: {str(e)}")
            pass
        
        return None
    except Exception as e:
        st.warning(f"Erro geral ao detectar versão do Chrome: {str(e)}")
        return None

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
        navegador = None
        try:
            chrome_options = Options()
            
            # Configurações para melhorar a estabilidade
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--dns-prefetch-disable')
            
            # Configuração do modo headless baseado no debug_mode
            if not debug_mode:
                if tentativa == 0:
                    chrome_options.add_argument('--headless=new')  # Modo headless moderno
                elif tentativa == 1:
                    chrome_options.add_argument('--headless')      # Modo headless tradicional
            
            # Configurações adicionais para depuração
            if debug_mode:
                chrome_options.add_argument('--remote-debugging-port=9222')
                chrome_options.add_experimental_option("detach", True)
                st.info("Modo de depuração ativo - O navegador permanecerá aberto")
            
            servico = Service(ChromeDriverManager().install())
            navegador = webdriver.Chrome(service=servico, options=chrome_options)
            
            # Timeouts aumentados
            navegador.set_page_load_timeout(45)
            navegador.set_script_timeout(45)
            
            username = os.getenv('VIVVER_USER', '123')
            password = os.getenv('VIVVER_PASS', '38355212')

            # Teste de conexão básica primeiro
            if debug_mode:
                st.write("⏳ Testando conexão básica com google.com...")
            navegador.get("https://www.google.com")
            
            if debug_mode:
                st.write("✅ Conexão básica OK. Acessando Vivver...")

            # Acessar página de login
            navegador.get('https://itabira-mg.vivver.com/login')
            
            # Espera dinâmica com verificações periódicas
            start_time = time.time()
            elemento_encontrado = False
            while time.time() - start_time < 30:
                try:
                    WebDriverWait(navegador, 5).until(
                        EC.presence_of_element_located((By.ID, 'conta')))
                    elemento_encontrado = True
                    break
                except:
                    if time.time() - start_time > 25:
                        raise TimeoutException("Timeout ao carregar elementos da página")
                    time.sleep(2)
                    continue
            
            if not elemento_encontrado:
                raise TimeoutException("Elementos da página não carregados")
            
            if debug_mode:
                st.write("✅ Página de login carregada. Preenchendo credenciais...")

            # Preencher credenciais com múltiplas tentativas
            for i in range(3):
                try:
                    conta = navegador.find_element(By.ID, 'conta')
                    conta.clear()
                    conta.send_keys(username)
                    break
                except Exception as e:
                    if i == 2:
                        raise
                    time.sleep(1)
            
            for i in range(3):
                try:
                    senha = navegador.find_element(By.ID, 'password')
                    senha.clear()
                    senha.send_keys(password)
                    break
                except Exception as e:
                    if i == 2:
                        raise
                    time.sleep(1)
            
            if debug_mode:
                st.write("✅ Credenciais preenchidas. Tentando login...")

            # Tentar clicar no botão de login de várias formas
            try:
                navegador.find_element(By.XPATH, '/html/body/div[1]/div/div/form/div[2]').click()
            except:
                navegador.execute_script("document.querySelector('form div[role=\"button\"]').click()")
            
            # Verificar se o login foi bem-sucedido
            WebDriverWait(navegador, 20).until(
                lambda driver: driver.current_url != 'https://itabira-mg.vivver.com/login')
            
            if debug_mode:
                st.write("✅ Login realizado com sucesso. Acessando API...")

            # Acessar a API com tratamento especial
            url_api = "https://itabira-mg.vivver.com/bit/gadget/view_paginate.json?id=228&draw=1&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=1&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=2&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=3&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=4&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=5&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=6&columns%5B6%5D%5Bname%5D=&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B7%5D%5Bdata%5D=7&columns%5B7%5D%5Bname%5D=&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=true&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B8%5D%5Bdata%5D=8&columns%5B8%5D%5Bname%5D=&columns%5B8%5D%5Bsearchable%5D=true&columns%5B8%5D%5Borderable%5D=true&columns%5B8%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B8%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B9%5D%5Bdata%5D=9&columns%5B9%5D%5Bname%5D=&columns%5B9%5D%5Bsearchable%5D=true&columns%5B9%5D%5Borderable%5D=true&columns%5B9%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B9%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B10%5D%5Bdata%5D=10&columns%5B10%5D%5Bname%5D=&columns%5B10%5D%5Bsearchable%5D=true&columns%5B10%5D%5Borderable%5D=true&columns%5B10%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B10%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B11%5D%5Bdata%5D=11&columns%5B11%5D%5Bname%5D=&columns%5B11%5D%5Bsearchable%5D=true&columns%5B11%5D%5Borderable%5D=true&columns%5B11%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B11%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&start=0&length=10000&search%5Bvalue%5D=&search%5Bregex%5D=false&_=1746727676517"
            
            for i in range(3):
                try:
                    navegador.get(url_api)
                    WebDriverWait(navegador, 20).until(
                        EC.presence_of_element_located((By.TAG_NAME, "pre")))
                    dados_json = navegador.find_element(By.TAG_NAME, "pre").text
                    dados = json.loads(dados_json)
                    
                    if debug_mode:
                        st.write("✅ Dados obtidos com sucesso!")
                        st.json(dados[:2])  # Mostrar amostra dos dados
                    
                    navegador.quit()
                    return dados
                except TimeoutException:
                    if i == 2:
                        raise
                    time.sleep(3)
                    continue
            
            raise TimeoutException("Não foi possível acessar a API após várias tentativas")
        
        except Exception as e:
            tentativa += 1
            if navegador is not None:
                try:
                    if debug_mode:
                        st.error(f"Erro na tentativa {tentativa}: {str(e)}")
                        st.write("📸 Captura de tela de erro:")
                        st.image(navegador.get_screenshot_as_png(), caption='Erro durante a execução')
                    navegador.quit()
                except:
                    pass
            
            if tentativa < max_tentativas:
                if debug_mode:
                    st.warning(f"Tentando novamente ({tentativa}/{max_tentativas})...")
                time.sleep(5)
            else:
                st.error(f"Falha na tentativa {tentativa}: {str(e)}")
                if "net::ERR_CONNECTION_TIMED_OUT" in str(e):
                    st.error("""
                    **Problema de timeout na conexão detectado. Possíveis soluções:**
                    1. Verifique sua conexão com a internet
                    2. O site pode estar temporariamente indisponível
                    3. Pode haver restrições de firewall/proxy
                    4. Tente novamente mais tarde
                    """)
                raise
    
    return None

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
def mostrar_calendario_mensal(df, origem_selecionada='Todos'):
    try:
        if origem_selecionada != 'Todos':
            df = df[df['Origem'] == origem_selecionada]
        
        # Ordenar por data e pegar os próximos 30 dias com vagas
        df = df.sort_values('Data')
        datas_unicas = df['Data'].dt.date.unique()
        
        # Pegar os próximos 30 dias com vagas (ou menos se não houver)
        proximos_30_dias = sorted(datas_unicas)[:30]
        
        # Determinar o intervalo de meses a mostrar
        meses_para_mostrar = set()
        for data in proximos_30_dias:
            meses_para_mostrar.add((data.month, data.year))
        
        # Configurações visuais
        hoje = datetime.now().date()
        st.subheader("Próximas Vagas Disponíveis (30 dias)")
        
        # Mostrar cada mês necessário
        for mes, ano in sorted(meses_para_mostrar):
            st.markdown(f"### {calendar.month_name[mes]} {ano}")
            
            # Filtrar dados para o mês atual
            df_mes = df[(df['Data'].dt.month == mes) & (df['Data'].dt.year == ano)]
            dias_com_vagas = df_mes['Data'].dt.day.unique()
            
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
                        data_atual = datetime(ano, mes, dia).date() if dia != 0 else None
                        
                        if dia == 0 or (data_atual not in proximos_30_dias):
                            st.write("")
                        else:
                            eventos_dia = df_mes[df_mes['Data'].dt.date == data_atual]
                            num_eventos = len(eventos_dia)
                            
                            # [Restante do código de formatação permanece igual...]
                            # Contar serviços específicos
                            ppi_count = eventos_dia['Serviço'].str.contains('PPI', case=False, na=False).sum()
                            cmce_count = eventos_dia['Serviço'].str.contains('CMCE', case=False, na=False).sum()
                            oncologia_count = eventos_dia['Serviço'].str.contains('ONCOLOGIA', case=False, na=False).sum()
                            glaucoma_count = eventos_dia['Serviço'].str.contains('GLAUCOMA', case=False, na=False).sum()

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

                            # Criar HTML para mostrar os contadores de serviços
                            servicos_html = ""
                            if ppi_count > 0:
                                servicos_html += f"<div style='color: #FF5733; font-size: 2em;'>PPI: {ppi_count}</div>"
                            if cmce_count > 0:
                                servicos_html += f"<div style='color: #33FF57; font-size: 2em;'>CMCE: {cmce_count}</div>"
                            if oncologia_count > 0:
                                servicos_html += f"<div style='color: #3357FF; font-size: 2em;'>ONCO: {oncologia_count}</div>"
                            if glaucoma_count > 0:
                                servicos_html += f"<div style='color: #3367FF; font-size: 2em;'>GLAU: {glaucoma_count}</div>"

                            # Construir o HTML do dia
                            day_html = f"""
                            <div class='day-container'>
                                <div class='calendar-day {selected_class}' 
                                    style='border: {border_width} solid {border_color}; 
                                    border-radius: 5px; padding: 8px; min-height: 80px; margin: 2px; 
                                    background-color: {bg_color}; color: {text_color}'>
                                    <div style='font-weight: bold; font-size: 1.1em;'>{dia}</div>
                                    <div style='font-size: 0.8em;'>{num_eventos} consulta(s)</div>
                            """

                            # Adicionar serviços apenas se houver algum
                            if servicos_html:
                                day_html += servicos_html

                            # Fechar as divs
                            day_html += """
                                </div>
                            </div>
                            """

                            st.markdown(day_html, unsafe_allow_html=True)

                            if st.button("", key=f"day_{dia}_{mes}_{ano}"):
                                st.session_state.selected_date = data_atual
                                st.rerun()
    except Exception as e:
        st.error(f"Erro ao gerar calendário: {str(e)}")

# --- FUNÇÃO PRINCIPAL ---
def main():
    st.title("📅 Acompanhamento de Vagas")

    # Configuração de debug
    debug_mode = st.sidebar.checkbox("🔍 Modo de Depuração", value=False,
                                    help="Ativa modo de depuração com mais informações e navegador visível")
    
    # Seção de diagnóstico
    with st.sidebar.expander("🔧 Diagnóstico do Sistema", expanded=False):
        st.write("**Informações do Sistema:**")
        
        chrome_version = get_chrome_version()
        st.write(f"- Versão do Chrome: {chrome_version if chrome_version else 'Não detectada'}")
        
        try:
            driver_version = ChromeDriverManager().driver_version
            st.write(f"- Versão do WebDriver: {driver_version}")
        except:
            st.write("- Versão do WebDriver: Não detectada")
        
        if st.button("🧪 Testar Conexão com Vivver"):
            with st.spinner("Testando conexão..."):
                status, mensagem = testar_conexao()
                st.markdown(f"""
                <div class='connection-test connection-{status}'>
                    {mensagem}
                </div>
                """, unsafe_allow_html=True)
                
                if status != "success":
                    st.warning("""
                    **Se o teste de conexão falhou:**
                    1. Verifique sua conexão com a internet
                    2. Tente acessar manualmente: [https://itabira-mg.vivver.com](https://itabira-mg.vivver.com)
                    3. Verifique configurações de firewall/proxy
                    """)

    # Botão para recarregar os dados
    if st.sidebar.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.session_state.selected_date = None
        st.rerun()

    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None

    # Carregar dados
    with st.spinner("Carregando dados..."):
        try:
            dados = carregar_dados_reais(debug_mode)
            df = processar_dados(dados)
        except Exception as e:
            st.error(f"Falha crítica ao carregar dados: {str(e)}")
            st.stop()

    if df.empty:
        st.warning("Nenhum dado foi carregado. Verifique a conexão ou as credenciais.")
        return

    # Filtros
    st.sidebar.header("Filtros")

    data_atual = datetime.now()
    ano_atual = data_atual.year
    mes_atual = data_atual.month

    anos_disponiveis = sorted(df['Data'].dt.year.unique(), reverse=True)
    if ano_atual not in anos_disponiveis:
        anos_disponiveis.insert(0, ano_atual)

    ano = st.sidebar.selectbox("Selecione o ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    mes_nome = st.sidebar.selectbox("Selecione o mês", list(meses.values()), index=mes_atual - 1)
    mes = list(meses.keys())[list(meses.values()).index(mes_nome)]

    origens_disponiveis = ['Todos'] + sorted(df['Origem'].dropna().unique().tolist())
    origem_selecionada = st.sidebar.selectbox("Filtrar por Origem", origens_disponiveis)

    if origem_selecionada != 'Todos':
        st.markdown(f"""
        <div class='filter-active'>
            <strong>Filtro Ativo:</strong> Mostrando apenas agendamentos da origem <strong>{origem_selecionada}</strong>
        </div>
        """, unsafe_allow_html=True)

    # Mostrar calendário
    mostrar_calendario_mensal(df, origem_selecionada)

    # Resumo na sidebar
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

    # Rodapé
    st.sidebar.markdown(
        """
        <div style="text-align: right; font-size: 3em; color: #777;">
            Desenvolvido por<br>
            <strong>Vinicius Viana</strong><br>
            <strong>V25.05.05</strong>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Mostrar dados filtrados
    if not df_filtrado.empty:
        st.markdown(f"### 📋 Vagas {periodo}")
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
            file_name=f"Vagas_{mes_nome.lower()}_{ano}.xlsx" if not st.session_state.selected_date else f"consultas_{st.session_state.selected_date.strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info(f"Nenhuma consulta agendada {periodo}.")

if __name__ == "__main__":
    main()
