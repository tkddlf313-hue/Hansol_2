import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from openai import OpenAI

# ── 페이지 기본 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="오늘의 종목 대시보드",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Noto Sans KR 폰트 + 공통 CSS ─────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.card {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 4px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.card-name  { font-size: 13px; color: #aaa; margin-bottom: 4px; }
.card-price { font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 4px; }
.card-up    { font-size: 15px; font-weight: 700; color: #FF4444; }
.card-down  { font-size: 15px; font-weight: 700; color: #0066CC; }
.card-flat  { font-size: 15px; font-weight: 700; color: #888; }

.chat-bubble-user {
    background: #2d5a8e;
    color: white;
    border-radius: 12px 12px 2px 12px;
    padding: 10px 14px;
    margin: 6px 0 6px 40px;
    font-size: 14px;
}
.chat-bubble-ai {
    background: #2a2a3e;
    color: #e0e0e0;
    border-radius: 12px 12px 12px 2px;
    padding: 10px 14px;
    margin: 6px 40px 6px 0;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# ── 종목 정의 ─────────────────────────────────────────────────────
KR_STOCKS = {
    "삼성전자":   "005930.KS",
    "SK하이닉스": "000660.KS",
    "NAVER":      "035420.KS",
    "카카오":     "035720.KS",
    "LG에너지솔루션": "373220.KS",
    "현대차":     "005380.KS",
    "POSCO홀딩스": "005490.KS",
    "셀트리온":   "068270.KS",
    "KB금융":     "105560.KS",
    "삼성바이오로직스": "207940.KS",
}

GLOBAL_STOCKS = {
    "Apple":    "AAPL",
    "Microsoft":"MSFT",
    "NVIDIA":   "NVDA",
    "Amazon":   "AMZN",
    "Tesla":    "TSLA",
}

# ── 사이드바 ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 설정")

    period_map = {"7일": 7, "30일": 30, "90일": 90}
    selected_period_label = st.selectbox("📅 조회 기간", list(period_map.keys()), index=1)
    days = period_map[selected_period_label]

    st.markdown("---")
    st.subheader("🤖 AI 챗봇 설정")
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="GPT-4o-mini를 사용하기 위한 API 키를 입력하세요.",
    )

# ── 데이터 수집 ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_data(tickers: dict, days: int) -> dict:
    end   = datetime.today()
    start = end - timedelta(days=days + 5)
    result = {}
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
            if not df.empty:
                result[name] = df
        except Exception:
            pass
    return result

kr_data     = fetch_data(KR_STOCKS, max(days, 30))
global_data = fetch_data(GLOBAL_STOCKS, days)

# ── 현재가·등락률 헬퍼 ────────────────────────────────────────────
def get_quote(df: pd.DataFrame):
    if df is None or df.empty or len(df) < 2:
        return None, None
    close = df["Close"].dropna()
    if len(close) < 2:
        return None, None
    price  = float(close.iloc[-1])
    prev   = float(close.iloc[-2])
    change = (price - prev) / prev * 100
    return price, change

# ── 제목 ─────────────────────────────────────────────────────────
st.title("📈 오늘의 종목 대시보드")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ══════════════════════════════════════════════════════════════════
# 상단 — 종목 카드
# ══════════════════════════════════════════════════════════════════
st.subheader("🇰🇷 한국 종목 현황")

cols = st.columns(len(KR_STOCKS))
for i, (name, ticker) in enumerate(KR_STOCKS.items()):
    df    = kr_data.get(name)
    price, change = get_quote(df)

    with cols[i]:
        if price is None:
            st.markdown(f"""
            <div class="card">
                <div class="card-name">{name}</div>
                <div class="card-price">—</div>
                <div class="card-flat">N/A</div>
            </div>""", unsafe_allow_html=True)
        else:
            arrow       = "▲" if change > 0 else ("▼" if change < 0 else "—")
            color_class = "card-up" if change > 0 else ("card-down" if change < 0 else "card-flat")
            price_fmt   = f"{price:,.0f}원"
            change_fmt  = f"{arrow} {abs(change):.2f}%"
            st.markdown(f"""
            <div class="card">
                <div class="card-name">{name}</div>
                <div class="card-price">{price_fmt}</div>
                <div class="{color_class}">{change_fmt}</div>
            </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# 중단 — 종가 추이 (탭: 한국 / 해외)
# ══════════════════════════════════════════════════════════════════
st.subheader(f"📊 종가 추이 (최근 {days}일)")

tab_kr, tab_global = st.tabs(["🇰🇷 한국 종목", "🌏 해외 종목"])

def draw_line_chart(data_dict: dict, days: int, title: str):
    fig = go.Figure()
    cutoff = datetime.today() - timedelta(days=days)

    for name, df in data_dict.items():
        if df is None or df.empty:
            continue
        close = df["Close"].dropna()
        close = close[close.index >= pd.Timestamp(cutoff)]
        if close.empty:
            continue
        fig.add_trace(go.Scatter(
            x=close.index, y=close.values,
            mode="lines", name=name,
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f}<extra>" + name + "</extra>",
        ))

    fig.update_layout(
        title=title,
        font=dict(family="Noto Sans KR, sans-serif"),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        hovermode="x unified",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_kr:
    draw_line_chart(kr_data, days, "한국 종목 종가 추이")

with tab_global:
    draw_line_chart(global_data, days, "해외 종목 종가 추이")

# ══════════════════════════════════════════════════════════════════
# 하단 — 일간 변동성 막대 차트
# ══════════════════════════════════════════════════════════════════
st.subheader(f"📉 종목별 일간 변동성 (최근 {days}일 평균)")

def calc_volatility(data_dict: dict, days: int) -> pd.DataFrame:
    rows = []
    cutoff = datetime.today() - timedelta(days=days)
    for name, df in data_dict.items():
        if df is None or df.empty:
            continue
        close = df["Close"].dropna()
        close = close[close.index >= pd.Timestamp(cutoff)]
        if len(close) < 2:
            continue
        vol = close.pct_change().dropna().std() * 100
        rows.append({"종목": name, "변동성(%)": round(float(vol), 4)})
    return pd.DataFrame(rows).sort_values("변동성(%)", ascending=False)

all_data = {**kr_data, **global_data}
vol_df   = calc_volatility(all_data, days)

if not vol_df.empty:
    fig_bar = px.bar(
        vol_df, x="종목", y="변동성(%)",
        color="변동성(%)",
        color_continuous_scale=["#0066CC", "#FFAA00", "#FF4444"],
        title=f"종목별 일간 변동성 (표준편차, 최근 {days}일)",
        text_auto=".2f",
    )
    fig_bar.update_layout(
        font=dict(family="Noto Sans KR, sans-serif"),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        coloraxis_showscale=False,
        height=380,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("변동성 데이터를 불러오지 못했습니다.")

# ══════════════════════════════════════════════════════════════════
# 챗봇 — GPT-4o-mini
# ══════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🤖 AI 주식 챗봇 (GPT-4o-mini)")

if not api_key_input:
    st.info("왼쪽 사이드바에 OpenAI API Key를 입력하면 챗봇을 사용할 수 있습니다.")
else:
    # 주식 컨텍스트 요약 생성
    def build_stock_context() -> str:
        lines = ["[현재 주식 데이터 요약]"]
        for name, df in {**kr_data, **global_data}.items():
            price, change = get_quote(df)
            if price is not None:
                direction = "상승" if change > 0 else ("하락" if change < 0 else "보합")
                lines.append(f"- {name}: {price:,.0f} ({direction} {abs(change):.2f}%)")
        return "\n".join(lines)

    SYSTEM_PROMPT = f"""당신은 주식 데이터 분석 전문 AI 어시스턴트입니다.
사용자의 질문에 한국어로 친절하고 간결하게 답변하세요.
아래는 현재 수집된 실시간 주식 데이터입니다. 이 데이터를 기반으로 답변하세요.

{build_stock_context()}

주의: 투자 권유는 하지 않으며, 데이터 분석과 정보 제공만 합니다."""

    # 세션 메시지 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 채팅 내역 표시
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-bubble-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

    # 입력창
    user_input = st.chat_input("주식에 대해 무엇이든 질문하세요...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.markdown(f'<div class="chat-bubble-user">👤 {user_input}</div>', unsafe_allow_html=True)

        try:
            client = OpenAI(api_key=api_key_input)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *st.session_state.messages,
                ],
                temperature=0.7,
                max_tokens=800,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"오류가 발생했습니다: {e}"

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.markdown(f'<div class="chat-bubble-ai">🤖 {answer}</div>', unsafe_allow_html=True)

    # 대화 초기화 버튼
    if st.session_state.get("messages"):
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()
