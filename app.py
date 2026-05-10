import streamlit as st
import pandas as pd
import plotly.express as px
import glob

st.set_page_config(page_title="SEC Fon Analiz", layout="wide")
st.markdown("# 📊 SEC Fon Analiz Sistemi")

@st.cache_data
def load_data():
    part_files = sorted(glob.glob("holding_part_*.tsv"))
    if not part_files:
        st.error("Holding parçaları bulunamadı!")
        return None, None
    
    df_list = []
    for f in part_files:
        df_list.append(pd.read_csv(f, delimiter='\t', low_memory=False))
    
    holdings = pd.concat(df_list, ignore_index=True)
    funds = pd.read_csv("info.tsv", delimiter='\t', low_memory=False)
    
    # LEI birleştirme
    if 'ISSUER_LEI' in holdings.columns:
        lei_map = {}
        for idx, row in holdings[holdings['ISSUER_LEI'].notna() & (holdings['ISSUER_LEI'] != '')].iterrows():
            if row['ISSUER_NAME'] not in lei_map:
                lei_map[row['ISSUER_NAME']] = row['ISSUER_LEI']
        
        def get_key(row):
            lei = row.get('ISSUER_LEI')
            name = row['ISSUER_NAME']
            if pd.notna(lei) and str(lei) != '' and str(lei) != 'nan':
                return lei
            if name in lei_map:
                return lei_map[name]
            return name
        
        holdings['GROUP_KEY'] = holdings.apply(get_key, axis=1)
        name_map = {}
        for key, group in holdings.groupby('GROUP_KEY'):
            name_map[key] = group['ISSUER_NAME'].value_counts().index[0]
        holdings['DISPLAY_NAME'] = holdings['GROUP_KEY'].map(name_map)
    else:
        holdings['DISPLAY_NAME'] = holdings['ISSUER_NAME']
    
    for col in ['BALANCE', 'CURRENCY_VALUE', 'PERCENTAGE']:
        if col in holdings.columns:
            holdings[col] = pd.to_numeric(holdings[col], errors='coerce').fillna(0)
    
    return holdings, funds

st.sidebar.markdown("# SEC Analiz")
menu = st.sidebar.radio("Navigation", ["📊 Dashboard", "🏢 Fonlar", "📈 Hisseler"], label_visibility="collapsed")

if 'holdings' not in st.session_state:
    with st.spinner("Veriler yükleniyor..."):
        holdings, funds = load_data()
        if holdings is None:
            st.stop()
        st.session_state['holdings'] = holdings
        st.session_state['funds'] = funds
        st.session_state['name_col'] = 'SERIES_NAME' if 'SERIES_NAME' in funds.columns else funds.columns[1]
        st.sidebar.success(f"✅ {len(funds):,} fon, {len(holdings):,} holding")

holdings = st.session_state['holdings']
funds = st.session_state['funds']
name_col = st.session_state['name_col']

def fmt_currency(x):
    return f"${x:,.2f}"

def fmt_number(x):
    return f"{x:,.0f}"

if menu == "📊 Dashboard":
    st.markdown("## 📊 Dashboard")
    hisse_stats = holdings.groupby('DISPLAY_NAME').agg({
        'ACCESSION_NUMBER': 'nunique',
        'CURRENCY_VALUE': 'sum'
    }).reset_index()
    hisse_stats.columns = ['Hisse', 'Fon Sayısı', 'Toplam Piyasa Değeri']
    hisse_stats = hisse_stats.sort_values('Fon Sayısı', ascending=False).head(20)
    
    display_df = hisse_stats.copy()
    display_df['Fon Sayısı'] = display_df['Fon Sayısı'].apply(fmt_number)
    display_df['Toplam Piyasa Değeri'] = display_df['Toplam Piyasa Değeri'].apply(fmt_currency)
    st.dataframe(display_df, width='stretch')
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(hisse_stats.head(10), x='Hisse', y='Fon Sayısı', title="En Çok Fonda Bulunan Hisseler")
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(hisse_stats.head(10), x='Hisse', y='Toplam Piyasa Değeri', title="En Yüksek Piyasa Değeri")
        fig2.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig2, use_container_width=True)

elif menu == "🏢 Fonlar":
    st.markdown("## 🏢 Fonlar")
    fon_portfoy = holdings.groupby('ACCESSION_NUMBER').agg({
        'CURRENCY_VALUE': 'sum',
        'DISPLAY_NAME': 'count'
    }).reset_index()
    fon_portfoy.columns = ['ACCESSION_NUMBER', 'Toplam Değer', 'Hisse Sayısı']
    fon_portfoy = fon_portfoy.merge(funds[['ACCESSION_NUMBER', name_col]], on='ACCESSION_NUMBER')
    fon_portfoy = fon_portfoy.sort_values('Toplam Değer', ascending=False).head(50)
    
    for i, row in fon_portfoy.iterrows():
        st.write(f"**{row[name_col][:50]}** | {fmt_currency(row['Toplam Değer'])} | {fmt_number(row['Hisse Sayısı'])} hisse")

elif menu == "📈 Hisseler":
    st.markdown("## 📈 Hisseler")
    tum_hisseler = sorted(holdings['DISPLAY_NAME'].dropna().unique())
    secilen = st.selectbox("Hisse seçin", tum_hisseler[:100])
    if secilen:
        hisse_data = holdings[holdings['DISPLAY_NAME'] == secilen].merge(
            funds[['ACCESSION_NUMBER', name_col]], on='ACCESSION_NUMBER'
        )
        st.success(f"{secilen}: {len(hisse_data)} fon")
        display_hisse = hisse_data[[name_col, 'BALANCE', 'CURRENCY_VALUE']].head(20).copy()
        display_hisse['BALANCE'] = display_hisse['BALANCE'].apply(fmt_number)
        display_hisse['CURRENCY_VALUE'] = display_hisse['CURRENCY_VALUE'].apply(fmt_currency)
        st.dataframe(display_hisse, width='stretch')
