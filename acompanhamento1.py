import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import chardet
import io

# Configuração da página
st.set_page_config(page_title="Dashboard de Agendamentos", layout="wide")

# Título do dashboard
st.title("📅 Dashboard de Agendamentos (Otimizado)")

# Função para detectar encoding de forma eficiente
def detect_encoding(uploaded_file, sample_size=1024*1024):  # 1MB sample
    rawdata = uploaded_file.read(sample_size)
    uploaded_file.seek(0)  # Reset file pointer
    return chardet.detect(rawdata)['encoding']

# Função para carregar e processar dados de forma otimizada
@st.cache_data
def load_data(uploaded_file):
    # 1. Detectar encoding com amostra menor
    encoding = detect_encoding(uploaded_file, sample_size=100000)  # 100KB sample
    
    # 2. Ler apenas colunas necessárias para economizar memória
    usecols = ['NOME Unidade executante', 'Data agenda', 'COD CBO', 'SITUAÇÃO']
    
    # 3. Definir tipos de dados para otimização
    dtype = {
        'COD CBO': 'category',
        'SITUAÇÃO': 'category',
        'NOME Unidade executante': 'category'
    }
    
    # 4. Ler em chunks se o arquivo for muito grande
    chunksize = 100000  # Ajuste conforme necessário
    chunks = []
    
    for chunk in pd.read_csv(
        uploaded_file,
        encoding=encoding,
        sep=';' if ';' in str(uploaded_file.read(1024)) else ',',
        usecols=usecols,
        dtype=dtype,
        chunksize=chunksize,
        parse_dates=['Data agenda'],
        infer_datetime_format=True,
        on_bad_lines='skip'
    ):
        # Filtrar TRA durante o carregamento
        chunk = chunk[chunk['SITUAÇÃO'] != 'TRA']
        chunks.append(chunk)
        
        # Atualizar progresso
        progress.progress(min(100, int(uploaded_file.tell() / uploaded_file.size * 100)))
    
    # Combinar chunks
    df = pd.concat(chunks, ignore_index=True)
    
    return df

# Upload do arquivo CSV
uploaded_file = st.file_uploader("Carregue seu arquivo CSV", type=["csv"])

if uploaded_file is not None:
    # Barra de progresso
    progress = st.progress(0)
    st.info("Processando arquivo... Por favor aguarde.")
    
    try:
        df = load_data(uploaded_file)
        progress.empty()
        
        # Verificar se as colunas necessárias existem
        required_columns = ['NOME Unidade executante', 'Data agenda', 'COD CBO', 'SITUAÇÃO']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Colunas não encontradas no arquivo: {', '.join(missing_columns)}")
        else:
            # Sidebar com filtros (mantido igual)
            st.sidebar.header("Filtros")
            
            # Filtro para Nome Unidade Executante (otimizado)
            unidades = df['NOME Unidade executante'].unique().tolist()
            unidades_selecionadas = st.sidebar.multiselect(
                'Unidade Executante',
                options=unidades,
                default=unidades[:3] if len(unidades) > 3 else unidades
            )
            
            # Filtro para Data da Agenda (otimizado)
            if df['Data agenda'].dtype == 'datetime64[ns]':
                min_date = df['Data agenda'].min().date()
                max_date = df['Data agenda'].max().date()
                datas_selecionadas = st.sidebar.date_input(
                    'Período da Agenda',
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                if len(datas_selecionadas) == 2:
                    df_filtrado = df[
                        (df['NOME Unidade executante'].isin(unidades_selecionadas)) &
                        (df['Data agenda'].dt.date >= datas_selecionadas[0]) &
                        (df['Data agenda'].dt.date <= datas_selecionadas[1])
                    ]
                else:
                    df_filtrado = df[df['NOME Unidade executante'].isin(unidades_selecionadas)]
            else:
                datas = df['Data agenda'].unique().tolist()
                datas_selecionadas = st.sidebar.multiselect(
                    'Data da Agenda',
                    options=datas,
                    default=datas[:3] if len(datas) > 3 else datas
                )
                df_filtrado = df[
                    (df['NOME Unidade executante'].isin(unidades_selecionadas)) &
                    (df['Data agenda'].isin(datas_selecionadas))
                ]
            
            # Filtro para COD CBO (otimizado)
            cbos = df_filtrado['COD CBO'].unique().tolist()
            cbos_selecionados = st.sidebar.multiselect(
                'CBO',
                options=cbos,
                default=cbos  # Todos selecionados por padrão
            )
            
            if cbos_selecionados:
                df_filtrado = df_filtrado[df_filtrado['COD CBO'].isin(cbos_selecionados)]
            
            # Cartões com contagem de situações (otimizado)
            st.header("Resumo de Situações")
            
            # Usando value_counts() para otimizar
            contagens = df_filtrado['SITUAÇÃO'].value_counts()
            contagem_rec = contagens.get('REC', 0)
            contagem_can = contagens.get('CAN', 0)
            contagem_age = contagens.get('AGE', 0)
            contagem_fal = contagens.get('FAL', 0)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(
                    f"""<div style="background-color:#4CAF50;padding:20px;border-radius:10px;color:white;">
                        <h3 style="color:white;">Realizados (REC)</h3>
                        <h1 style="color:white;text-align:center;">{contagem_rec}</h1>
                    </div>""",
                    unsafe_allow_html=True
                )
            
            with col2:
                st.markdown(
                    f"""<div style="background-color:#F44336;padding:20px;border-radius:10px;color:white;">
                        <h3 style="color:white;">Cancelados (CAN)</h3>
                        <h1 style="color:white;text-align:center;">{contagem_can}</h1>
                    </div>""",
                    unsafe_allow_html=True
                )
            
            with col3:
                st.markdown(
                    f"""<div style="background-color:#2196F3;padding:20px;border-radius:10px;color:white;">
                        <h3 style="color:white;">Agendados (AGE)</h3>
                        <h1 style="color:white;text-align:center;">{contagem_age}</h1>
                    </div>""",
                    unsafe_allow_html=True
                )
            
            with col4:
                st.markdown(
                    f"""<div style="background-color:#FFEB3B;padding:20px;border-radius:10px;color:black;">
                        <h3 style="color:black;">Faltas (FAL)</h3>
                        <h1 style="color:black;text-align:center;">{contagem_fal}</h1>
                    </div>""",
                    unsafe_allow_html=True
                )
            
            # Visualização otimizada dos dados filtrados
            st.header("Dados Filtrados (Amostra)")
            st.dataframe(df_filtrado.head(1000), height=300)  # Mostra apenas as primeiras 1000 linhas
            
            # Gráfico otimizado
            st.header("Distribuição das Situações")
            st.bar_chart(contagens)
            
            st.success(f"Processamento concluído! Total de registros: {len(df_filtrado):,}")
    
    except Exception as e:
        progress.empty()
        st.error(f"Erro ao processar o arquivo: {str(e)}")
else:
    st.info("Por favor, carregue um arquivo CSV para começar.")
