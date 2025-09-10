import os, streamlit as st, pandas as pd
from dateutil import parser
from datetime import time

st.set_page_config(page_title="Jeju SME Strategy (Lite)", layout="wide")

DATA_DIR, DATA_PATH = "data", "data/sample_actions.csv"
SAMPLE_ROWS = [
    {"phase":"단기(1~6개월)","task":"제주어 병기 메뉴판/영수증 적용","owner":"매장","cost_krw":50000,"due":"2025-10-01","status":"진행중","segment":"도민","impact_score":3},
    {"phase":"단기(1~6개월)","task":"도민 전용 주소인증 할인 시범","owner":"매장","cost_krw":0,"due":"2025-10-15","status":"계획","segment":"도민","impact_score":4},
    {"phase":"단기(1~6개월)","task":"제주어 퀴즈 컵홀더 SNS 이벤트","owner":"매장","cost_krw":70000,"due":"2025-11-01","status":"계획","segment":"관광객","impact_score":3},
    {"phase":"중기(6~12개월)","task":"생활 구독(커피+빵) 출시","owner":"연합","cost_krw":200000,"due":"2026-02-01","status":"계획","segment":"도민","impact_score":5},
    {"phase":"중기(6~12개월)","task":"원데이 체험 클래스(향토/공예)","owner":"협업","cost_krw":150000,"due":"2026-03-01","status":"계획","segment":"관광객","impact_score":4},
    {"phase":"장기(1~3년)","task":"도민 레시피 → 관광객 한정 메뉴","owner":"연합","cost_krw":100000,"due":"2026-10-01","status":"계획","segment":"연계","impact_score":5},
    {"phase":"장기(1~3년)","task":"협동조합형 상점(지분참여) 검토","owner":"연합","cost_krw":0,"due":"2027-04-01","status":"계획","segment":"도민","impact_score":4},
]
def ensure_csv():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_PATH):
        pd.DataFrame(SAMPLE_ROWS).to_csv(DATA_PATH, index=False)
@st.cache_data
def load_df():
    ensure_csv()
    try: df = pd.read_csv(DATA_PATH)
    except: df = pd.DataFrame(SAMPLE_ROWS)
    df["due"] = df["due"].apply(lambda x: parser.parse(str(x)).date() if pd.notna(x) else None)
    return df
def phase_rank(x): return {"단기(1~6개월)":0,"중기(6~12개월)":1,"장기(1~3년)":2}.get(x,99)

st.title("🌊 제주 소상공인 실행 보드 (Lite)")
df = load_df()
st.subheader("📌 전략 맵(요약)")
counts = df.groupby("phase")["task"].count().to_dict()
st.markdown(f"""
- **생활 속 브랜드(도민)** 실행: {counts.get('단기(1~6개월)',0)}
- **특별한 경험(관광객)** 실행: {counts.get('중기(6~12개월)',0)}
- **지속가능 가치(장기)** 실행: {counts.get('장기(1~3년)',0)}
""")

st.subheader("🗺️ 로드맵")
# 간단 CRUD (추가만)
with st.form("add", clear_on_submit=True):
    c = st.columns([1,2,1,1,1,1,1])
    phase = c[0].selectbox("단계", ["단기(1~6개월)","중기(6~12개월)","장기(1~3년)"])
    task  = c[1].text_input("작업")
    owner = c[2].text_input("담당", value="매장")
    cost  = c[3].number_input("비용(₩)", 0, 10**9, 0, step=1000)
    due   = c[4].date_input("마감일")
    stt   = c[5].selectbox("상태", ["계획","진행중","완료","보류"])
    seg   = c[6].selectbox("세그먼트", ["도민","관광객","연계"])
    i2 = st.columns([1,3])
    impact = i2[0].slider("임팩트(1~5)", 1,5,3)
    ok = i2[1].form_submit_button("추가")
    if ok and task.strip():
        df = pd.concat([df, pd.DataFrame([{"phase":phase,"task":task,"owner":owner,"cost_krw":cost,"due":due.isoformat(),"status":stt,"segment":seg,"impact_score":impact}])], ignore_index=True)
        st.cache_data.clear()
        pd.DataFrame(df).to_csv(DATA_PATH, index=False)
        st.success("추가 완료! 상단 메뉴에서 Rerun하면 반영됩니다.")

# 정렬/표시
df2 = df.copy()
df2["phase_rank"] = df2["phase"].apply(phase_rank)
df2 = df2.sort_values(["phase_rank","due"]).drop(columns=["phase_rank"])
st.dataframe(df2, use_container_width=True)

st.subheader("📊 간단 통계")
st.metric("총 작업 수", len(df2))
st.metric("진행중", int((df2["status"]=="진행중").sum()))
st.metric("예상 총비용(₩)", int(df2["cost_krw"].fillna(0).sum()))
st.bar_chart(df2.groupby("phase")["task"].count())
st.bar_chart(df2.groupby("segment")["impact_score"].mean())
