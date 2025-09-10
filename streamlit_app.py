import os, random, string
import streamlit as st
import pandas as pd
from dateutil import parser
from datetime import datetime, date, time, timedelta

# ---- Optional deps: Plotly / Graphviz (없으면 자동 폴백) ----
PLOTLY_OK = True
try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    PLOTLY_OK = False

GRAPHVIZ_OK = True
try:
    from graphviz import Digraph
except Exception:
    GRAPHVIZ_OK = False

st.set_page_config(page_title="Jeju SME · Welfare Integration Board", layout="wide")

# -------------------- 파일/데이터 --------------------
DATA_DIR = "data"
PATH_ROADMAP = os.path.join(DATA_DIR, "actions.csv")
PATH_SENIORS = os.path.join(DATA_DIR, "seniors.csv")
PATH_VISITS  = os.path.join(DATA_DIR, "visits.csv")
PATH_FUND    = os.path.join(DATA_DIR, "fund_ledger.csv")

SAMPLE_ACTIONS = [
    {"phase":"단기(1~6개월)","task":"제주어 병기 메뉴판/영수증 적용","owner":"매장","cost_krw":50000,"due":"2025-10-01","status":"진행중","segment":"도민","impact_score":3},
    {"phase":"단기(1~6개월)","task":"도민 전용 주소인증 할인 시범","owner":"매장","cost_krw":0,"due":"2025-10-15","status":"계획","segment":"도민","impact_score":4},
    {"phase":"중기(6~12개월)","task":"생활 구독(커피+빵) 출시","owner":"연합","cost_krw":200000,"due":"2026-02-01","status":"계획","segment":"도민","impact_score":5},
    {"phase":"중기(6~12개월)","task":"원데이 체험 클래스(향토/공예)","owner":"협업","cost_krw":150000,"due":"2026-03-01","status":"계획","segment":"관광객","impact_score":4},
    {"phase":"장기(1~3년)","task":"도민 레시피 → 관광객 한정 메뉴","owner":"연합","cost_krw":100000,"due":"2026-10-01","status":"계획","segment":"연계","impact_score":5},
]

def _ensure_dir(): os.makedirs(DATA_DIR, exist_ok=True)

def ensure_files():
    _ensure_dir()
    if not os.path.exists(PATH_ROADMAP):
        pd.DataFrame(SAMPLE_ACTIONS).to_csv(PATH_ROADMAP, index=False)
    if not os.path.exists(PATH_SENIORS):
        pd.DataFrame(columns=[
            "senior_id","name","phone","address","caregiver","caregiver_phone",
            "risk_tier","welfare_points","pin","last_visit_date"
        ]).to_csv(PATH_SENIORS, index=False)
    if not os.path.exists(PATH_VISITS):
        pd.DataFrame(columns=[
            "ts","senior_id","name","store","systolic","diastolic","weight_kg","notes"
        ]).to_csv(PATH_VISITS, index=False)
    if not os.path.exists(PATH_FUND):
        pd.DataFrame(columns=[
            "ts","type","amount","store","memo","donation_rate"
        ]).to_csv(PATH_FUND, index=False)

@st.cache_data
def load_df(path, fallback=None):
    ensure_files()
    try:
        return pd.read_csv(path)
    except Exception:
        return fallback if fallback is not None else pd.DataFrame()

def save_df(path, df):
    df.to_csv(path, index=False)
    st.cache_data.clear()

def clean_date(x):
    try:
        return parser.parse(str(x)).date()
    except Exception:
        return None

def phase_rank(x):
    return {"단기(1~6개월)":0,"중기(6~12개월)":1,"장기(1~3년)":2}.get(x,99)

def make_coupon(prefix="JEJU", n=6):
    return f"{prefix}-" + "".join(random.choices(string.ascii_uppercase+string.digits, k=n))

# -------------------- 사이드바 --------------------
st.sidebar.title("제주 소상공인 × 복지 통합 보드")
STORE = st.sidebar.text_input("상호명", value="혼저커피(예시)")
st.sidebar.write("---")
uploaded_actions = st.sidebar.file_uploader("로드맵 CSV 업로드", type=["csv"])
uploaded_seniors = st.sidebar.file_uploader("어르신 명부 CSV 업로드", type=["csv"])
uploaded_visits  = st.sidebar.file_uploader("방문기록 CSV 업로드", type=["csv"])
uploaded_fund    = st.sidebar.file_uploader("기금 장부 CSV 업로드", type=["csv"])

# -------------------- 데이터 적재 --------------------
if "actions" not in st.session_state:  st.session_state.actions = load_df(PATH_ROADMAP, pd.DataFrame(SAMPLE_ACTIONS))
if "seniors" not in st.session_state:  st.session_state.seniors = load_df(PATH_SENIORS)
if "visits"  not in st.session_state:  st.session_state.visits  = load_df(PATH_VISITS)
if "fund"    not in st.session_state:  st.session_state.fund    = load_df(PATH_FUND)

if uploaded_actions is not None: st.session_state.actions = pd.read_csv(uploaded_actions)
if uploaded_seniors is not None: st.session_state.seniors = pd.read_csv(uploaded_seniors)
if uploaded_visits  is not None: st.session_state.visits  = pd.read_csv(uploaded_visits)
if uploaded_fund    is not None: st.session_state.fund    = pd.read_csv(uploaded_fund)

actions = st.session_state.actions.copy()
seniors = st.session_state.seniors.copy()
visits  = st.session_state.visits.copy()
fund    = st.session_state.fund.copy()

# 타입 정리
if "due" in actions: actions["due"] = actions["due"].apply(clean_date)
if "last_visit_date" in seniors: seniors["last_visit_date"] = seniors["last_visit_date"].apply(clean_date)
if "ts" in visits:
    try: visits["ts"] = pd.to_datetime(visits["ts"])
    except: pass
if "ts" in fund:
    try: fund["ts"] = pd.to_datetime(fund["ts"])
    except: pass

# -------------------- UI --------------------
st.title("🌊 제주 소상공인 · 노인 돌봄/복지 통합 실행 보드")
tabs = st.tabs(["전략 맵", "로드맵", "복지 허브(어르신)", "오퍼 연구소", "기금/대시보드"])

# ====== 1) 전략 맵 ======
with tabs[0]:
    st.subheader("📌 제주형 이중 포지셔닝 + 복지 연계 전략 맵")
    counts = actions.groupby("phase")["task"].count().to_dict()

    if GRAPHVIZ_OK:
        g = Digraph("jeju_strategy", format="svg")
        g.attr(rankdir="TB", bgcolor="white", fontname="NanumGothic, Malgun Gothic, Arial")
        g.node("brand", "제주 소상공인 브랜드", shape="box", style="rounded,filled", fillcolor="#e6f7ff")
        g.node("daily", f"생활 속 브랜드(도민)\n실행:{counts.get('단기(1~6개월)',0)}", shape="box", style="rounded,filled", fillcolor="#eaffea")
        g.node("exp",   f"특별한 경험(관광객)\n실행:{counts.get('중기(6~12개월)',0)}", shape="box", style="rounded,filled", fillcolor="#fff5e6")
        g.node("care",  "복지 허브(노인 안부/체크포인트)\n미방문 경보·건강기록·복지포인트", shape="box", style="rounded,filled", fillcolor="#ffe6ef")
        g.node("sust",  "지속가능한 제주형 가치\n(협동·RE100·제로웨이스트·돌봄기금)", shape="box", style="rounded,filled", fillcolor="#f0e6ff")
        g.edge("brand","daily"); g.edge("brand","exp"); g.edge("brand","care")
        g.edge("daily","sust", label="공동체·생활"); g.edge("exp","sust", label="체험·스토리"); g.edge("care","sust", label="복지·ESG")
        st.graphviz_chart(g, use_container_width=True)
    else:
        st.info("Graphviz 미설치 → 요약 수치로 대체합니다.")
        st.markdown(f"""
- **생활(도민) 실행**: {counts.get('단기(1~6개월)',0)}  
- **체험(관광객) 실행**: {counts.get('중기(6~12개월)',0)}  
- **복지 허브 노드**: 어르신 수 {len(seniors)}명 / 방문기록 {len(visits)}건 / 기금건수 {len(fund)}건
""")

# ====== 2) 로드맵 ======
with tabs[1]:
    st.subheader("🗺️ 로드맵 관리")
    with st.form("add_action", clear_on_submit=True):
        c = st.columns([1,2,1,1,1,1,1])
        phase   = c[0].selectbox("단계", ["단기(1~6개월)","중기(6~12개월)","장기(1~3년)"])
        task    = c[1].text_input("작업")
        owner   = c[2].text_input("담당", value="매장")
        cost    = c[3].number_input("비용(₩)", 0, 10**9, 0, step=1000)
        due     = c[4].date_input("마감일", value=pd.Timestamp.today())
        status  = c[5].selectbox("상태", ["계획","진행중","완료","보류"])
        segment = c[6].selectbox("세그먼트", ["도민","관광객","연계"])
        i2 = st.columns([1,3])
        impact  = i2[0].slider("임팩트(1~5)", 1,5,3)
        ok = i2[1].form_submit_button("추가")
        if ok and task.strip():
            new = {"phase":phase,"task":task,"owner":owner,"cost_krw":cost,"due":due.isoformat(),"status":status,"segment":segment,"impact_score":impact}
            actions = pd.concat([actions, pd.DataFrame([new])], ignore_index=True)
            save_df(PATH_ROADMAP, actions)
            st.success("작업이 추가되었습니다.")

    f1, f2, f3, f4 = st.columns(4)
    fil_phase = f1.multiselect("단계", sorted(actions["phase"].dropna().unique().tolist()))
    fil_status = f2.multiselect("상태", sorted(actions["status"].dropna().unique().tolist()))
    fil_seg = f3.multiselect("세그먼트", sorted(actions["segment"].dropna().unique().tolist()))
    fil_q = f4.text_input("검색")

    adf = actions.copy()
    adf["due"] = adf["due"].apply(clean_date)
    if fil_phase: adf = adf[adf["phase"].isin(fil_phase)]
    if fil_status: adf = adf[adf["status"].isin(fil_status)]
    if fil_seg: adf = adf[adf["segment"].isin(fil_seg)]
    if fil_q: adf = adf[adf["task"].str.contains(fil_q, case=False, na=False)]
    adf["phase_rank"] = adf["phase"].apply(phase_rank)
    adf = adf.sort_values(["phase_rank","due"]).drop(columns=["phase_rank"])
    st.dataframe(adf, use_container_width=True)
    st.download_button("로드맵 CSV 다운로드", adf.to_csv(index=False).encode("utf-8-sig"), "jeju_roadmap.csv", "text/csv")

# ====== 3) 복지 허브 ======
with tabs[2]:
    st.subheader("🧓 복지 허브: 어르신 등록 · 안부체크 · 경보")
    colA, colB = st.columns([1,1])

    # --- A) 어르신 등록/조회
    with colA:
        st.markdown("### 어르신 등록")
        with st.form("add_senior", clear_on_submit=True):
            name = st.text_input("성함")
            phone = st.text_input("연락처")
            address = st.text_input("주소(선택)")
            cg = st.text_input("보호자/담당자")
            cg_phone = st.text_input("보호자 연락처")
            risk = st.selectbox("위험군", ["일반","주의","고위험"])
            points = st.number_input("복지 포인트", 0, 10**9, 0, step=100)
            pin = st.text_input("체크인 PIN(4~6자리, 미입력 시 자동 생성)", value="")
            ok = st.form_submit_button("등록")
            if ok and name.strip():
                senior_id = "S" + "".join(random.choices(string.digits, k=6))
                if not pin.strip():
                    pin = "".join(random.choices(string.digits, k=4))
                new = {
                    "senior_id": senior_id, "name": name, "phone": phone, "address": address,
                    "caregiver": cg, "caregiver_phone": cg_phone, "risk_tier": risk,
                    "welfare_points": points, "pin": pin, "last_visit_date": ""
                }
                seniors = pd.concat([seniors, pd.DataFrame([new])], ignore_index=True)
                save_df(PATH_SENIORS, seniors)
                st.success(f"등록 완료! ID:{senior_id}, PIN:{pin}")

        st.markdown("### 어르신 명부")
        st.dataframe(seniors, use_container_width=True)
        st.download_button("어르신 명부 CSV 다운로드", seniors.to_csv(index=False).encode("utf-8-sig"), "seniors.csv", "text/csv")

    # --- B) 안부 체크 · 경보
    with colB:
        st.markdown("### 매장 방문 체크인(안부)")
        if len(seniors)==0:
            st.info("먼저 어르신을 등록하세요.")
        else:
            srow = st.selectbox("대상자", seniors["name"] + " ("+ seniors["senior_id"] +")")
            sid = srow.split("(")[-1][:-1]
            _pin = st.text_input("체크인 PIN 입력")
            systolic = st.number_input("수축기 혈압", 0, 400, 0, step=1)
            diastolic = st.number_input("이완기 혈압", 0, 300, 0, step=1)
            weight = st.number_input("체중(kg)", 0.0, 300.0, 0.0, step=0.1)
            notes = st.text_input("비고")
            earn_pt = st.number_input("방문 포인트 적립(+)", 0, 10000, 0, step=10)
            if st.button("체크인 기록"):
                row = seniors[seniors["senior_id"]==sid].iloc[0]
                if str(row.get("pin","")) != _pin:
                    st.error("PIN 불일치")
                else:
                    now = datetime.utcnow()
                    v = {"ts": now.isoformat(), "senior_id": sid, "name": row["name"], "store": STORE,
                         "systolic": systolic or "", "diastolic": diastolic or "", "weight_kg": weight or "", "notes": notes}
                    visits = pd.concat([visits, pd.DataFrame([v])], ignore_index=True)
                    # update last_visit & points
                    seniors.loc[seniors["senior_id"]==sid, "last_visit_date"] = date.today().isoformat()
                    seniors.loc[seniors["senior_id"]==sid, "welfare_points"] = pd.to_numeric(seniors.loc[seniors["senior_id"]==sid, "welfare_points"]).fillna(0) + earn_pt
                    save_df(PATH_VISITS, visits); save_df(PATH_SENIORS, seniors)
                    st.success("안부 체크 완료!")

        st.markdown("### 미방문 경보")
        threshold = st.slider("미방문 경보 기준(일)", 3, 30, 7)
        tmp = seniors.copy()
        tmp["last_visit_date"] = tmp["last_visit_date"].apply(clean_date)
        tmp["days_from_last"] = tmp["last_visit_date"].apply(lambda d: (date.today() - d).days if isinstance(d, date) else 10**9)
        alert_df = tmp[tmp["days_from_last"] >= threshold].sort_values("days_from_last", ascending=False)
        st.warning(f"경보 대상 {len(alert_df)}명")
        st.dataframe(alert_df[["senior_id","name","phone","caregiver","caregiver_phone","risk_tier","last_visit_date","days_from_last"]], use_container_width=True)

        st.markdown("**문자/카톡 템플릿**")
        if len(alert_df):
            s0 = alert_df.iloc[0]
            msg = f"[{STORE}] {s0['name']} 어르신이 {s0['days_from_last']}일째 미방문입니다. 연락처 {s0['phone']} / 보호자 {s0['caregiver']}({s0['caregiver_phone']})."
            st.code(msg)

        st.markdown("### 방문 기록")
        st.dataframe(visits.sort_values("ts", ascending=False), use_container_width=True)
        st.download_button("방문 기록 CSV 다운로드", visits.to_csv(index=False).encode("utf-8-sig"), "visits.csv", "text/csv")

# ====== 4) 오퍼 연구소 ======
with tabs[3]:
    st.subheader("🎟️ 오퍼 연구소 (도민/관광객 + 돌봄기금 연계)")
    c = st.columns(4)
    seg = c[0].selectbox("대상", ["도민","관광객"])
    days = c[1].multiselect("요일", ["월","화","수","목","금","토","일"], default=(["월","화","수","목","금"] if seg=="도민" else ["토","일"]))
    t_from = c[2].time_input("시작시간", value=time(8,0) if seg=="도민" else time(13,0))
    t_to   = c[3].time_input("종료시간", value=time(10,0) if seg=="도민" else time(17,0))
    d2 = st.columns(3)
    pct = d2[0].slider("할인율(%)", 5, 40, 15 if seg=="도민" else 10, step=5)
    minsp = d2[1].number_input("최소결제(₩)", 0, 200000, 5000 if seg=="도민" else 15000, step=1000)
    donate = d2[2].slider("돌봄기금 적립율(%)", 0, 10, 1, step=1)
    prefix = st.text_input("쿠폰 접두사", value="JEJU-D" if seg=="도민" else "JEJU-T")

    if st.button("쿠폰 규칙 생성"):
        code = make_coupon(prefix)
        rule = {
            "segment": seg, "days": days,
            "time_from": t_from.strftime("%H:%M"), "time_to": t_to.strftime("%H:%M"),
            "discount_pct": int(pct), "min_spend": int(minsp),
            "care_fund_rate_pct": int(donate), "code": code
        }
        st.success("쿠폰 규칙이 생성되었습니다.")
        st.json(rule)
        st.download_button("쿠폰 규칙 JSON", pd.Series(rule).to_json(), file_name=f"coupon_{code}.json")

# ====== 5) 기금/대시보드 ======
with tabs[4]:
    st.subheader("💚 관광객 연계 돌봄기금 · 경영 대시보드")
    col1, col2 = st.columns([1,1])

    with col1:
        st.markdown("### 기금 수입/지출 등록")
        tr_type = st.selectbox("유형", ["수입(기부/적립)","지출(돌봄지원)"])
        amt = st.number_input("금액(₩)", 0, 10**9, 0, step=1000)
        memo = st.text_input("메모(예: 관광객 체험 매출 1% 적립)")
        rate = st.slider("적립율(%) 표기용", 0, 20, 1)
        if st.button("장부 기록"):
            now = datetime.utcnow()
            rec = {"ts": now.isoformat(), "type": ("in" if tr_type.startswith("수입") else "out"),
                   "amount": amt, "store": STORE, "memo": memo, "donation_rate": rate}
            fund = pd.concat([fund, pd.DataFrame([rec])], ignore_index=True)
            save_df(PATH_FUND, fund)
            st.success("기록 완료")

        st.markdown("### 장부")
        st.dataframe(fund.sort_values("ts", ascending=False), use_container_width=True)
        st.download_button("기금 장부 CSV", fund.to_csv(index=False).encode("utf-8-sig"), "fund_ledger.csv", "text/csv")

    with col2:
        st.markdown("### 핵심 지표")
        # seniors
        at_df = seniors.copy()
        at_df["last_visit_date"] = at_df["last_visit_date"].apply(clean_date)
        at_df["days_from_last"] = at_df["last_visit_date"].apply(lambda d: (date.today()-d).days if isinstance(d, date) else 10**9)
        at_risk = (at_df["days_from_last"]>=7).sum()
        # fund
        total_in  = pd.to_numeric(fund.loc[fund["type"]=="in","amount"], errors="coerce").fillna(0).sum()
        total_out = pd.to_numeric(fund.loc[fund["type"]=="out","amount"], errors="coerce").fillna(0).sum()
        balance = int(total_in - total_out)

        m = st.columns(4)
        m[0].metric("어르신 수", len(seniors))
        m[1].metric("경보(7일↑) 대상", int(at_risk))
        m[2].metric("방문 기록(총)", len(visits))
        m[3].metric("돌봄기금 잔액(₩)", balance)

        if PLOTLY_OK:
            v1, v2 = st.columns(2)
            if len(fund):
                fdf = fund.copy(); fdf["ts"] = pd.to_datetime(fdf["ts"]).dt.date
                fdf["signed"] = fdf.apply(lambda r: r["amount"] if r["type"]=="in" else -r["amount"], axis=1)
                fig = px.bar(fdf, x="ts", y="signed", color="type", title="기금 흐름(일자별)")
                v1.plotly_chart(fig, use_container_width=True)
            if len(visits):
                vdf = visits.copy(); vdf["ts"] = pd.to_datetime(vdf["ts"]).dt.date
                fig2 = px.histogram(vdf, x="ts", title="어르신 방문 수(일자별)")
                v2.plotly_chart(fig2, use_container_width=True)
        else:
            st.bar_chart(fund.assign(ts=pd.to_datetime(fund["ts"]).dt.date).groupby("ts")["amount"].sum())
            st.bar_chart(visits.assign(ts=pd.to_datetime(visits["ts"]).dt.date).groupby("ts")["name"].count())
