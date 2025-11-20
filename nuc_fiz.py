import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- SAYFA AYARLARI (Geniş Ekran) ---
st.set_page_config(page_title="MNT - Nükleer Tıp Yönetim Paneli", layout="wide", page_icon="☢️")

# --- STİL ---
st.markdown("""
<style>
    .main { background-color: #f5f5f5; }
    div.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title("☢️ MNT | Nükleer Tıp Yatırım & Fizibilite Sistemi")
st.markdown("Bu sistem; cihaz yatırımı, operasyonel verimlilik ve finansal senaryoları analiz eder.")

# ==========================================
# YAN MENÜ: PARAMETRELER
# ==========================================
with st.sidebar:
    st.header("⚙️ Operasyonel Ayarlar")

    st.subheader("1. Zaman Planı")
    sure_yil = st.slider("Projeksiyon Süresi (Yıl)", 5, 15, 10)
    calisma_gunu = st.number_input("Aylık Çalışma Günü", value=24, min_value=1, max_value=30,
                                   help="Pazar hariç genelde 24-26 gün")
    verimlilik = st.slider("Cihaz Aktiflik Oranı (%)", 80, 100, 95,
                           help="Bakım, arıza ve hasta iptalleri düşüldükten sonraki oran.")

    st.subheader("2. Finansal Varsayımlar")
    iskonto_orani = st.number_input("İskonto Oranı (NPV için %)", value=25.0) / 100
    kurumlar_vergisi = st.number_input("Kurumlar Vergisi (%)", value=25.0) / 100

    st.subheader("3. Kur & Enflasyon")
    usd_kur = st.number_input("USD Kuru", value=34.5)
    eur_kur = st.number_input("EUR Kuru", value=36.2)
    enflasyon = st.number_input("Yıllık Enflasyon Beklentisi (%)", value=45.0) / 100

    st.divider()
    secilen_senaryo = st.radio("📌 Analiz Senaryosu:", ["Kötümser", "Beklenen", "İyimser"], index=1)


# --- YARDIMCI FONKSİYON ---
def get_inflation_factor(year, rate):
    return (1 + rate) ** (year - 1)


# ==========================================
# ANA EKRAN - SEKME YAPISI
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["💰 Yatırım (CAPEX)", "⚙️ İşletme (OPEX)", "📈 Gelirler", "📊 ANALİZ & RAPOR"])

# --- TAB 1: CAPEX ---
with tab1:
    st.subheader("Yatırım Bütçesi")
    col1, col2 = st.columns([2, 1])
    with col1:
        capex_df = pd.DataFrame([
            {"Kalem": "PET/CT Cihazı", "Tutar": 1150000, "Döviz": "EUR"},
            {"Kalem": "Sıcak Oda (Hot Lab)", "Tutar": 120000, "Döviz": "EUR"},
            {"Kalem": "İnşaat & Kurşunlama", "Tutar": 4500000, "Döviz": "TL"},
            {"Kalem": "Ruhsat & Proje", "Tutar": 250000, "Döviz": "TL"},
        ])
        edited_capex = st.data_editor(capex_df, num_rows="dynamic", use_container_width=True)

    with col2:
        st.info("💡 **İpucu:** Yatırım kalemlerini sağdaki tabloya ekleyebilirsiniz. Döviz kurları yan menüden çekilir.")
        # Anlık Hesaplama
        toplam_capex_tl = 0
        for _, row in edited_capex.iterrows():
            kur = eur_kur if row["Döviz"] == "EUR" else (usd_kur if row["Döviz"] == "USD" else 1.0)
            toplam_capex_tl += row["Tutar"] * kur
        st.metric("Toplam Yatırım İhtiyacı (TL)", f"{toplam_capex_tl:,.0f} ₺")

# --- TAB 2: OPEX ---
with tab2:
    col_p, col_g = st.columns(2)

    with col_p:
        st.subheader("👥 Personel Giderleri")
        personel_df = pd.DataFrame([
            {"Pozisyon": "Nükleer Tıp Uzmanı", "Adet": 1, "Brüt Maaş (TL)": 140000, "Yıllık Artış (%)": 45},
            {"Pozisyon": "Medikal Fizikçi", "Adet": 1, "Brüt Maaş (TL)": 75000, "Yıllık Artış (%)": 45},
            {"Pozisyon": "Tekniker", "Adet": 3, "Brüt Maaş (TL)": 35000, "Yıllık Artış (%)": 45},
            {"Pozisyon": "Hemşire/Sekreter", "Adet": 2, "Brüt Maaş (TL)": 30000, "Yıllık Artış (%)": 45},
        ])
        edited_personel = st.data_editor(personel_df, num_rows="dynamic", use_container_width=True)

    with col_g:
        st.subheader("🏢 İşletme Giderleri")
        opex_df = pd.DataFrame([
            {"Gider": "Radyofarmasötik (FDG)", "Tip": "Değişken (Hasta Başı)", "Tutar (TL)": 2200, "Artış (%)": 40},
            {"Gider": "Sarf Malzeme", "Tip": "Değişken (Hasta Başı)", "Tutar (TL)": 300, "Artış (%)": 40},
            {"Gider": "Bakım Anlaşması", "Tip": "Sabit (Aylık)", "Tutar (TL)": 120000, "Artış (%)": 50},
            {"Gider": "Kira & Aidat", "Tip": "Sabit (Aylık)", "Tutar (TL)": 60000, "Artış (%)": 55},
            {"Gider": "Elektrik/Su/Data", "Tip": "Sabit (Aylık)", "Tutar (TL)": 35000, "Artış (%)": 60},
        ])
        edited_opex = st.data_editor(opex_df, num_rows="dynamic", use_container_width=True)

# --- TAB 3: GELİRLER ---
with tab3:
    st.subheader("📈 Gelir Projeksiyonu")
    st.markdown(
        f"**Seçilen Senaryo:** `{secilen_senaryo}` | **Aylık İş Günü:** `{calisma_gunu}` | **Verimlilik:** `%{verimlilik}`")

    gelir_df = pd.DataFrame([
        {"Hizmet": "PET/CT (Onkoloji)", "Fiyat (TL)": 5500, "Kötümser (Günlük)": 8, "Beklenen (Günlük)": 15,
         "İyimser (Günlük)": 25},
        {"Hizmet": "PET/CT (Kardiyoloji)", "Fiyat (TL)": 5500, "Kötümser (Günlük)": 1, "Beklenen (Günlük)": 2,
         "İyimser (Günlük)": 4},
        {"Hizmet": "Sintigrafi Grubu", "Fiyat (TL)": 1200, "Kötümser (Günlük)": 4, "Beklenen (Günlük)": 8,
         "İyimser (Günlük)": 12},
    ])
    edited_gelir = st.data_editor(gelir_df, num_rows="dynamic", use_container_width=True)

# ==========================================
# HESAPLAMA MOTORU (ARKA PLAN)
# ==========================================
years = list(range(1, sure_yil + 1))
nakit_akisi = []
kumulatif = -toplam_capex_tl
npv_toplam = -toplam_capex_tl

# Grafik İçin Veri Toplayıcılar
waterfall_data = {"Gelir": 0, "Personel": 0, "Değişken": 0, "Sabit": 0, "Vergi": 0}  # Sadece 1. yıl için örnek

for y in years:
    # Enflasyon Çarpanı
    inf_factor = get_inflation_factor(y, enflasyon)

    # --- 1. GELİR HESABI ---
    yillik_gelir = 0
    yillik_toplam_hasta = 0

    # Efektif Çalışma Günü: Çalışma Günü * Verimlilik Çarpanı
    efektif_gun = calisma_gunu * (verimlilik / 100)

    for _, row in edited_gelir.iterrows():
        gunluk_hasta = row[f"{secilen_senaryo} (Günlük)"]
        # Formül: Günlük Hasta * Efektif Gün * 12 Ay * Fiyat * Enflasyon
        yillik_hizmet_geliri = (gunluk_hasta * efektif_gun * 12) * (row["Fiyat (TL)"] * inf_factor)
        yillik_gelir += yillik_hizmet_geliri
        yillik_toplam_hasta += (gunluk_hasta * efektif_gun * 12)

    # --- 2. GİDER HESABI ---
    # Personel
    yillik_personel = 0
    for _, row in edited_personel.iterrows():
        pers_inf = get_inflation_factor(y, row["Yıllık Artış (%)"] / 100)
        yillik_personel += (row["Brüt Maaş (TL)"] * pers_inf) * 12 * row["Adet"]

    # OPEX (Sabit ve Değişken)
    yillik_degisken = 0
    yillik_sabit = 0

    for _, row in edited_opex.iterrows():
        opex_inf = get_inflation_factor(y, row["Artış (%)"] / 100)
        birim_tutar = row["Tutar (TL)"] * opex_inf

        if "Değişken" in row["Tip"]:
            # Değişken Gider = Birim Tutar * Toplam Yıllık Hasta
            yillik_degisken += birim_tutar * yillik_toplam_hasta
        else:
            # Sabit Gider = Aylık Tutar * 12
            yillik_sabit += birim_tutar * 12

    # --- 3. SONUÇLAR ---
    toplam_gider = yillik_personel + yillik_degisken + yillik_sabit
    ebitda = yillik_gelir - toplam_gider
    vergi = ebitda * kurumlar_vergisi if ebitda > 0 else 0
    net_kar = ebitda - vergi

    kumulatif += net_kar

    # NPV Hesabı (Net Bugünkü Değer)
    npv_katki = net_kar / ((1 + iskonto_orani) ** y)
    npv_toplam += npv_katki

    # İlk yılın waterfall verisini sakla
    if y == 1:
        waterfall_data["Gelir"] = yillik_gelir
        waterfall_data["Personel"] = -yillik_personel
        waterfall_data["Değişken"] = -yillik_degisken
        waterfall_data["Sabit"] = -yillik_sabit
        waterfall_data["Vergi"] = -vergi

    nakit_akisi.append({
        "Yıl": y,
        "Gelir": yillik_gelir,
        "Gider": toplam_gider,
        "Net Kâr": net_kar,
        "Kümülatif": kumulatif,
        "Yatırım": -toplam_capex_tl if y == 1 else 0
    })

df_sonuc = pd.DataFrame(nakit_akisi)

# ==========================================
# TAB 4: GÖRSEL ANALİZ RAPORU
# ==========================================
with tab4:
    # --- KPI METRİKLERİ ---
    st.markdown("### 📊 Yönetici Özeti")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    roi = (kumulatif / toplam_capex_tl) * 100
    payback_text = "10+ Yıl"
    for i, row in df_sonuc.iterrows():
        if row["Kümülatif"] > 0:
            payback_text = f"{row['Yıl']}. Yıl"
            break

    kpi1.metric("Yatırım Tutarı (CAPEX)", f"{toplam_capex_tl:,.0f} ₺", delta_color="inverse")
    kpi2.metric("Net Bugünkü Değer (NPV)", f"{npv_toplam:,.0f} ₺", delta=f"İskonto: %{iskonto_orani * 100}",
                help="Paranın zaman maliyeti düşüldükten sonraki gerçek değer.")
    kpi3.metric("Geri Dönüş (Payback)", payback_text, delta="ROI Hedefi")
    kpi4.metric("10 Yıllık Toplam Kâr", f"{kumulatif:,.0f} ₺", delta=f"%{roi:.1f} ROI")

    st.divider()

    # --- GRAFİK BÖLÜMÜ ---
    col_graf1, col_graf2 = st.columns([2, 1])

    with col_graf1:
        st.markdown("#### 🟢 Nakit Akışı ve Başabaş Noktası")
        fig_cf = go.Figure()
        fig_cf.add_trace(
            go.Bar(x=df_sonuc["Yıl"], y=df_sonuc["Net Kâr"], name="Yıllık Net Kâr", marker_color='#2ecc71'))
        fig_cf.add_trace(
            go.Scatter(x=df_sonuc["Yıl"], y=df_sonuc["Kümülatif"], name="Kümülatif Nakit Durumu", mode='lines+markers',
                       line=dict(color='#e74c3c', width=3)))
        fig_cf.add_hline(y=0, line_dash="dash", annotation_text="Başabaş Noktası")
        st.plotly_chart(fig_cf, use_container_width=True)

    with col_graf2:
        st.markdown("#### 🍰 1. Yıl Gider Dağılımı")
        # Gider Pastası
        labels = ['Personel', 'Değişken (İlaç/Sarf)', 'Sabit (Kira/Bakım)']
        values = [abs(waterfall_data["Personel"]), abs(waterfall_data["Değişken"]), abs(waterfall_data["Sabit"])]
        fig_pie = px.pie(names=labels, values=values, hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- WATERFALL VE TABLO ---
    col_w, col_t = st.columns([1, 2])

    with col_w:
        st.markdown("#### 💧 Kârlılık Şelalesi (1. Yıl)")
        fig_water = go.Figure(go.Waterfall(
            name="20", orientation="v",
            measure=["relative", "relative", "relative", "relative", "relative", "total"],
            x=["Gelir", "Personel", "Değişken", "Sabit", "Vergi", "Net Kâr"],
            textposition="outside",
            y=[waterfall_data["Gelir"], waterfall_data["Personel"], waterfall_data["Değişken"],
               waterfall_data["Sabit"], waterfall_data["Vergi"], df_sonuc.iloc[0]["Net Kâr"]],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        fig_water.update_layout(showlegend=False)
        st.plotly_chart(fig_water, use_container_width=True)

    with col_t:
        st.markdown("#### 📋 Detaylı Finansal Tablo")
        st.dataframe(
            df_sonuc.style.format("{:,.0f}"),
            use_container_width=True,
            height=300
        )