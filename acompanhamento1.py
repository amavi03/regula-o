import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard de Agendamentos", layout="wide")

# Título do dashboard
st.title("📅 Dashboard de Agendamentos")

# Função para carregar e processar dados
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file, encoding='latin1', sep=';' if ';' in uploaded_file.getvalue().decode('latin1')[:100] else ',')
    
    # Verificar e converter coluna de data se necessário
    if 'Data agenda' in df.columns:
        try:
            df['Data agenda'] = pd.to_datetime(df['Data agenda'], errors='coerce')
        except:
            pass
    
    # Remover registros com situação TRA
    if 'SITUAÇÃO' in df.columns:
        df = df[df['SITUAÇÃO'] != 'TRA']
    
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
        
        # Filtro para COD CBO - TODOS PRÉ-SELECIONADOS POR PADRÃO
        cbos = sorted(df_filtrado['COD CBO'].unique())
        cbos_selecionados = st.sidebar.multiselect(
            'CBO',
            options=cbos,
            default=cbos  # Todos selecionados por padrão
        )
        
        if cbos_selecionados:
            df_filtrado = df_filtrado[df_filtrado['COD CBO'].isin(cbos_selecionados)]
        
        # Cartões com contagem de situações
        st.header("Resumo de Situações")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Contagem de cada SITUAÇÃO (TRA já foi removido)
        contagem_rec = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'REC'])
        contagem_can = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'CAN'])
        contagem_age = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'AGE'])
        contagem_fal = len(df_filtrado[df_filtrado['SITUAÇÃO'] == 'FAL'])
        
        with col1:
            # Cartão REC - Verde
            st.markdown(
                f"""
                <div style="background-color:#4CAF50;padding:20px;border-radius:10px;color:white;">
                    <h3 style="color:white;">Realizados (REC)</h3>
                    <h1 style="color:white;text-align:center;">{contagem_rec}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            # Cartão CAN - Vermelho
            st.markdown(
                f"""
                <div style="background-color:#F44336;padding:20px;border-radius:10px;color:white;">
                    <h3 style="color:white;">Cancelados (CAN)</h3>
                    <h1 style="color:white;text-align:center;">{contagem_can}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            # Cartão AGE - Azul
            st.markdown(
                f"""
                <div style="background-color:#2196F3;padding:20px;border-radius:10px;color:white;">
                    <h3 style="color:white;">Agendados (AGE)</h3>
                    <h1 style="color:white;text-align:center;">{contagem_age}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col4:
            # Cartão FAL - Amarelo (apenas FAL agora)
            st.markdown(
                f"""
                <div style="background-color:#FFEB3B;padding:20px;border-radius:10px;color:black;">
                    <h3 style="color:black;">Faltas (FAL)</h3>
                    <h1 style="color:black;text-align:center;">{contagem_fal}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Visualização dos dados filtrados
        st.header("Dados Filtrados")
        st.dataframe(df_filtrado, height=300)
        
        # Gráfico de distribuição das situações
        st.header("Distribuição das Situações")
        st.bar_chart(df_filtrado['SITUAÇÃO'].value_counts())
        
        # Adicionando informação sobre os dados filtrados
        st.info(f"Total de registros analisados: {len(df_filtrado)} | Registros TRA (transferidos) foram removidos da análise")
else:
    st.info("Por favor, carregue um arquivo CSV para começar.")
