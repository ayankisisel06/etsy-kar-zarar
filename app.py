import streamlit as st
import requests
from supabase import create_client, Client

# Page configuration
st.set_page_config(page_title="Etsy Kar-Zarar Hesaplayıcı", page_icon="🛍️", layout="centered")

# --- CANLI KUR ÇEKME FONKSİYONU ---
def get_live_usd_rate():
    try:
        # TCMB verilerini de kullanan açık döviz servisi
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=5)
        data = response.json()
        return round(float(data["rates"]["TRY"]), 2)
    except Exception:
        # Alternatif servis (Yedek)
        try:
            url_alt = "https://open.er-api.com/v6/latest/USD"
            response_alt = requests.get(url_alt, timeout=5)
            data_alt = response_alt.json()
            return round(float(data_alt["rates"]["TRY"]), 2)
        except Exception:
            return 32.50 # Bağlantı koparsa varsayılan yedek kur

# Session state başlatma (Canlı kur için)
if "usd_rate" not in st.session_state:
    st.session_state["usd_rate"] = get_live_usd_rate()

# Supabase connection
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase bağlantı hatası: {e}")

st.title("🛍️ Etsy Kar-Zarar Hesaplayıcı")

# --- INPUT SECTION ---
st.subheader("1. Dolar Kuru")

# Kur ve Canlı Çek Butonu Yan Yana
col_kur1, col_kur2 = st.columns([3, 1])

with col_kur2:
    st.write("") # Hizalama boşluğu
    st.write("") 
    if st.button("🔄 Canlı Kur", use_container_width=True):
        st.session_state["usd_rate"] = get_live_usd_rate()
        st.toast(f"Güncel Kur: {st.session_state['usd_rate']} TL", icon="💱")

with col_kur1:
    kur = st.number_input("Güncel Dolar Kuru (TL)", min_value=0.0, value=st.session_state["usd_rate"], step=0.1, key="usd_input")

st.subheader("2. Ürün Maliyeti ($)")
cost_usd = st.number_input("Ürün Maliyeti (USD)", min_value=0.0, value=14.72, step=0.5)

gider_tl = cost_usd * kur

st.subheader("3. Satış Kazancı ( TL )")
kazanc_tl = st.number_input("Elinize Geçen Tutar (TL)", min_value=0.0, value=1000.0, step=10.0)

net_kar_tl = kazanc_tl - gider_tl

st.markdown("---")
st.subheader("📊 Sonuç Özeti")
st.caption(f"Maliyet: ${cost_usd:.2f} x {kur:.2f} TL = {gider_tl:.2f} TL")

if net_kar_tl >= 0:
    st.success(f"### NET KAR: +{net_kar_tl:.2f} TL")
else:
    st.error(f"### NET ZARAR: {net_kar_tl:.2f} TL")

# --- DATABASE INSERT ---
if st.button("💾 PostgreSQL Veritabanına Yaz", use_container_width=True):
    data = {
        "kur": float(kur),
        "gider_tl": float(gider_tl),
        "kazanc_tl": float(kazanc_tl),
        "net_kar_tl": float(net_kar_tl)
    }
    try:
        res = supabase.table("satislar").insert(data).execute()
        if res.data:
            st.toast("Satış başarıyla eklendi!", icon="✅")
            st.rerun()
    except Exception as e:
        st.error(f"Veritabanına kaydetme hatası: {e}")

st.markdown("---")

# --- DATABASE READ & DELETE SECTION ---
st.subheader("🔍 Veritabanı Kayıtları")

try:
    res = supabase.table("satislar").select("*").order("created_at", desc=True).execute()
    rows = res.data

    if rows:
        for row in rows:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    tarih = row.get("created_at", "")[:16].replace("T", " ")
                    kar = row.get("net_kar_tl", 0)
                    kar_metin = f":green[+{kar:.2f} TL]" if kar >= 0 else f":red[{kar:.2f} TL]"
                    
                    st.markdown(f"**Tarih:** {tarih} | **Net Kar:** {kar_metin}")
                    st.caption(f"Kazanç: {row.get('kazanc_tl', 0):.2f} TL | Gider: {row.get('gider_tl', 0):.2f} TL | Kur: {row.get('kur', 0):.2f} TL")
                
                with col2:
                    if st.button("🗑️ Sil", key=f"del_{row['id']}", type="secondary"):
                        supabase.table("satislar").delete().eq("id", row["id"]).execute()
                        st.toast("Kayıt silindi!", icon="🗑️")
                        st.rerun()
    else:
        st.info("Henüz veritabanında kayıtlı bir satış bulunmuyor.")

except Exception as e:
    st.error(f"Kayıtlar çekilirken hata oluştu: {e}")
