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
    
    return holdings, funds

st.sidebar.markdown("# SEC Analiz")
menu = st.sidebar.radio("Menü", ["📊 Dashboard", "🏢 Fonlar", "📈 Hisseler"], label_visibility="collapsed")

if 'holdings' not in st.session_state:
    with st.spinner("Veriler yükleniyor..."):
        holdings, funds = load_data()
        for col in ['BALANCE', 'CURRENCY_VALUE', 'PERCENTAGE']:
            if col in holdings.columns:
                holdings[col] = pd.to_numeric(holdings[col], errors='coerce').fillna(0)
        st.session_state['holdings'] = holdings
        st.session_state['funds'] = funds
        st.sidebar.success(f"✅ {len(funds)} fon, {len(holdings):,} holding")

holdings = st.session_state['holdings']
funds = st.session_state['funds']
name_col = 'SERIES_NAME' if 'SERIES_NAME' in funds.columns else funds.columns[1]

def fmt_currency(x):
    if x >= 1e9:
        return f"${x/1e9:.2f}B"
    elif x >= 1e6:
        return f"${x/1e6:.2f}M"
    return f"${x:,.0f}"

if menu == "📊 Dashboard":
    st.markdown("## 📊 Dashboard")
    hisse_istatistik = holdings.groupby('ISSUER_NAME').agg({
        'ACCESSION_NUMBER': 'nunique',
        'CURRENCY_VALUE': 'sum'
    }).reset_index()
    hisse_istatistik.columns = ['Hisse', 'Fon Sayısı', 'Toplam Piyasa Değeri']
    hisse_istatistik = hisse_istatistik.sort_values('Fon Sayısı', ascending=False).head(20)
    
    # SADECE BURASI DEĞİŞTİ - BİNLİK AYRAÇ EKLENDİ
    display_df = hisse_istatistik.copy()
    display_df['Fon Sayısı'] = display_df['Fon Sayısı'].apply(lambda x: f"{int(x):,}")
    display_df['Toplam Piyasa Değeri'] = display_df['Toplam Piyasa Değeri'].apply(lambda x: f"${x:,.2f}")
    
    st.subheader("🏆 Fonlar Tarafından En Çok Tercih Edilen Hisseler")
    st.dataframe(display_df, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(hisse_istatistik.head(10), x='Hisse', y='Fon Sayısı', title="En Çok Fonda Bulunan Hisseler")
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(hisse_istatistik.head(10), x='Hisse', y='Toplam Piyasa Değeri', title="En Yüksek Piyasa Değeri")
        fig2.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig2, use_container_width=True)

elif menu == "🏢 Fonlar":
    st.markdown("## 🏢 Fonlar")
    fon_portfoy = holdings.groupby('ACCESSION_NUMBER').agg({
        'CURRENCY_VALUE': 'sum',
        'ISSUER_NAME': 'count'
    }).reset_index()
    fon_portfoy.columns = ['ACCESSION_NUMBER', 'Toplam Değer', 'Hisse Sayısı']
    fon_portfoy = fon_portfoy.merge(funds[['ACCESSION_NUMBER', name_col]], on='ACCESSION_NUMBER')
    fon_portfoy = fon_portfoy.sort_values('Toplam Değer', ascending=False).reset_index(drop=True)
    
    st.info(f"📊 Toplam {len(fon_portfoy):,} fon")
    arama = st.text_input("🔍 Fon ara")
    if arama:
        fon_portfoy = fon_portfoy[fon_portfoy[name_col].str.contains(arama, case=False, na=False)]
    
    for i, row in fon_portfoy.head(50).iterrows():
        col1, col2, col3 = st.columns([3, 1.5, 1])
        with col1:
            st.write(row[name_col][:60])
        with col2:
            st.write(fmt_currency(row['Toplam Değer']))
        with col3:
            st.write(f"{int(row['Hisse Sayısı']):,}")
        st.divider()

elif menu == "📈 Hisseler":
    st.markdown("## 📈 Hisseler")
    tum_hisseler = sorted(holdings['ISSUER_NAME'].dropna().unique())
    st.info(f"📊 Toplam {len(tum_hisseler):,} farklı hisse")
    hisse_arama = st.text_input("🔍 Hisse ara")
    if hisse_arama:
        tum_hisseler = [h for h in tum_hisseler if hisse_arama.upper() in h.upper()]
    if tum_hisseler:
        secilen_hisse = st.selectbox("Bir hisse seçin", tum_hisseler)
        if secilen_hisse:
            hisse_fonlar = holdings[holdings['ISSUER_NAME'] == secilen_hisse].merge(
                funds[['ACCESSION_NUMBER', name_col]], on='ACCESSION_NUMBER'
            )
            hisse_fonlar = hisse_fonlar.groupby(name_col).agg({
                'BALANCE': 'sum',
                'CURRENCY_VALUE': 'sum'
            }).reset_index()
            hisse_fonlar = hisse_fonlar.sort_values('BALANCE', ascending=False)
            st.success(f"✅ {secilen_hisse} hissesini tutan {len(hisse_fonlar):,} fon")
            if not hisse_fonlar.empty:
                fig = px.bar(hisse_fonlar.head(10), x=name_col, y='BALANCE', title="En Çok Pozisyona Sahip Fonlar")
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
                hisse_fonlar['BALANCE'] = hisse_fonlar['BALANCE'].apply(lambda x: f"{int(x):,}")
                hisse_fonlar['CURRENCY_VALUE'] = hisse_fonlar['CURRENCY_VALUE'].apply(fmt_currency)
                st.dataframe(hisse_fonlar, use_container_width=True)
