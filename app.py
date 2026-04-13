import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import time

st.set_page_config(page_title="T3 MTF Sinyal Tarayıcı", layout="wide", page_icon="📈")

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
T3_LENGTH    = 7
T3_FACTOR    = 0.7
YENILEME_DK  = 60

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
        if not isinstance(close, pd.Series):
            return None
        t3 = hesapla_t3(close, length, factor)
        son_durum = "AL" if float(t3.iloc[-1]) >= float(t3.iloc[-2]) else "SAT"
        for i in range(1, min(lookback, len(t3) - 2)):
            prev = float(t3.iloc[-(i+2)])
            cur  = float(t3.iloc[-(i+1)])
            nxt  = float(t3.iloc[-i])
            if prev < cur and nxt >= cur:
                return {"durum": "AL",  "mum_once": i}
            if prev > cur and nxt <= cur:
                return {"durum": "SAT", "mum_once": i}
        return {"durum": son_durum, "mum_once": lookback + 1}
    except Exception:
        return None

def tara(hisseler):
    sonuclar = []
    toplam = len(hisseler)
    progress_bar = st.progress(0, text="Tarama başlıyor...")
    for idx, ticker in enumerate(hisseler):
        pct = (idx + 1) / toplam
        progress_bar.progress(pct, text=f"🔍 Tarıyor: {ticker}  ({idx+1}/{toplam})")
        s4  = sinyal_bul(ticker, "4s", T3_LENGTH, T3_FACTOR)
        s1g = sinyal_bul(ticker, "1g", T3_LENGTH, T3_FACTOR)
        if s4 is None and s1g is None:
            continue
        durum_4s = s4["durum"]         if s4  else "-"
        once_4s  = int(s4["mum_once"]) if s4  else 9999
        durum_1g = s1g["durum"]        if s1g else "-"
        once_1g  = int(s1g["mum_once"]) if s1g else 9999
        genel = "AL" if "AL" in [durum_4s, durum_1g] else "SAT"
        sonuclar.append({
            "Hisse":       ticker,
            "Genel":       genel,
            "4S Sinyal":   durum_4s,
            "4S Mum Önce": once_4s,
            "1G Sinyal":   durum_1g,
            "1G Mum Önce": once_1g,
        })
    progress_bar.progress(1.0, text="✅ Tarama tamamlandı!")
    time.sleep(0.8)
    progress_bar.empty()
    return pd.DataFrame(sonuclar)

def geri_sayim_bar():
    saniye = YENILEME_DK * 60
    bar   = st.progress(1.0)
    metin = st.empty()
    for kalan in range(saniye, 0, -1):
        dk   = kalan // 60
        sn   = kalan % 60
        oran = kalan / saniye
        bar.progress(oran)
        metin.caption(f"⏳ Sonraki tarama: {dk} dk {sn:02d} sn")
        time.sleep(1)
    bar.empty()
    metin.empty()

def renk_sinyal(val):
    if val == "AL":
        return "background-color: #0d2e0d; color: #00e676; font-weight:bold"
    elif val == "SAT":
        return "background-color: #2e0d0d; color: #ff5252; font-weight:bold"
    return "color: #888888"

def stil_uygula(df):
    # applymap yerine map — pandas 2.x uyumlu
    try:
        return df.style.map(renk_sinyal, subset=["4S Sinyal","1G Sinyal"])
    except AttributeError:
        return df.style.applymap(renk_sinyal, subset=["4S Sinyal","1G Sinyal"])

def mum_label(val):
    if val >= 9999:
        return ">50"
    return str(val)

def tablo_hazirla(df):
    goster = df.sort_values("4S Mum Önce")[
        ["Hisse","4S Sinyal","4S Mum Önce","1G Sinyal","1G Mum Önce"]
    ].reset_index(drop=True)
    goster["4S Mum Önce"] = goster["4S Mum Önce"].apply(mum_label)
    goster["1G Mum Önce"] = goster["1G Mum Önce"].apply(mum_label)
    return goster

# ── ANA DÖNGÜ ──────────────────────────────────────────────────────────────────
st.title("📈 Tilson T3 MTF Sinyal Tarayıcı")
st.caption(f"BIST100 + Ek Hisseler  |  T3 Length: {T3_LENGTH}  |  Factor: {T3_FACTOR}  |  Yenileme: {YENILEME_DK} dk")

with st.sidebar:
    st.header("ℹ️ Bilgi")
    st.metric("Toplam Hisse", len(TUM_HISSELER))
    st.metric("T3 Uzunluk",   T3_LENGTH)
    st.metric("T3 Faktör",    T3_FACTOR)
    st.metric("Yenileme",     f"{YENILEME_DK} dk")
    st.markdown("---")
    st.info("Ayarlar sabittir.\nLength: 7 | Factor: 0.7")

while True:
    guncelleme = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    df = tara(TUM_HISSELER)

    if df.empty:
        st.warning("Hiç sinyal bulunamadı veya veri çekilemedi.")
    else:
        al_df  = df[df["Genel"] == "AL"].copy()
        sat_df = df[(df["Genel"] == "SAT") & (~df["Hisse"].isin(al_df["Hisse"]))].copy()

        st.markdown("---")
        st.markdown(f"## 🟢 AL Sinyali — {len(al_df)} hisse")
        st.caption(f"Güncelleme: {guncelleme}")
        if not al_df.empty:
            al_g = tablo_hazirla(al_df)
            st.dataframe(
                stil_uygula(al_g),
                use_container_width=True,
                height=min(500, 40 + len(al_g) * 36),
            )
        else:
            st.info("Şu an AL sinyali veren hisse yok.")

        st.markdown(f"## 🔴 SAT Sinyali — {len(sat_df)} hisse")
        if not sat_df.empty:
            sat_g = tablo_hazirla(sat_df)
            st.dataframe(
                stil_uygula(sat_g),
                use_container_width=True,
                height=min(500, 40 + len(sat_g) * 36),
            )
        else:
            st.info("Şu an SAT sinyali veren hisse yok.")

    st.markdown("---")
    st.caption("⚠️ Bu uygulama yatırım tavsiyesi değildir.")

    geri_sayim_bar()
    st.rerun()
