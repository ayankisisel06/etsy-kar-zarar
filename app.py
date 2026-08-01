import datetime
import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

# Sayfa Yapılandırması (Mobil Odaklı)
st.set_page_config(
    page_title="Etsy Kar-Zarar (PostgreSQL)",
    page_icon="🛍️",
    layout="centered"
)

# ---------------------------------------------------------
# VERİTABANI BAĞLANTISI (Supabase)
# ---------------------------------------------------------
# Gizli API Anahtarlarını Streamlit Secrets üzerinden veya doğrudan okur
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "BURAYA_SUPABASE_URL_GELECEK")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "BURAYA_SUPABASE_ANON_KEY_GELECEK")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Canlı Kur Çekme Fonksiyonu
def canli_kur_cek():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        res = requests.get(url, timeout=3).json()
        return round(res["rates"]["TRY"], 2)
    except Exception:
        return 35.00

# ---------------------------------------------------------
# ARAYÜZ
# ---------------------------------------------------------
st.title("🛍️ Etsy Kar - Zarar Paneli")

tab1, tab2 = st.tabs(["🧮 Hesapla & Ekle", "📜 Veritabanı Kayıtları"])

# ==================== 1. SEKME: HESAPLAMA ====================
with tab1:
    st.subheader("1. Döviz Kuru")
    col_kur1, col_kur2 = st.columns([2, 1])
    
    with col_kur2:
        if st.button("🔄 Canlı Çek", use_container_width=True):
            st.session_state.kur = canli_kur_cek()
            
    if "kur" not in st.session_state:
        st.session_state.kur = canli_kur_cek()
        
    with col_kur1:
        kur = st.number_input("USD / TRY Kuru", value=float(st.session_state.kur), step=0.1, format="%.2f")

    st.divider()

    st.subheader("2. Ürün & Kargo Maliyeti")
    
    if "fiyatlar" not in st.session_state:
        st.session_state.fiyatlar = [9.72, 11.88, 14.50, 19.99]
        
    fiyat_secim = st.selectbox("Ürün Fiyatı ($)", options=st.session_state.fiyatlar)
    
    with st.expander("➕ / ➖ Fiyat Seçeneklerini Düzenle"):
        yeni_fiyat = st.number_input("Yeni Fiyat ($)", value=0.0, step=0.5)
        if st.button("Listeye Ekle"):
            if yeni_fiyat > 0 and yeni_fiyat not in st.session_state.fiyatlar:
                st.session_state.fiyatlar.append(yeni_fiyat)
                st.session_state.fiyatlar.sort()
                st.rerun()

    kargo_usd = st.number_input("Kargo Ücreti ($)", value=5.0, step=0.5)
    arka_baski = st.checkbox("Arka kısımda baskı var (+$2.00)")

    st.divider()

    st.subheader("3. Satış Kazancı (TL)")
    kazanc_tl = st.number_input("Elinize Geçen Tutar (TL)", value=1000.0, step=50.0)

    # Hesaplama Mantığı
    baski_usd = 2.0 if arka_baski else 0.0
    toplam_gider_usd = fiyat_secim + kargo_usd + baski_usd
    toplam_gider_tl = toplam_gider_usd * kur
    net_kar_tl = kazanc_tl - toplam_gider_tl

    st.divider()
    st.markdown("### 📊 Sonuç Özeti")
    st.caption(f"Maliyet: ${toplam_gider_usd:.2f} x {kur:.2f} TL = {toplam_gider_tl:.2f} TL")
    
    if net_kar_tl >= 0:
        st.success(f"### NET KAR: +{net_kar_tl:.2f} TL")
    else:
        st.error(f"### NET ZARAR: {net_kar_tl:.2f} TL")

    # Supabase PostgreSQL INSERT İşlemi
    if st.button("📥 PostgreSQL Veritabanına Yaz", type="primary", use_container_width=True):
        data = {
            "kur": float(kur),
            "gider_tl": float(toplam_gider_tl),
            "kazanc_tl": float(kazanc_tl),
            "net_kar_tl": float(net_kar_tl)
        }
        res = supabase.table("satislar").insert(data).execute()
        if res.data:
            st.toast("Satış PostgreSQL veritabanına başarıyla eklendi!", icon="✅")

# ==================== 2. SEKME: DB OKUMA & SİLME ====================
with tab2:
    st.subheader("🔍 Veritabanı Kayıtları")
    
    # Supabase SELECT Sorgusu
    res = supabase.table("satislar").select("*").order("created_at", desc=True).execute()
    rows = res.data

    if rows:
        df = pd.DataFrame(rows)
        # Tarih Formatlama
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime('%Y-%m-%d %H:%M')
        
        # Tablo Sütun İsimleri
        df = df[["id", "created_at", "kur", "gider_tl", "kazanc_tl", "net_kar_tl"]]
        df.rename(columns={
            "id": "ID",
            "created_at": "Tarih/Saat",
            "kur": "Kur",
            "gider_tl": "Gider (TL)",
            "kazanc_tl": "Kazanç (TL)",
            "net_kar_tl": "Net Kar (TL)"
        }, inplace=True)

        st.dataframe(df, use_container_width=True)

        st.divider()
        st.caption("🗑️ Veritabanından Satır Sil (ID ile)")
        col_sil1, col_sil2 = st.columns([2, 1])
        with col_sil1:
            silinecek_id = st.number_input("Silinecek Kayıt ID'si", min_value=1, step=1)
        with col_sil2:
            st.write("") # Boşluk hizalama
            if st.button("Kaydı Sil", use_container_width=True):
                supabase.table("satislar").delete().eq("id", silinecek_id).execute()
                st.toast(f"ID #{silinecek_id} veritabanından silindi.", icon="🗑️")
                st.rerun()
    else:
        st.info("Veritabanında henüz satış kaydı bulunmuyor.")