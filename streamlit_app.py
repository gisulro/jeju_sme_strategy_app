import streamlit as st
import pandas as pd
from dateutil import parser
from datetime import datetime, time
import plotly.express as px
import plotly.graph_objects as go

# Try optional graphviz
GRAPHVIZ_OK = True
try:
    from graphviz import Digraph
except Exception:
    GRAPHVIZ_OK = False

st.set_page_config(page_title="Jeju SME Dual Positioning", layout="wide")

# ---------- Utils ----------
@st.cache_data
def load_sample():
    try:
        return pd.read_csv("data/sample_actions.csv")
    except Exception:
        return pd.DataFrame(columns=["phase","task","owner","cost_krw","due","status","segment","impact_score"])

def clean_date(x):
    try:
        return parser.parse(str(x)).date()
    except Exception:
        return None

def phase_order(x):
    order = {"단기(1~6개월)":0, "중기(6~12개월)":1, "장기(1~3년)":2}
    return order.get(x, 99)

def ensure_phase_rank(df):
    if "phase_rank" not in df.columns:
        df["phase_rank"] = df["phase"].apply(phase_order)
    return df

def make_sankey(counts):
    labels = ["제주 소상공인 브랜드","생활 속 브랜드(도민)","특별한 경험(관광객)","지속가능한 제주형 브랜드"]
    source = [0,0,1,2]
    target = [1,2,3,3]
    values = [
        counts.get("단기(1~6개월)",0) + counts.get("중기(6~12개월)",0) or 1,
        counts.get("단기(1~6개월)",0) or 1,
        counts.get("중기(6~12개월)",0) or 1,
        max(counts.get("장기(1~3년)",0), 1)
    ]
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, pad=20, thickness=15),
        link=dict(source=source, target=target, value=values)))
    fig.update_layout(title="전략 맵 (Sankey 대체 시각화)")
    return fig

# ---------- Sidebar ----------
st.sidebar.title("제주 소상공인 실행 보드")
store = st.sidebar.text_input("상호명", value="예: 혼저커피")
mode = st.sidebar.selectbox("대상 세그먼트", ["도민","관광객","연계(도민→관광객)"])
st.sidebar.markdown("---")
st.sidebar.caption("데이터 파일을 불러오면 샘플 대신 사용됩니다.")
uploaded = st.sidebar.file_uploader("로드맵 CSV 업로드", type=["csv"])

if "df" not in st.session_state:
    st.session_state.df = load_sample()

if uploaded is not None:
    st.session_state.df = pd.read_csv(uploaded)

df = st.session_state.df.copy()
df["due"] = df["due"].apply(clean_date)
df = ensure_phase_rank(df)

# ---------- Header ----------
st.title("🌊 제주 소상공인 이중 포지셔닝 실행 보드")
st.caption("도민=생활 속 브랜드 · 관광객=특별한 경험  ⟶  전략 맵 · 로드맵 · 오퍼 생성")

# ---------- Strategy Map ----------
with st.expander("📌 전략 맵 (Strategy Map) 보기 / 숨기기", expanded=True):
    counts = df.groupby("phase")["task"].count().to_dict()

    if GRAPHVIZ_OK:
        from graphviz import Digraph
        g = Digraph("jeju_strategy", format="svg")
        g.attr(rankdir="TB", bgcolor="white", fontname="NanumGothic, Malgun Gothic, Arial")
        g.node("brand", "제주 소상공인 브랜드", shape="box", style="rounded,filled", fillcolor="#e6f7ff")
        g.node("daily", f"생활 속 브랜드\n(도민/시민)\n실행:{counts.get('단기(1~6개월)',0)}", shape="box", style="rounded,filled", fillcolor="#eaffea")
        g.node("exp",   f"특별한 경험\n(관광객)\n실행:{counts.get('중기(6~12개월)',0)}", shape="box", style="rounded,filled", fillcolor="#fff5e6")
        g.node("sust", "지속가능한 제주형 브랜드 가치\n(협동·RE100·제로웨이스트)", shape="box", style="rounded,filled", fillcolor="#f0e6ff")
        g.edge("brand","daily")
        g.edge("brand","exp")
        g.edge("daily","sust", label="공동체·생활")
        g.edge("exp","sust", label="체험·스토리")
        st.graphviz_chart(g, use_container_width=True)
    else:
        st.warning("Graphviz 미설치 → Sankey 대체 시각화 사용 중 (pip install graphviz + 시스템 Graphviz 설치 시 박스형 맵 제공)")
        st.plotly_chart(make_sankey(counts), use_container_width=True)

# ---------- Roadmap CRUD ----------
st.subheader("🗺️ 로드맵 관리")
with st.form("add_item", clear_on_submit=True):
    cols = st.columns([1,2,1,1,1,1,1])
    phase = cols[0].selectbox("단계", ["단기(1~6개월)","중기(6~12개월)","장기(1~3년)"])
    task = cols[1].text_input("작업")
    owner = cols[2].text_input("담당", value="매장")
    cost = cols[3].number_input("비용(₩)", min_value=0, value=0, step=1000)
    due  = cols[4].date_input("마감일", value=pd.Timestamp.today())
    status = cols[5].selectbox("상태", ["계획","진행중","완료","보류"])
    segment = cols[6].selectbox("세그먼트", ["도민","관광객","연계"])
    irow2 = st.columns([1,3])
    impact = irow2[0].slider("임팩트 점수(1~5)", 1,5,3)
    submitted = irow2[1].form_submit_button("추가")

    if submitted and task.strip():
        new = {"phase":phase,"task":task,"owner":owner,"cost_krw":cost,"due":due.isoformat(),"status":status,"segment":segment,"impact_score":impact}
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
        st.success("작업이 추가되었습니다.")

# Filters
fcols = st.columns(4)
f_phase = fcols[0].multiselect("단계 필터", df["phase"].dropna().unique().tolist())
f_status = fcols[1].multiselect("상태 필터", df["status"].dropna().unique().tolist())
f_segment = fcols[2].multiselect("세그먼트 필터", df["segment"].dropna().unique().tolist())
f_search = fcols[3].text_input("검색")

fdf = st.session_state.df.copy()
if f_phase: fdf = fdf[fdf["phase"].isin(f_phase)]
if f_status: fdf = fdf[fdf["status"].isin(f_status)]
if f_segment: fdf = fdf[fdf["segment"].isin(f_segment)]
if f_search: fdf = fdf[fdf["task"].str.contains(f_search, case=False, na=False)]

# Ensure phase_rank exists before sorting
fdf = ensure_phase_rank(fdf)
fdf = fdf.sort_values(["phase_rank","due"]).drop(columns=["phase_rank"])

st.dataframe(fdf, use_container_width=True)

# Download
csv = fdf.to_csv(index=False).encode("utf-8-sig")
st.download_button("현재 로드맵 CSV 다운로드", data=csv, file_name="jeju_roadmap.csv", mime="text/csv")

# ---------- Dashboard ----------
st.subheader("📊 대시보드")
m1, m2, m3 = st.columns(3)
m1.metric("총 작업 수", len(fdf))
m2.metric("진행중", int((fdf["status"]=="진행중").sum()))
m3.metric("예상 총비용(₩)", int(fdf["cost_krw"].fillna(0).sum()))

c1, c2 = st.columns(2)
with c1:
    if len(fdf):
        fig1 = px.histogram(fdf, x="phase", color="status", barmode="group", title="단계별 상태")
        st.plotly_chart(fig1, use_container_width=True)
with c2:
    if len(fdf):
        fig2 = px.box(fdf, x="segment", y="impact_score", title="세그먼트별 임팩트 점수 분포")
        st.plotly_chart(fig2, use_container_width=True)

# ---------- Offers Lab ----------
st.subheader("🎟️ 오퍼 연구소 (도민/관광객 맞춤 쿠폰)")
oc = st.columns(4)
seg = oc[0].selectbox("대상", ["도민","관광객"])
dow = oc[1].multiselect("요일", ["월","화","수","목","금","토","일"], default=["월","화","수","목","금"] if seg=="도민" else ["토","일"])
time_from = oc[2].time_input("시작시간", value=time(8,0) if seg=="도민" else time(13,0))
time_to   = oc[3].time_input("종료시간", value=time(10,0) if seg=="도민" else time(17,0))

dc = st.columns(3)
discount = dc[0].slider("할인율(%)", 5, 40, 15 if seg=="도민" else 10, step=5)
min_spend = dc[1].number_input("최소결제(₩)", 0, 200000, 5000 if seg=="도민" else 15000, step=1000)
prefix = dc[2].text_input("쿠폰 접두사", value="JEJU-D" if seg=="도민" else "JEJU-T")

if st.button("쿠폰 코드 생성"):
    import random, string
    body = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    code = f"{prefix}-{body}"
    rule = {
        "segment": seg,
        "days": dow,
        "time_from": time_from.strftime("%H:%M"),
        "time_to": time_to.strftime("%H:%M"),
        "discount_pct": int(discount),
        "min_spend": int(min_spend),
        "code": code
    }
    st.success("쿠폰 규칙이 생성되었습니다.")
    st.json(rule, expanded=False)
    st.caption("이 JSON을 POS/채팅봇/키오스크 룰로 바로 적용하거나, 파일로 내려받아 사용하세요.")
    st.download_button("쿠폰 규칙 JSON 다운로드", data=pd.Series(rule).to_json(), file_name=f"coupon_{code}.json")

st.info("팁: 도민=평일/아침/생활형 할인, 관광객=주말/오후/체험 패키지 권장")

st.write("---")
st.caption("© Jeju SME Strategy Board · 생활 속 브랜드 × 특별한 경험")
