import streamlit as st
import requests
from datetime import datetime
from supabase import create_client, Client

# Sayfa Genişlik ve Başlık Ayarı
st.set_page_config(page_title="Etsy Kar-Zarar Paneli", page_icon="🛍️", layout="wide")

# --- CANLI KUR ÇEKME FONKSİYONU ---
def get_live_usd_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=5)
        data = response.json()
        return round(float(data["rates"]["TRY"]), 2)
    except Exception:
        try:
            url_alt = "https://open.er-api.com/v6/latest/USD"
            response_alt = requests.get(url_alt, timeout=5)
            data_alt = response_alt.json()
            return round(float(data_alt["rates"]["TRY"]), 2)
        except Exception:
            return 32.50

# Session State Başlatma (Canlı Kur İçin)
if "usd_rate" not in st.session_state:
    st.session_state["usd_rate"] = get_live_usd_rate()

# Supabase Bağlantısı
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase bağlantı hatası: {e}")

st.title("🛍️ Etsy Finansal Yönetim Paneli")

# ==========================================
# İKİ AYRI SEKME OLUŞTURULUYOR
# ==========================================
tab1, tab2 = st.tabs(["🧮 Kar-Zarar Hesapla", "📊 Veritabanı Kayıtları"])

# ------------------------------------------
# SEKME 1: HESAPLAYICI VE KAYIT
# ------------------------------------------
with tab1:
    st.markdown("### 1. Dolar Kuru")
    col_kur1, col_kur2 = st.columns([3, 1])
    
    with col_kur2:
        st.write("")
        st.write("")
        if st.button("🔄 Canlı Kur Çek", use_container_width=True):
            st.session_state["usd_rate"] = get_live_usd_rate()
            st.toast(f"Güncel Kur: {st.session_state['usd_rate']} TL", icon="💱")

    with col_kur1:
        kur = st.number_input("Güncel Dolar Kuru (TL)", min_value=0.0, value=st.session_state["usd_rate"], step=0.1, key="usd_input")

    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        st.markdown("### 2. Ürün Maliyeti ($)")
        cost_usd = st.number_input("Ürün Maliyeti (USD)", min_value=0.0, value=14.72, step=0.5)
        gider_tl = cost_usd * kur

    with col_inp2:
        st.markdown("### 3. Satış Kazancı (TL)")
        kazanc_tl = st.number_input("Elinize Geçen Tutar (TL)", min_value=0.0, value=1000.0, step=10.0)

    net_kar_tl = kazanc_tl - gider_tl

    st.markdown("---")
    
    # Sonuç Metrik Kartları
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Toplam Maliyet (TL)", f"{gider_tl:.2f} TL", delta=f"${cost_usd:.2f}", delta_color="inverse")
    res_col2.metric("Elinize Geçen Net (TL)", f"{kazanc_tl:.2f} TL")
    res_col3.metric("HESAPLANAN NET KAR", f"{net_kar_tl:.2f} TL", delta=f"{net_kar_tl:.2f} TL")

    st.write("")
    if st.button("💾 Kaydı Veritabanına Yaz", type="primary", use_container_width=True):
        data = {
            "kur": float(kur),
            "gider_tl": float(gider_tl),
            "kazanc_tl": float(kazanc_tl),
            "net_kar_tl": float(net_kar_tl)
        }
        try:
            res = supabase.table("satislar").insert(data).execute()
            if res.data:
                st.toast("Satış başarıyla veritabanına eklendi!", icon="✅")
                st.rerun()
        except Exception as e:
            st.error(f"Veritabanına kaydetme hatası: {e}")

# ------------------------------------------
# SEKME 2: VERİTABANI KAYITLARI & FİLTRELEME
# ------------------------------------------
with tab2:
    col_filter1, col_filter2 = st.columns([2, 2])
    
    with col_filter1:
        selected_date = st.date_input("📅 İncelemek İstediğiniz Tarihi Seçin:", datetime.now())
    
    formatted_date_str = selected_date.strftime("%d/%m/%Y")
    
    # Renkli Belirgin Tarih Kutusu (HTML Banner)
    st.markdown(
        f"""
        <div style="background-color: #0F172A; border-left: 6px solid #3B82F6; padding: 14px 20px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px;">
            <h3 style="color: #F8FAFC; margin: 0; font-size: 1.25rem;">
                📌 <span style="color: #60A5FA; font-weight: bold;">{formatted_date_str}</span> Tarihine Ait Satış Kayıtları
            </h3>
        </div>
        """, 
        unsafe_allow_html=True
    )

    try:
        res = supabase.table("satislar").select("*").order("created_at", desc=True).execute()
        rows = res.data

        if rows:
            # Seçilen güne göre filtreleme
            filtered_rows = []
            for r in rows:
                raw_dt = r.get("created_at", "")
                if raw_dt:
                    try:
                        dt_obj = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                        if dt_obj.date() == selected_date:
                            r["formatted_time"] = dt_obj.strftime("%d/%m/%Y - %H:%M")
                            filtered_rows.append(r)
                    except Exception:
                        pass

            if filtered_rows:
                # O Güne Ait İstatistikler
                gunluk_toplam_kar = sum(item["net_kar_tl"] for item in filtered_rows)
                gunluk_toplam_ciro = sum(item["kazanc_tl"] for item in filtered_rows)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Günün Satış Adedi", f"{len(filtered_rows)} Adet")
                m2.metric("Günün Cirosu", f"{gunluk_toplam_ciro:.2f} TL")
                m3.metric("Günün Net Kârı", f"{gunluk_toplam_kar:.2f} TL", delta=f"{gunluk_toplam_kar:.2f} TL")
                
                st.markdown("---")

                # Tablo Başlık Alanı
                t_head1, t_head2, t_head3, t_head4, t_head5, t_head6 = st.columns([2.5, 1.5, 1.5, 1.5, 1.5, 1])
                t_head1.markdown("**Tarih / Saat**")
                t_head2.markdown("**Dolar Kuru**")
                t_head3.markdown("**Gider (TL)**")
                t_head4.markdown("**Kazanç (TL)**")
                t_head5.markdown("**Net Kar (TL)**")
                t_head6.markdown("**İşlem**")
                
                st.divider()

                # Tablo Satırları
                for r in filtered_rows:
                    c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1.5, 1.5, 1.5, 1.5, 1])
                    c1.write(r["formatted_time"])
                    c2.write(f"{r['kur']:.2f} TL")
                    c3.write(f"{r['gider_tl']:.2f} TL")
                    c4.write(f"{r['kazanc_tl']:.2f} TL")
                    
                    kar_val = r['net_kar_tl']
                    if kar_val >= 0:
                        c5.markdown(f"<span style='color:#22C55E; font-weight:bold;'>+{kar_val:.2f} TL</span>", unsafe_allow_html=True)
                    else:
                        c5.markdown(f"<span style='color:#EF4444; font-weight:bold;'>{kar_val:.2f} TL</span>", unsafe_allow_html=True)
                    
                    # Tek Tıkla Sil Butonu
                    if c6.button("🗑️ Sil", key=f"del_{r['id']}", type="secondary"):
                        supabase.table("satislar").delete().eq("id", r["id"]).execute()
                        st.toast("Kayıt veritabanından silindi!", icon="🗑️")
                        st.rerun()

            else:
                st.info(f"💡 {formatted_date_str} tarihinde henüz kaydınız bulunmuyor.")

        else:
            st.info("Veritabanında henüz kayıtlı bir satış bulunmuyor.")

    except Exception as e:
        st.error(f"Kayıtlar çekilirken hata oluştu: {e}")
