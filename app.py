import streamlit as st
import requests
from datetime import datetime
from supabase import create_client, Client

# Sayfa Yapılandırması
st.set_page_config(page_title="Etsy Kar-Zarar Paneli", page_icon="🪶", layout="wide")

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

# --- SESSION STATE ---
if "usd_rate" not in st.session_state:
    st.session_state["usd_rate"] = get_live_usd_rate()

if "cost_list" not in st.session_state:
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

st.title("🪶 Etsy Kar-Zarar Paneli")

# --- İKİ AYRI SEKME ---
tab1, tab2 = st.tabs(["🧮 Kar-Zarar Hesapla", "📊 Veritabanı Kayıtları"])

# ==========================================
# SEKME 1: HESAPLAYICI (MOBİL UYUMLU / KOMPAKT)
# ==========================================
with tab1:
    # SATIR 1: Kur ve Canlı Çek
    c_kur1, c_kur2 = st.columns([2, 1])
    with c_kur1:
        kur = st.number_input("1. Döviz Kuru (TL)", min_value=0.0, value=st.session_state["usd_rate"], step=0.1, key="usd_input")
    with c_kur2:
        st.write("")
        st.write("")
        if st.button("🔄 Canlı", use_container_width=True):
            st.session_state["usd_rate"] = get_live_usd_rate()
            st.toast(f"Güncel Kur: {st.session_state['usd_rate']} TL", icon="💱")
            st.rerun()

    # SATIR 2: Ürün Maliyeti & Kargo Maliyeti (Yan Yana)
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        selected_cost = st.selectbox("2. Ürün Maliyeti ($)", options=st.session_state["cost_list"], index=0)
    with c_m2:
        kargo_usd = st.number_input("3. Kargo Maliyeti ($)", min_value=0.0, value=5.00, step=0.5)

    # İSTEĞE BAĞLI: Fiyat Ekleme / Silme (Açılır Gizli Menü)
    with st.expander("⚙️ Fiyat Seçeneklerini Yönet (+ / -)"):
        col_add, col_del = st.columns(2)
        with col_add:
            new_cost_val = st.number_input("Yeni Fiyat ($)", min_value=0.0, value=10.0, step=0.5)
            if st.button("+ Listeye Ekle", use_container_width=True):
                if new_cost_val not in st.session_state["cost_list"]:
                    st.session_state["cost_list"].append(round(new_cost_val, 2))
                    st.session_state["cost_list"].sort()
                    st.toast("Fiyat eklendi!", icon="✅")
                    st.rerun()
        with col_del:
            st.write("")
            st.write("")
            if st.button("- Seçili Fiyatı Sil", type="secondary", use_container_width=True):
                if len(st.session_state["cost_list"]) > 1:
                    st.session_state["cost_list"].remove(selected_cost)
                    st.toast("Fiyat silindi!", icon="🗑️")
                    st.rerun()

    # SATIR 3: Satış Kazancı & Arka Baskı (Yan Yana)
    c_k1, c_k2 = st.columns([2, 1])
    with c_k1:
        kazanc_tl = st.number_input("4. Satış Kazancı (TL)", min_value=0.0, value=1000.00, step=10.0)
    with c_k2:
        st.write("")
        st.write("")
        arka_baski = st.checkbox("Arka Baskı (+$2)")

    arka_baski_usd = 2.00 if arka_baski else 0.00

    # HESAPLAMALAR
    urun_gider_tl = selected_cost * kur
    kargo_gider_tl = kargo_usd * kur
    baski_gider_tl = arka_baski_usd * kur
    toplam_gider_tl = urun_gider_tl + kargo_gider_tl + baski_gider_tl
    net_kar_tl = kazanc_tl - toplam_gider_tl

    st.markdown("---")

    # KOMPAKT HESAPLAMA ÖZETİ
    with st.container(border=True):
        st.caption(f"Ürün: ${selected_cost:.2f} | Kargo: ${kargo_usd:.2f} | Arka Baskı: ${arka_baski_usd:.2f} (Kur: {kur:.2f})")
        
        res_c1, res_c2 = st.columns(2)
        res_c1.markdown(f"**Toplam Gider:**  \n**{toplam_gider_tl:.2f} TL**")
        
        if net_kar_tl >= 0:
            res_c2.markdown(f"**NET KAR:**  \n<span style='color:#10B981; font-size:1.2rem; font-weight:bold;'>+{net_kar_tl:.2f} TL</span>", unsafe_allow_html=True)
        else:
            res_c2.markdown(f"**NET ZARAR:**  \n<span style='color:#EF4444; font-size:1.2rem; font-weight:bold;'>{net_kar_tl:.2f} TL</span>", unsafe_allow_html=True)

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
                st.toast("Satış başarıyla eklendi!", icon="✅")
                st.rerun()
        except Exception as e:
            st.error(f"Veritabanına kaydetme hatası: {e}")

# ==========================================
# SEKME 2: VERİTABANI KAYITLARI & FİLTRELEME
# ==========================================
with tab2:
    selected_date = st.date_input("📅 İncelemek İstediğiniz Tarih:", datetime.now())
    formatted_date_str = selected_date.strftime("%d/%m/%Y")
    
    st.markdown(
        f"""
        <div style="background-color: #0F172A; border-left: 5px solid #3B82F6; padding: 10px 15px; border-radius: 6px; margin-bottom: 15px;">
            <h4 style="color: #F8FAFC; margin: 0;">
                📌 <span style="color: #60A5FA;">{formatted_date_str}</span> Kayıtları
            </h4>
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
                            r["formatted_time"] = dt_obj.strftime("%H:%M")
                            filtered_rows.append(r)
                    except Exception:
                        pass

            if filtered_rows:
                gunluk_toplam_kar = sum(item["net_kar_tl"] for item in filtered_rows)
                gunluk_toplam_ciro = sum(item["kazanc_tl"] for item in filtered_rows)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Satış", f"{len(filtered_rows)} Adet")
                m2.metric("Ciro", f"{gunluk_toplam_ciro:.0f} TL")
                m3.metric("Net Kar", f"{gunluk_toplam_kar:.0f} TL", delta=f"{gunluk_toplam_kar:.0f} TL")
                
                st.markdown("---")

                # Mobil İçin Kart Tipi Satırlar (Daha Rahat Okuma ve Silme)
                for r in filtered_rows:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            kar_val = r['net_kar_tl']
                            kar_html = f"<span style='color:#10B981; font-weight:bold;'>+{kar_val:.2f} TL</span>" if kar_val >= 0 else f"<span style='color:#EF4444; font-weight:bold;'>{kar_val:.2f} TL</span>"
                            st.markdown(f"**Saat {r['formatted_time']}** | Kar: {kar_html}", unsafe_allow_html=True)
                            st.caption(f"Kazanç: {r['kazanc_tl']:.2f} TL | Gider: {r['gider_tl']:.2f} TL | Kur: {r['kur']:.2f} TL")
                        with c2:
                            if st.button("🗑️", key=f"del_{r['id']}", type="secondary", use_container_width=True):
                                supabase.table("satislar").delete().eq("id", r["id"]).execute()
                                st.toast("Kayıt silindi!", icon="🗑️")
                                st.rerun()

            else:
                st.info(f"💡 {formatted_date_str} tarihinde henüz kaydınız bulunmuyor.")
        else:
            st.info("Veritabanında henüz kayıtlı bir satış bulunmuyor.")

    except Exception as e:
        st.error(f"Kayıtlar çekilirken hata oluştu: {e}")
