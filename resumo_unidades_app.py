import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 1. Configurações Iniciais da Página
st.set_page_config(page_title="Gestão Milagres Cloud", layout="wide")
st_autorefresh(interval=600000, key="datarefresh")

# --- CSS SEGURO PARA COMPATIBILIDADE CLOUD ---
st.markdown("""
    <style>
        .header-style { font-weight: bold; color: #888; font-size: 13px; text-transform: uppercase; margin-bottom: 5px; }
        .stTable { background-color: #1a1c23; padding: 10px; border-radius: 5px; border: 1px solid #333; margin-top: 5px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# Cabeçalho Principal
st.markdown("<h1 style='text-align: center; color: white; font-family: sans-serif; margin-bottom: 30px;'>Monitoramento Cloud - Gestão Milagres</h1>", unsafe_allow_html=True)

# 2. Função de Formatação Contábil
def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

# 3. CONEXÃO DIRETA VIA PANDAS (À PROVA DE ERRO 400)
@st.cache_data(ttl=300)
def carregar_dados_direto():
    try:
        # ID único da sua planilha
        sheet_id = "1d_TbFNuJKBtBK-7rfMstsQcrtnCYQLw-47vZK92JWdY"
        
        # Gerando URLs de exportação direta em CSV para cada aba
        url_detalhe = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=detalhamento"
        url_pacientes = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=pacientes"
        url_tipos = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=tipos"
        
        # Lendo os dados ignorando erros de parser do Streamlit
        df_equip = pd.read_csv(url_detalhe)
        df_pacientes = pd.read_csv(url_pacientes)
        df_tipo = pd.read_csv(url_tipos)

        # Limpeza financeira básica
        for col in ['Valor Total', 'Valor Unitario']:
            if col in df_equip.columns:
                df_equip[col] = df_equip[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                df_equip[col] = pd.to_numeric(df_equip[col], errors='coerce').fillna(0)

        # Tratamento de texto para o casamento (Merge)
        df_equip['Paciente'] = df_equip['Paciente'].astype(str).str.strip().str.upper()
        df_pacientes['Paciente'] = df_pacientes['Paciente'].astype(str).str.strip().str.upper()
        df_equip['Equipamento'] = df_equip['Equipamento'].astype(str).str.strip().str.upper()
        df_tipo['Equipamento'] = df_tipo['Equipamento'].astype(str).str.strip().str.upper()

        df_pacientes = df_pacientes.drop_duplicates(subset=['Paciente'])
        df_tipo = df_tipo.drop_duplicates(subset=['Equipamento'])

        df_merge1 = pd.merge(df_equip, df_pacientes[['Paciente', 'Operadora', 'Tipo de Atendimento']], on='Paciente', how='left')
        df_final = pd.merge(df_merge1, df_tipo[['Equipamento', 'Tipo']], on='Equipamento', how='left')

        df_final['Operadora'] = df_final['Operadora'].fillna('NÃO LOCALIZADA')
        df_final['Tipo de Atendimento'] = df_final['Tipo de Atendimento'].fillna('NÃO INFORMADO')
        df_final['Tipo'] = df_final['Tipo'].fillna('NÃO CLASSIFICADO')
        
        return df_final
    except Exception as e:
        st.error(f"Erro ao ler dados da planilha pública: {e}")
        return pd.DataFrame()

df_raw = carregar_dados_direto()

if not df_raw.empty:
    # --- FILTROS POR UNIDADE ---
    st.markdown("### 📍 Selecionar Unidade")
    filiais = ["TODAS"] + sorted([str(f) for f in df_raw['Filial'].unique() if pd.notna(f)])
    if 'filial_ativa' not in st.session_state: st.session_state.filial_ativa = "TODAS"
    
    cols_btn = st.columns(len(filiais))
    for i, f in enumerate(filiais):
        if cols_btn[i].button(f, use_container_width=True, type="primary" if st.session_state.filial_ativa == f else "secondary"):
            st.session_state.filial_ativa = f
            st.rerun()

    df_filt = df_raw if st.session_state.filial_ativa == "TODAS" else df_raw[df_raw['Filial'] == st.session_state.filial_ativa]

  # --- BLOCOS DE RESUMO SUPERIORES (AJUSTADOS SEM BARRA DE ROLAGEM) ---
    st.markdown("### 📊 Resumo por Categoria")
    c1, c2, c3, c4 = st.columns(4)
    
    def gerar_resumo_com_total(df, grupo, col_nome):
        res = df.groupby(grupo).agg({'Paciente': 'nunique', 'Valor Total': 'sum'}).reset_index()
        res = res.sort_values('Valor Total', ascending=False)
        res.columns = [col_nome, 'Qtd Pac.', 'Total']  # Abreviações cirúrgicas para caber em telas menores
        total = pd.DataFrame([{col_nome: 'TOTAL', 'Qtd Pac.': res['Qtd Pac.'].sum(), 'Total': res['Total'].sum()}])
        res = pd.concat([res, total], ignore_index=True)
        res['Total'] = res['Total'].apply(formatar_moeda)
        return res

    with c1:
        st.write("**🏢 Operadoras**")
        st.dataframe(
            gerar_resumo_com_total(df_filt, 'Operadora', 'Operadora'), 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Operadora": st.column_config.TextColumn("Operadora", width="medium"),
                "Qtd Pac.": st.column_config.NumberColumn(width="small"),
                "Total": st.column_config.TextColumn(width="small")
            }
        )
    with c2:
        st.write("**🚑 Atendimento**")
        st.dataframe(
            gerar_resumo_com_total(df_filt, 'Tipo de Atendimento', 'Atendimento'), 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Atendimento": st.column_config.TextColumn("Atendimento", width="medium"),
                "Qtd Pac.": st.column_config.NumberColumn(width="small"),
                "Total": st.column_config.TextColumn(width="small")
            }
        )
    with c3:
        st.write("**🚚 Locadora**")
        st.dataframe(
            gerar_resumo_com_total(df_filt, 'Locadora', 'Locadora'), 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Locadora": st.column_config.TextColumn("Locadora", width="medium"),
                "Qtd Pac.": st.column_config.NumberColumn(width="small"),
                "Total": st.column_config.TextColumn(width="small")
            }
        )
    with c4:
        st.write("**🔧 Tipo de Item**")
        st.dataframe(
            gerar_resumo_com_total(df_filt, 'Tipo', 'Tipo de Item'), 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Tipo de Item": st.column_config.TextColumn("Tipo de Item", width="medium"),
                "Qtd Pac.": st.column_config.NumberColumn(width="small"),
                "Total": st.column_config.TextColumn(width="small")
            }
        )

    # --- DETALHAMENTO POR PACIENTE ---
    st.divider()
    st.markdown(f"### 👥 Detalhamento por Paciente - {st.session_state.filial_ativa}")
    
    h = st.columns([5, 1, 1.5])
    h[0].markdown('<p class="header-style">Paciente</p>', unsafe_allow_html=True)
    h[1].markdown('<p class="header-style" style="text-align: center;">Itens</p>', unsafe_allow_html=True)
    h[2].markdown('<p class="header-style" style="text-align: right;">Total</p>', unsafe_allow_html=True)

    df_lista = df_filt.groupby('Paciente').agg({'Equipamento': 'count', 'Valor Total': 'sum'}).reset_index().sort_values('Paciente')
    if 'expander_states' not in st.session_state: st.session_state.expander_states = {}

    for _, row in df_lista.iterrows():
        nome_p, qtd_i, total_p = row['Paciente'], str(row['Equipamento']), formatar_moeda(row['Valor Total'])
        if nome_p not in st.session_state.expander_states: st.session_state.expander_states[nome_p] = False
        
        c = st.columns([5, 1, 1.5])
        if c[0].button(f"▼ {nome_p}", key=f"n_{nome_p}", use_container_width=True):
            st.session_state.expander_states[nome_p] = not st.session_state.expander_states[nome_p]
            st.rerun()
        if c[1].button(qtd_i, key=f"q_{nome_p}", use_container_width=True):
            st.session_state.expander_states[nome_p] = not st.session_state.expander_states[nome_p]
            st.rerun()
        if c[2].button(total_p, key=f"v_{nome_p}", use_container_width=True):
            st.session_state.expander_states[nome_p] = not st.session_state.expander_states[nome_p]
            st.rerun()

        if st.session_state.expander_states[nome_p]:
            df_det = df_filt[df_filt['Paciente'] == nome_p][['Equipamento', 'Tipo', 'Qtd', 'Valor Unitario', 'Valor Total', 'Locadora', 'Operadora', 'Tipo de Atendimento']].copy()
            df_det['Valor Unitario'] = df_det['Valor Unitario'].apply(formatar_moeda)
            df_det['Valor Total'] = df_det['Valor Total'].apply(formatar_moeda)
            df_det.columns = ['Equipamento', 'Tipo de Item', 'Qtd', 'Valor Unitário', 'Valor Total', 'Locadora', 'Operadora', 'Tipo de Atendimento']
            st.table(df_det)
else:
    st.warning("Aguardando carregamento inicial da planilha na nuvem...")
