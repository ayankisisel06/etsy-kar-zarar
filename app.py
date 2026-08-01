import streamlit as st
import requests
from datetime import datetime
from supabase import create_client, Client

# Sayfa Yapılandırması
st.set_page_config(page_title="Etsy Kar-Zarar & Maliyet Yönetim Paneli", page_icon="🪶", layout="wide")

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
            return 47.54

# --- SESSION STATE (SAYFA HAFIZASI) ---
if "usd_rate" not in st.session_state:
    st.session_state["usd_rate"] = get_live_usd_rate()

if "cost_list" not in st.session_state:
    # Varsayılan kaydedilmiş fiyat seçenekleri
    st.session_state["cost_list"] = [9.72, 11.88, 14.72, 16.50]

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

st.title("🪶 Etsy Kar-Zarar & Maliyet Yönetim Paneli")

# --- İKİ AYRI SEKME ---
tab1, tab2 = st.tabs(["🧮 Kar-Zarar Hesapla", "📊 Veritabanı Kayıtları"])

# ==========================================
# SEKME 1: HESAPLAYICI (GÖRSEL BİREBİR)
# ==========================================
with tab1:
    # 1. Güncel Döviz Kuru
    st.markdown("##### 💱 1. Güncel Döviz Kuru")
    col_k1, col_k2 = st.columns([3, 1])
    with col_k1:
        kur = st.number_input("USD / TRY Kuru:", min_value=0.0, value=st.session_state["usd_rate"], step=0.1, key="usd_input")
    with col_k2:
        st.write("")
        st.write("")
        if st.button("🔄 Canlı Çek", use_container_width=True):
            st.session_state["usd_rate"] = get_live_usd_rate()
            st.toast(f"Güncel Kur: {st.session_state['usd_rate']} TL", icon="💱")
            st.rerun()

    st.markdown("---")

    # 2. Ürün Maliyeti (USD)
    st.markdown("##### 🏷️ 2. Ürün Maliyeti (USD)")
    col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
    
    with col_m1:
        selected_cost = st.selectbox("Fiyat Seçin ($):", options=st.session_state["cost_list"], index=0)
    
    with col_m2:
        st.write("")
        st.write("")
        new_cost_val = st.number_input("Yeni Fiyat Ekle ($)", min_value=0.0, value=10.0, step=0.5, label_visibility="collapsed")
        if st.button("+ Fiyat Ekle", use_container_width=True):
            if new_cost_val not in st.session_state["cost_list"]:
                st.session_state["cost_list"].append(round(new_cost_val, 2))
                st.session_state["cost_list"].sort()
                st.toast("Yeni fiyat listeye eklendi!", icon="✅")
                st.rerun()

    with col_m3:
        st.write("")
        st.write("")
        if st.button("- Sil", type="secondary", use_container_width=True):
            if len(st.session_state["cost_list"]) > 1:
                st.session_state["cost_list"].remove(selected_cost)
                st.toast("Seçili fiyat silindi!", icon="🗑️")
                st.rerun()
            else:
                st.warning("Listede en az bir fiyat kalmalıdır!")

    st.markdown("---")

    # 3. Kargo Maliyeti (USD)
    st.markdown("##### 📦 3. Kargo Maliyeti (USD)")
    kargo_usd = st.number_input("Kargo Ücreti ($):", min_value=0.0, value=5.00, step=0.5)

    st.markdown("---")

    # 4. Satış Kazancı (TL)
    st.markdown("##### 💰 4. Satış Kazancı (TL)")
    kazanc_tl = st.number_input("Elinize Geçen (TL):", min_value=0.0, value=1000.00, step=10.0)

    st.markdown("---")

    # 5. Baskı Seçenekleri
    st.markdown("##### 🌐 5. Baskı Seçenekleri")
    arka_baski = st.checkbox("Arka kısımda baskı var (+$2.00)")
    arka_baski_usd = 2.00 if arka_baski else 0.00

    st.markdown("---")

    # HESAPLAMALAR
    urun_gider_tl = selected_cost * kur
    kargo_gider_tl = kargo_usd * kur
    baski_gider_tl = arka_baski_usd * kur
    toplam_gider_tl = urun_gider_tl + kargo_gider_tl + baski_gider_tl
    net_kar_tl = kazanc_tl - toplam_gider_tl

    # HESAPLAMA ÖZETİ (GÖRSEL BİREBİR)
    st.markdown("##### 📥 Hesaplama Özeti")
    
    with st.container(border=True):
        st.write(f"**Ürün Maliyeti:** ${selected_cost:.2f} x {kur:.2f} = {urun_gider_tl:.2f} TL")
        st.write(f"**Kargo Maliyeti:** ${kargo_usd:.2f} x {kur:.2f} = {kargo_gider_tl:.2f} TL")
        st.write(f"**Arka Baskı:** ${arka_baski_usd:.2f} x {kur:.2f} = {baski_gider_tl:.2f} TL")
        st.markdown("---")
        st.markdown(f"### **Toplam Gider:** {toplam_gider_tl:.2f} TL")
        
        if net_kar_tl >= 0:
            st.markdown(f"### <span style='color:#10B981;'>NET KAR: +{net_kar_tl:.2f} TL</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"### <span style='color:#EF4444;'>NET ZARAR: {net_kar_tl:.2f} TL</span>", unsafe_allow_html=True)

    st.write("")
    if st.button("📥 Kayıtlara Ekle", type="primary", use_container_width=True):
        data = {
            "kur": float(kur),
            "gider_tl": float(toplam_gider_tl),
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

# ==========================================
# SEKME 2: VERİTABANI KAYITLARI & FİLTRELEME
# ==========================================
with tab2:
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        selected_date = st.date_input("📅 İncelemek İstediğiniz Tarihi Seçin:", datetime.now())
    
    formatted_date_str = selected_date.strftime("%d/%m/%Y")
    
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
                gunluk_toplam_kar = sum(item["net_kar_tl"] for item in filtered_rows)
                gunluk_toplam_ciro = sum(item["kazanc_tl"] for item in filtered_rows)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Günün Satış Adedi", f"{len(filtered_rows)} Adet")
                m2.metric("Günün Cirosu", f"{gunluk_toplam_ciro:.2f} TL")
                m3.metric("Günün Net Kârı", f"{gunluk_toplam_kar:.2f} TL", delta=f"{gunluk_toplam_kar:.2f} TL")
                
                st.markdown("---")

                t_head1, t_head2, t_head3, t_head4, t_head5, t_head6 = st.columns([2.5, 1.5, 1.5, 1.5, 1.5, 1])
                t_head1.markdown("**Tarih / Saat**")
                t_head2.markdown("**Dolar Kuru**")
                t_head3.markdown("**Gider (TL)**")
                t_head4.markdown("**Kazanç (TL)**")
                t_head5.markdown("**Net Kar (TL)**")
                t_head6.markdown("**İşlem**")
                
                st.divider()

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
                    
                    if c6.button("🗑️ Sil", key=f"del_{r['id']}", type="secondary"):
                        supabase.table("satislar").delete().eq("id", r["id"]).execute()
                        st.toast("Kayıt silindi!", icon="🗑️")
                        st.rerun()

            else:
                st.info(f"💡 {formatted_date_str} tarihinde henüz kaydınız bulunmuyor.")

        else:
            st.info("Veritabanında henüz kayıtlı bir satış bulunmuyor.")

    except Exception as e:
        st.error(f"Kayıtlar çekilirken hata oluştu: {e}")
