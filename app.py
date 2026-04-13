import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import time

st.set_page_config(page_title="T3 MTF Sinyal Tarayıcı", layout="wide", page_icon="📈")

# ── HISSE LİSTESİ ──────────────────────────────────────────────────────────────
BIST100 = [
    "AEFES","AGHOL","AKBNK","AKSA","AKSEN","ALARK","ALTNY","ANSGR","ARCLK","ASELS",
    "ASTOR","BALSU","BIMAS","BRSAN","BRYAT","BSOKE","BTCIM","CANTE","CCOLA","CIMSA",
    "CVKMD","CWENE","DAPGM","DOAS","DOHOL","DSTKF","ECILC","EFOR","EKGYO","ENERY",
    "ENJSA","ENKAI","EREGL","EUPWR","EUREN","FENER","FROTO","GARAN","GENIL","GESAN",
    "GLRMK","GRSEL","GRTHO","GSRAY","GUBRF","HALKB","HEKTS","ISCTR","ISMEN","IZENR",
    "KCHOL","KLRHO","KONTR","KRDMD","KTLEV","KUYAS","LOGO","MAVI","MGROS","ODAS",
    "OTKAR","OYAKC","PETKM","PGSUS","QUAGR","SAHOL","SASA","SELEC","SISE","SKBNK",
    "SMRTG","SOKM","TAVHL","TCELL","THYAO","TKFEN","TKNSA","TOASO","TSKB","TTKOM",
    "TTRAK","TUPRS","TURSG","ULAS","ULKER","VAKBN","VERUS","VESTL","YKBNK","YYLGD",
    "ZRGYO","ZOREN","NTHOL","MPARK","BERA","CEMAS","ASUZU","SEGYO","BIOEN","INDES",
]

EK_HISSELER = [
    "AKFYE","ASGR","ORGE","HTTBT","SDTTR","OYYAT","NETCAD",
    "VBTYZ","EGEGY","RYSAS","TGSAS","ATATP","KCAER","A1CAP",
]

TUM_HISSELER = sorted(list(set(BIST100 + EK_HISSELER)))

# ── T3 HESAPLAMA ───────────────────────────────────────────────────────────────
def hesapla_t3(close, length=7, factor=0.7):
    def ema(s, n):
        return s.ewm(span=n, adjust=False).mean()

    e1 = ema(close, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    e4 = ema(e3, length)
    e5 = ema(e4, length)
    e6 = ema(e5, length)

    c1 = -(factor ** 3)
    c2 = 3 * factor**2 + 3 * factor**3
    c3 = -6 * factor**2 - 3 * factor - 3 * factor**3
    c4 = 1 + 3 * factor + factor**3 + 3 * factor**2

    return c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3

def sinyal_bul(ticker, timeframe, length=7, factor=0.7, lookback=50):
    sembol = ticker + ".IS"
    try:
        tf_map = {"4s": ("60m", "60d"), "1g": ("1d", "400d")}
        interval, period = tf_map[timeframe]
        df = yf.download(sembol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or len(df) < length * 6 + 5:
            return None
        close = df["Close"].squeeze()
        t3 = hesapla_t3(close, length, factor)
        # Al sinyali: t3 önceki barın t3'ünün üstüne geçti
        sinyal_barlari = []
        for i in range(1, min(lookback, len(t3)-1)):
            idx = -(i+1)
            if t3.iloc[idx] < t3.iloc[idx-1] and t3.iloc[idx+1] >= t3.iloc[idx]:
                sinyal_barlari.append(("AL", i))
                break
            if t3.iloc[idx] > t3.iloc[idx-1] and t3.iloc[idx+1] <= t3.iloc[idx]:
                sinyal_barlari.append(("SAT", i))
                break
        # Son durum: hala AL mı SAT mı
        son_durum = "AL" if t3.iloc[-1] >= t3.iloc[-2] else "SAT"
        # En son crossover bul
        for i in range(1, min(lookback, len(t3)-1)):
            cur  = t3.iloc[-(i+1)]
            prev = t3.iloc[-(i+2)]
            nxt  = t3.iloc[-i]
            if prev < cur and nxt >= cur:  # yukarı kırım = AL
                return {"durum": "AL", "mum_once": i, "son_t3": round(float(t3.iloc[-1]), 2)}
            if prev > cur and nxt <= cur:  # aşağı kırım = SAT
                return {"durum": "SAT", "mum_once": i, "son_t3": round(float(t3.iloc[-1]), 2)}
        return {"durum": son_durum, "mum_once": ">"+str(lookback), "son_t3": round(float(t3.iloc[-1]), 2)}
    except Exception:
        return None

# ── TARAMA ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def tara(hisseler, length, factor):
    sonuclar = []
    for ticker in hisseler:
        s4 = sinyal_bul(ticker, "4s", length, factor)
        s1g = sinyal_bul(ticker, "1g", length, factor)
        if s4 is None and s1g is None:
            continue
        # En az birinde sinyal varsa ekle
        durum_4s  = s4["durum"]  if s4  else "-"
        once_4s   = s4["mum_once"] if s4 else "-"
        durum_1g  = s1g["durum"] if s1g else "-"
        once_1g   = s1g["mum_once"] if s1g else "-"
        # Genel durum: AL varsa AL (herhangi birinde)
        genel = "AL" if "AL" in [durum_4s, durum_1g] else "SAT"
        sonuclar.append({
            "Hisse": ticker,
            "Genel": genel,
            "4S Sinyal": durum_4s,
            "4S Mum Önce": once_4s,
            "1G Sinyal": durum_1g,
            "1G Mum Önce": once_1g,
        })
    return pd.DataFrame(sonuclar)

# ── ARAYÜZ ─────────────────────────────────────────────────────────────────────
st.title("📈 Tilson T3 MTF Sinyal Tarayıcı")
st.caption("BIST100 + Ek Hisseler | 4 Saatlik & Günlük | Otomatik Yenileme")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    length     = st.slider("T3 Uzunluk", 2, 20, 7)
    factor_raw = st.slider("T3 Faktör (×0.10)", 1, 10, 7)
    factor     = factor_raw * 0.10
    yenileme   = st.slider("Yenileme (dakika)", 1, 60, 5)
    st.markdown("---")
    st.info(f"Toplam: **{len(TUM_HISSELER)}** hisse taranıyor")
    st.caption(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")

# Otomatik yenileme
st_autorefresh = st.empty()
with st_autorefresh:
    st.markdown(
        f'<meta http-equiv="refresh" content="{yenileme*60}">',
        unsafe_allow_html=True
    )

with st.spinner("Hisseler taranıyor, lütfen bekleyin..."):
    df = tara(tuple(TUM_HISSELER), length, factor)

if df.empty:
    st.warning("Hiç sinyal bulunamadı veya veri çekilemedi.")
    st.stop()

# AL/SAT ayrımı — AL listesindekiler SAT'tan otomatik çıkar
al_df  = df[df["Genel"] == "AL"].copy()
sat_df = df[(df["Genel"] == "SAT") & (~df["Hisse"].isin(al_df["Hisse"]))].copy()

# ── AL TABLOSU ──────────────────────────────────────────────────────────────────
st.markdown("## 🟢 AL Sinyali")
st.caption(f"{len(al_df)} hisse | 4S veya 1G grafiğinde AL sinyali var")

def renk_sinyal(val):
    if val == "AL":
        return "background-color: #1a3a1a; color: #00ff88; font-weight:bold"
    elif val == "SAT":
        return "background-color: #3a1a1a; color: #ff4444; font-weight:bold"
    return ""

if not al_df.empty:
    al_df = al_df.sort_values("4S Mum Önce")
    st.dataframe(
        al_df[["Hisse","4S Sinyal","4S Mum Önce","1G Sinyal","1G Mum Önce"]]
        .reset_index(drop=True)
        .style.applymap(renk_sinyal, subset=["4S Sinyal","1G Sinyal"]),
        use_container_width=True,
        height=400
    )
else:
    st.info("Şu an AL sinyali veren hisse yok.")

st.markdown("---")

# ── SAT TABLOSU ─────────────────────────────────────────────────────────────────
st.markdown("## 🔴 SAT Sinyali")
st.caption(f"{len(sat_df)} hisse | AL listesinde olmayanlar")

if not sat_df.empty:
    sat_df = sat_df.sort_values("4S Mum Önce")
    st.dataframe(
        sat_df[["Hisse","4S Sinyal","4S Mum Önce","1G Sinyal","1G Mum Önce"]]
        .reset_index(drop=True)
        .style.applymap(renk_sinyal, subset=["4S Sinyal","1G Sinyal"]),
        use_container_width=True,
        height=400
    )
else:
    st.info("Şu an SAT sinyali veren hisse yok.")

st.markdown("---")
st.caption("⚠️ Bu uygulama yatırım tavsiyesi değildir. Veriler yfinance üzerinden çekilmektedir.")
