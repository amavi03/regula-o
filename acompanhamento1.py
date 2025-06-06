import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard de Agendamentos", layout="wide")

# Título do dashboard
st.title("📅 Dashboard de Agendamentos")

# Função para carregar dados
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file, encoding='latin1', sep=';' if ';' in uploaded_file.getvalue().decode('latin1')[:100] else ',')
    
    # Verificar e converter coluna de data se necessário
    if 'Data agenda' in df.columns:
        try:
            df['Data agenda'] = pd.to_datetime(df['Data agenda'], errors='coerce')
        except:
            pass
    
    return df

# Upload do arquivo CSV
uploaded_file = st.file_uploader("Carregue seu arquivo CSV", type=["csv"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    # Verificar se as colunas necessárias existem
    required_columns = ['NOME Unidade executante', 'Data agenda', 'COD CBO', 'SITUAÇÃO']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Colunas não encontradas no arquivo: {', '.join(missing_columns)}")
    else:
        # Sidebar com filtros
        st.sidebar.header("Filtros")
        
        # Filtro para Nome Unidade Executante
        unidades = sorted(df['NOME Unidade executante'].unique())
        unidades_selecionadas = st.sidebar.multiselect(
            'Unidade Executante',
            options=unidades,
            default=unidades[:3] if len(unidades) > 3 else unidades
        )
        
        # Filtro para Data da Agenda
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
            datas = sorted(df['Data agenda'].unique())
            datas_selecionadas = st.sidebar.multiselect(
                'Data da Agenda',
                options=datas,
                default=datas[:3] if len(datas) > 3 else datas
            )
            df_filtrado = df[
                (df['NOME Unidade executante'].isin(unidades_selecionadas)) &
                (df['Data agenda'].isin(datas_selecionadas))
            ]
        
        # Filtro para COD CBO
        cbos = sorted(df_filtrado['COD CBO'].unique())
        cbos_selecionados = st.sidebar.multiselect(
            'CBO',
            options=cbos,
            default=cbos[:3] if len(cbos) > 3 else cbos
        )
        
        if cbos_selecionados:
            df_filtrado = df_filtrado[df_filtrado['COD CBO'].isin(cbos_selecionados)]
        
        # Cartões com contagem de situações
        st.header("Resumo de Situações")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Contagem de cada SITUAÇÃO
        contagem_rec = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'REC'])
        contagem_can = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'CAN'])
        contagem_age = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'AGE'])
        contagem_fal = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'FAL'])
        
        with col1:
            st.metric(label="Realizados (REC)", value=contagem_rec)
        
        with col2:
            st.metric(label="Cancelados (CAN)", value=contagem_can)
        
        with col3:
            st.metric(label="Agendados (AGE)", value=contagem_age)
        
        with col4:
            st.metric(label="Faltas (FAL)", value=contagem_fal)
        
        # Visualização dos dados filtrados
        st.header("Dados Filtrados")
        st.dataframe(df_filtrado, height=300)
        
        # Gráfico de distribuição das situações
        st.header("Distribuição das Situações")
        st.bar_chart(df_filtrado['SITUAÇÃO'].value_counts())
else:
    st.info("Por favor, carregue um arquivo CSV para começar.")
