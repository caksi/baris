import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="MNT - Nükleer Tıp Final Finansal Model", layout="wide", page_icon="☢️")

# --- STİL ---
st.markdown("""
<style>
    div.block-container { padding-top: 2rem; }
    .stMetric > div[data-testid="stMetricValue"] { font-size: 24px; }
</style>
""", unsafe_allow_html=True)

st.title("☢️ MNT | Nükleer Tıp Final Finansal Model (Tam ve Hata Giderilmiş)")

# ==========================================
# YAN MENÜ: PARAMETRELER
# ==========================================
with st.sidebar:
    st.header("⚙️ Global Ayarlar")

    secilen_senaryo = st.radio("📌 Analiz Senaryosu:", ["Kötümser", "Beklenen", "İyimser"], index=1)
    sure_yil = st.slider("Projeksiyon Süresi (Yıl)", 5, 15, 10)

    st.subheader("1. Finansal Varsayımlar")
    iskonto_orani = st.number_input("İskonto Oranı (NPV için %)", value=25.0, min_value=0.0) / 100
    kurumlar_vergisi = st.number_input("Kurumlar Vergisi (%)", value=25.0, min_value=0.0) / 100

    st.subheader("2. Kur & Enflasyon")
    usd_kur = st.number_input("USD Kuru", value=34.5, min_value=1.0)
    eur_kur = st.number_input("EUR Kuru", value=36.2, min_value=1.0)
    enflasyon = st.number_input("Yıllık Genel Enflasyon (%)", value=45.0, min_value=0.0) / 100

    st.divider()

    st.subheader("3. Ortaklık Yapısı")
    ortak1_oran = st.number_input("Ortak A Payı (%)", value=60.0, min_value=0.0, max_value=100.0)
    ortak2_oran = 100 - ortak1_oran
    st.info(f"Ortak B Payı: **%{ortak2_oran:.0f}**")

    # Operasyonel Ayarlar
    st.subheader("4. Operasyonel Ayarlar")
    calisma_gunu = st.number_input("Aylık Çalışma Günü", value=24, min_value=1, max_value=30)
    verimlilik = st.slider("Cihaz Aktiflik Oranı (%)", 80, 100, 95) / 100


# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================

def get_inflation_factor(year, rate):
    return (1 + rate) ** (year - 1)


def calculate_depreciation(df_capex, sure_yil, usd_kur, eur_kur):
    """Her bir yatırım kaleminin yıllık amortismanını hesaplar."""
    yillik_amortisman = np.zeros(sure_yil)
    if df_capex.empty:
        return yillik_amortisman

    for _, row in df_capex.iterrows():
        # Güvenli erişim
        kur = eur_kur if row.get("Döviz") == "EUR" else (usd_kur if row.get("Döviz") == "USD" else 1.0)
        tutar_tl = row.get("Tutar", 0) * kur
        sure = row.get("Amortisman Süresi (Yıl)", 1)

        if sure > 0:
            yillik_tutari = tutar_tl / sure
            for y in range(min(int(sure), sure_yil)):
                yillik_amortisman[y] += yillik_tutari
    return yillik_amortisman


def calculate_interest(df_finansman, sure_yil):
    """Faiz Gideri Hesaplaması (DÜZELTİLMİŞ FONKSİYON)"""
    yillik_faiz_gideri = np.zeros(sure_yil)
    if df_finansman.empty or df_finansman.iloc[0].isnull().all():
        return yillik_faiz_gideri

    # Güvenli okuma ve TAM SAYI'ya (int) dönüştürme:
    kredi_tutar = df_finansman.iloc[0].get("Kredi/Leasing Tutar (TL)", 0)
    faiz_orani = df_finansman.iloc[0].get("Faiz Oranı (%)", 0) / 100

    # Hata giderildi: float64'ten int'e dönüştürülüyor
    geri_odeme_sure = int(df_finansman.iloc[0].get("Geri Ödeme Süresi (Yıl)", 1))
    baslangic_yili = int(df_finansman.iloc[0].get("Başlangıç Yılı", 1))

    if geri_odeme_sure > 0:
        toplam_faiz = kredi_tutar * faiz_orani * geri_odeme_sure
        yillik_faiz = toplam_faiz / geri_odeme_sure

        # Hata giderildi: range() fonksiyonunun argümanları tam sayı olmalı
        for y in range(baslangic_yili - 1, min(geri_odeme_sure + baslangic_yili - 1, sure_yil)):
            if y < sure_yil:
                yillik_faiz_gideri[y] = yillik_faiz

    return yillik_faiz_gideri


# ==========================================
# TAB YAPISI VE GİRİŞLER
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["💰 Yatırım (CAPEX)", "🏦 Finansman", "⚙️ İşletme (OPEX)", "📈 Gelirler", "📊 FİNANSAL RAPOR"])

# --- TAB 1: CAPEX ---
with tab1:
    st.subheader("Yatırım Kalemleri")
    capex_df = pd.DataFrame([
        {"Kalem": "PET/CT Cihazı", "Tutar": 1150000, "Döviz": "EUR", "Amortisman Süresi (Yıl)": 7},
        {"Kalem": "İnşaat & Kurşunlama", "Tutar": 4500000, "Döviz": "TL", "Amortisman Süresi (Yıl)": 10},
    ])
    edited_capex = st.data_editor(capex_df, num_rows="dynamic", use_container_width=True)

    toplam_capex_tl = 0
    if not edited_capex.empty:
        for _, row in edited_capex.iterrows():
            kur = eur_kur if row.get("Döviz") == "EUR" else (usd_kur if row.get("Döviz") == "USD" else 1.0)
            toplam_capex_tl += row.get("Tutar", 0) * kur
    st.metric("Toplam Yatırım (TL)", f"{toplam_capex_tl:,.0f} ₺")

# --- TAB 2: FİNANSMAN ---
with tab2:
    st.subheader("🏦 Kredi & Finansman Giderleri")
    finansman_df = pd.DataFrame([
        {"Kredi/Leasing Tutar (TL)": 3000000, "Faiz Oranı (%)": 35.0, "Geri Ödeme Süresi (Yıl)": 5,
         "Başlangıç Yılı": 1},
    ])
    edited_finansman = st.data_editor(finansman_df, num_rows=1, use_container_width=True)

# --- TAB 3: OPEX ---
with tab3:
    col_p, col_g = st.columns(2)
    with col_p:
        st.subheader("👥 Personel Giderleri")
        personel_df = pd.DataFrame([
            {"Pozisyon": "Nükleer Tıp Uzmanı", "Adet": 1, "Brüt Maaş (TL)": 140000, "Yıllık Artış (%)": 45},
        ])
        edited_personel = st.data_editor(personel_df, num_rows="dynamic", use_container_width=True)

    with col_g:
        st.subheader("🏢 İşletme Giderleri")
        opex_df = pd.DataFrame([
            {"Gider": "Radyofarmasötik (FDG)", "Tip": "Değişken (Hasta Başı)", "Tutar (TL)": 2200, "Artış (%)": 40},
            {"Gider": "Bakım Anlaşması", "Tip": "Sabit (Aylık)", "Tutar (TL)": 120000, "Artış (%)": 50},
        ])
        edited_opex = st.data_editor(opex_df, num_rows="dynamic", use_container_width=True)

# --- TAB 4: GELİRLER ---
with tab4:
    st.subheader("📈 Gelir Projeksiyonu")
    gelir_df = pd.DataFrame([
        {"Hizmet": "PET/CT (Onkoloji)", "Fiyat (TL)": 5500, "Kötümser (Günlük)": 8, "Beklenen (Günlük)": 15,
         "İyimser (Günlük)": 25},
    ])
    edited_gelir = st.data_editor(gelir_df, num_rows="dynamic", use_container_width=True)

# ==========================================
# TAB 5: FİNANSAL RAPOR (ANA HESAPLAMA)
# ==========================================
with tab5:
    st.markdown("### 🔍 Analiz Başlatılıyor...")

    # --- HESAPLAMA MOTORU GİRİŞ DEĞERLERİ ---
    yillik_amortisman_listesi = calculate_depreciation(edited_capex, sure_yil, usd_kur, eur_kur)
    yillik_faiz_gideri = calculate_interest(edited_finansman, sure_yil)

    years = list(range(1, sure_yil + 1))
    nakit_akisi = []
    kumulatif = -toplam_capex_tl
    npv_toplam = -toplam_capex_tl

    if toplam_capex_tl == 0 and not edited_capex.empty:
        st.error("Lütfen yatırım tutarı giriniz.")
    elif edited_gelir.empty:
        st.warning("Lütfen gelir kalemlerini giriniz.")
    else:
        for y in years:
            y_index = y - 1
            inf_factor = get_inflation_factor(y, enflasyon)

            # --- GELİR HESABI ---
            yillik_gelir = 0
            yillik_toplam_hasta = 0
            efektif_gun = calisma_gunu * verimlilik * 12

            for _, row in edited_gelir.iterrows():
                gunluk_hasta = row.get(f"{secilen_senaryo} (Günlük)", 0)
                if gunluk_hasta > 0:
                    yillik_hizmet_geliri = (gunluk_hasta * efektif_gun * (row.get("Fiyat (TL)", 0) * inf_factor))
                    yillik_gelir += yillik_hizmet_geliri
                    yillik_toplam_hasta += (gunluk_hasta * efektif_gun)

            # --- GİDER HESABI ---
            yillik_personel = 0
            for _, row in edited_personel.iterrows():
                pers_inf = get_inflation_factor(y, row.get("Yıllık Artış (%)", 0) / 100)
                yillik_personel += (row.get("Brüt Maaş (TL)", 0) * pers_inf) * 12 * row.get("Adet", 0)

            yillik_opex = 0
            for _, row in edited_opex.iterrows():
                opex_inf = get_inflation_factor(y, row.get("Artış (%)", 0) / 100)
                birim_tutar = row.get("Tutar (TL)", 0) * opex_inf
                if "Değişken" in row.get("Tip", ""):
                    yillik_opex += birim_tutar * yillik_toplam_hasta
                else:
                    yillik_opex += birim_tutar * 12

            toplam_operasyonel_gider = yillik_personel + yillik_opex

            # --- FİNANSAL RASYO AŞAMALARI ---
            amortisman = yillik_amortisman_listesi[y_index]
            faiz_gideri = yillik_faiz_gideri[y_index]

            EBITDA = yillik_gelir - toplam_operasyonel_gider
            EBIT = EBITDA - amortisman
            EBT = EBIT - faiz_gideri

            vergi = EBT * kurumlar_vergisi if EBT > 0 else 0
            Net_Kar = EBT - vergi

            Net_Nakit_Akisi = Net_Kar + amortisman

            kumulatif += Net_Nakit_Akisi

            # NPV Hesabı
            npv_katki = Net_Nakit_Akisi / ((1 + iskonto_orani) ** y)
            npv_toplam += npv_katki

            nakit_akisi.append({
                "Yıl": y,
                "Gelir": yillik_gelir,
                "OPEX": toplam_operasyonel_gider,
                "EBITDA": EBITDA,
                "Amortisman": amortisman,
                "EBIT": EBIT,
                "Faiz Gideri": faiz_gideri,
                "EBT": EBT,
                "Vergi": vergi,
                "NET KÂR": Net_Kar,
                "Net Nakit Akışı": Net_Nakit_Akisi,
                "Kümülatif Nakit": kumulatif
            })

        df_sonuc = pd.DataFrame(nakit_akisi)

        # ----------------------------------------------------
        # 3. RAPORLAMA VE GÖRSELLEŞTİRME
        # ----------------------------------------------------

        # KPI Kartları
        col1, col2, col3, col4, col5 = st.columns(5)

        roi = (kumulatif / toplam_capex_tl) * 100 if toplam_capex_tl != 0 else 0
        sum_gelir = df_sonuc["Gelir"].sum()

        col1.metric("Toplam Yatırım", f"{toplam_capex_tl:,.0f} ₺")
        col2.metric("Net Bugünkü Değer (NPV)", f"{npv_toplam:,.0f} ₺", delta=f"Iskonto: %{iskonto_orani * 100}")
        col3.metric("ROI (Toplam)", f"%{roi:.1f}")
        col4.metric("Ort. EBITDA Marjı",
                    f"%{(df_sonuc['EBITDA'].sum() / sum_gelir * 100):.1f}" if sum_gelir != 0 else "N/A")
        col5.metric("Ort. Net Kâr Marjı",
                    f"%{(df_sonuc['NET KÂR'].sum() / sum_gelir * 100):.1f}" if sum_gelir != 0 else "N/A")

        st.divider()

        # Ortaklık Dağılımı
        st.markdown("#### 🤝 Ortaklık Yapısı ve Nakit Dağılımı")
        toplam_net_kar = df_sonuc["NET KÂR"].sum()

        col_o1, col_o2, col_o3 = st.columns(3)
        col_o1.metric("Toplam Net Kâr (10 Yıl)", f"{toplam_net_kar:,.0f} ₺")
        col_o2.metric(f"Ortak A (%{ortak1_oran:.0f} Payı)", f"{toplam_net_kar * (ortak1_oran / 100):,.0f} ₺")
        col_o3.metric(f"Ortak B (%{ortak2_oran:.0f} Payı)", f"{toplam_net_kar * (ortak2_oran / 100):,.0f} ₺")

        st.divider()

        # Grafik ve Tablo
        st.markdown("#### 📈 Yıllık Nakit Akışı ve Finansal Rapor")
        fig_cf = go.Figure()
        fig_cf.add_trace(
            go.Bar(x=df_sonuc["Yıl"], y=df_sonuc["Net Nakit Akışı"], name="Yıllık Nakit", marker_color='#2ecc71'))
        fig_cf.add_trace(
            go.Scatter(x=df_sonuc["Yıl"], y=df_sonuc["Kümülatif Nakit"], name="Kümülatif Nakit", mode='lines+markers',
                       line=dict(color='#e74c3c', width=3)))
        fig_cf.add_hline(y=0, line_dash="dash", annotation_text="Başabaş Noktası")
        st.plotly_chart(fig_cf, use_container_width=True)

        with st.expander("Detaylı Finansal Tabloyu Gör"):
            st.dataframe(
                df_sonuc.style.format("{:,.0f}"),
                use_container_width=True
            )