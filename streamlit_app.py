# -*- coding: utf-8 -*-
import os, io, json, random, string, urllib.parse
import streamlit as st
import pandas as pd
from dateutil import parser
from datetime import datetime, date, time

st.set_page_config(page_title="Jeju SME · Welfare + QR (Final)", layout="wide")

# -------------------- 경로/샘플 --------------------
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
        pd.DataFrame(columns=["ts","senior_id","name","store","systolic","diastolic","weight_kg","notes"])\
          .to_csv(PATH_VISITS, index=False)
    if not os.path.exists(PATH_FUND):
        pd.DataFrame(columns=["ts","type","amount","store","memo","donation_rate"])\
          .to_csv(PATH_FUND, index=False)

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
    try: return parser.parse(str(x)).date()
    except: return None

def phase_rank(x): return {"단기(1~6개월)":0,"중기(6~12개월)":1,"장기(1~3년)":2}.get(x,99)

def make_coupon(prefix="JEJU", n=6):
    return f"{prefix}-" + "".join(random.choices(string.ascii_uppercase+string.digits, k=n))

def _kor_day(dt: datetime):
    return ["월","화","수","목","금","토","일"][dt.weekday()]

def check_coupon_rule(rule: dict, cart_amount: int, segment: str | None = None, now: datetime | None = None):
    now = now or datetime.now()
    if segment and rule.get("segment") and segment != rule["segment"]:
        return (False, "세그먼트 불일치")
    if _kor_day(now) not in rule["days"]:
        return (False, "적용 요일 아님")
    cur = now.strftime("%H:%M")
    if not (rule["time_from"] <= cur <= rule["time_to"]):
        return (False, "적용 시간대 아님")
    if cart_amount < rule["min_spend"]:
        return (False, "최소 결제액 미만")
    discount = int(round(cart_amount * rule["discount_pct"] / 100))
    care_fund = int(round(cart_amount * rule.get("care_fund_rate_pct", 0) / 100))
    return (True, {"discount": discount, "care_fund": care_fund})

# ---- QR 생성: segno 있으면 내부 PNG, 없으면 None (호출부에서 외부 QR 폴백) ----
def qr_png_bytes(data_url: str, scale: int = 6):
    try:
        import segno
        buf = io.BytesIO()
        segno.make(data_url).save(buf, kind="png", scale=scale)
        return buf.getvalue()
    except Exception:
        return None  # 폴백은 호출부에서

# -------------------- 사이드바 --------------------
st.sidebar.title("제주 소상공인 × 복지 통합 보드 + QR")
STORE = st.sidebar.text_input("상호명", value="혼저커피(예시)")
PUBLIC_URL = st.sidebar.text_input(
    "앱 공개 URL",
    value=os.environ.get("PUBLIC_APP_URL", "http://localhost:8501"),
    help="Cloud 주소 또는 로컬 주소 (예: https://your-app.streamlit.app)"
)
st.sidebar.caption("CSV 업로드 시 즉시 반영됩니다.")
up_actions = st.sidebar.file_uploader("로드맵 CSV 업로드", type=["csv"])
up_seniors = st.sidebar.file_uploader("어르신 명부 CSV 업로드", type=["csv"])
up_visits  = st.sidebar.file_uploader("방문기록 CSV 업로드", type=["csv"])
up_fund    = st.sidebar.file_uploader("기금 장부 CSV 업로드", type=["csv"])

# -------------------- 데이터 적재 --------------------
if "actions" not in st.session_state:  st.session_state.actions = load_df(PATH_ROADMAP, pd.DataFrame(SAMPLE_ACTIONS))
if "seniors" not in st.session_state:  st.session_state.seniors = load_df(PATH_SENIORS)
if "visits"  not in st.session_state:  st.session_state.visits  = load_df(PATH_VISITS)
if "fund"    not in st.session_state:  st.session_state.fund    = load_df(PATH_FUND)

# 업로드 즉시 반영
if up_actions is not None: st.session_state.actions = pd.read_csv(up_actions)
if up_seniors is not None: st.session_state.seniors = pd.read_csv(up_seniors)
if up_visits  is not None: st.session_state.visits  = pd.read_csv(up_visits)
if up_fund    is not None: st.session_state.fund    = pd.read_csv(up_fund)

actions = st.session_state.actions.copy()
seniors = st.session_state.seniors.copy()
visits  = st.session_state.visits.copy()
fund    = st.session_state.fund.copy()

if "due" in actions: actions["due"] = actions["due"].apply(clean_date)
if "last_visit_date" in seniors: seniors["last_visit_date"] = seniors["last_visit_date"].apply(clean_date)
if "ts" in visits:
    try: visits["ts"] = pd.to_datetime(visits["ts"])
    except: pass
if "ts" in fund:
    try: fund["ts"] = pd.to_datetime(fund["ts"])
    except: pass

# -------------------- 헤더 & URL 파라미터 --------------------
st.title("🌊 제주 소상공인 · 복지 통합 실행 보드 (Final)")

try:
    params = st.query_params
except Exception:
    params = st.experimental_get_query_params()

def qget(key: str):
    if not isinstance(params, dict): return None
    v = params.get(key)
    return v[0] if isinstance(v, list) else v

# ① 쿠폰 QR 스캔 즉시 검증 (?r=...)
r_param = qget("r")
if r_param:
    st.subheader("🔎 QR 쿠폰 즉시 검증")
    try:
        loaded_rule = json.loads(urllib.parse.unquote(r_param))
        st.success("QR에서 쿠폰 규칙을 불러왔습니다.")
        seg_input = st.selectbox("사용자 세그먼트", ["도민","관광객"], index=0 if loaded_rule.get("segment")=="도민" else 1)
        amt = st.number_input("결제 금액(₩)", 0, 10**9, 15000, step=1000)
        ok, res = check_coupon_rule(loaded_rule, amt, segment=seg_input)
        if ok:
            c1, c2 = st.columns(2)
            c1.metric("할인액(₩)", res["discount"])
            c2.metric("돌봄기금 적립(₩)", res["care_fund"])
            st.balloons()
        else:
            st.error(f"적용 불가: {res}")
        with st.expander("쿠폰 규칙 보기"):
            st.json(loaded_rule)
        st.info("※ 현재 서버시간 기준으로 검증합니다.")
    except Exception as e:
        st.error(f"QR 쿠폰 규칙 해석 오류: {e}")

# ② 어르신 체크인 QR 스캔 모드 (?mode=checkin&sid=...)
if qget("mode") == "checkin" and qget("sid"):
    st.subheader("🧓 QR 체크인")
    sid = qget("sid")
    row = seniors[seniors["senior_id"] == sid]
    if len(row)==0:
        st.error(f"명부에 없는 ID입니다: {sid}")
    else:
        row = row.iloc[0]
        st.info(f"{row['name']} 어르신 체크인")
        pin_in = st.text_input("PIN 입력")
        systolic = st.number_input("수축기 혈압", 0, 400, 0)
        diastolic = st.number_input("이완기 혈압", 0, 300, 0)
        weight = st.number_input("체중(kg)", 0.0, 300.0, 0.0, step=0.1)
        notes = st.text_input("비고")
        if st.button("체크인 기록"):
            if str(row.get("pin","")) != pin_in:
                st.error("PIN 불일치")
            else:
                v = {"ts": datetime.utcnow().isoformat(), "senior_id": sid, "name": row["name"],
                     "store": STORE, "systolic": systolic or "", "diastolic": diastolic or "",
                     "weight_kg": weight or "", "notes": notes}
                visits = pd.concat([visits, pd.DataFrame([v])], ignore_index=True)
                seniors.loc[seniors["senior_id"]==sid, "last_visit_date"] = date.today().isoformat()
                save_df(PATH_VISITS, visits); save_df(PATH_SENIORS, seniors)
                st.success("체크인 완료! (장부에 반영됨)")

# -------------------- 탭 --------------------
tabs = st.tabs(["전략 요약", "로드맵", "복지 허브(업로드 반영 + QR)", "오퍼 연구소(QR 쿠폰)", "기금/대시보드"])

# ---- 1) 전략 요약 ----
with tabs[0]:
    st.subheader("📌 전략 요약")
    counts = actions.groupby("phase")["task"].count().to_dict()
    st.markdown(f"""
- **생활(도민) 실행**: {counts.get('단기(1~6개월)',0)}
- **체험(관광객) 실행**: {counts.get('중기(6~12개월)',0)}
- **복지 허브 지표**: 어르신 {len(seniors)}명 / 방문기록 {len(visits)}건 / 기금 {len(fund)}건
""")
    if len(actions):
        st.bar_chart(actions.groupby("phase")["task"].count())

# ---- 2) 로드맵 ----
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

# ---- 3) 복지 허브 (업로드 반영 + 체크인 QR 생성) ----
with tabs[2]:
    st.subheader("🧓 복지 허브(업로드 반영 + QR 생성)")
    colA, colB = st.columns([1,1])

    with colA:
        st.markdown("### 어르신 명부")
        st.dataframe(seniors, use_container_width=True)
        st.download_button("명부 CSV 다운로드", seniors.to_csv(index=False).encode("utf-8-sig"), "seniors.csv", "text/csv")

        st.markdown("### 신규 등록")
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
                sid = "S" + "".join(random.choices(string.digits, k=6))
                if not pin.strip(): pin = "".join(random.choices(string.digits, k=4))
                new = {"senior_id":sid,"name":name,"phone":phone,"address":address,
                       "caregiver":cg,"caregiver_phone":cg_phone,"risk_tier":risk,
                       "welfare_points":points,"pin":pin,"last_visit_date":""}
                seniors = pd.concat([seniors, pd.DataFrame([new])], ignore_index=True)
                save_df(PATH_SENIORS, seniors)
                st.success(f"등록 완료! ID:{sid}, PIN:{pin}")

    with colB:
        st.markdown("### 체크인(현장 처리)")
        if len(seniors)==0:
            st.info("먼저 어르신을 등록하거나 CSV를 업로드하세요.")
        else:
            sel = st.selectbox("대상자", seniors["name"]+" ("+seniors["senior_id"]+")")
            sid = sel.split("(")[-1][:-1]
            pin_in = st.text_input("체크인 PIN")
            systolic = st.number_input("수축기 혈압", 0, 400, 0)
            diastolic = st.number_input("이완기 혈압", 0, 300, 0)
            weight = st.number_input("체중(kg)", 0.0, 300.0, 0.0, step=0.1)
            notes = st.text_input("비고")
            if st.button("체크인 기록"):
                row = seniors[seniors["senior_id"]==sid].iloc[0]
                if str(row.get("pin","")) != pin_in:
                    st.error("PIN 불일치")
                else:
                    v = {"ts": datetime.utcnow().isoformat(), "senior_id": sid, "name": row["name"],
                         "store": STORE, "systolic": systolic or "", "diastolic": diastolic or "",
                         "weight_kg": weight or "", "notes": notes}
                    visits = pd.concat([visits, pd.DataFrame([v])], ignore_index=True)
                    seniors.loc[seniors["senior_id"]==sid, "last_visit_date"] = date.today().isoformat()
                    save_df(PATH_VISITS, visits); save_df(PATH_SENIORS, seniors)
                    st.success("체크인 완료!")

        st.markdown("### 🧾 어르신별 ‘체크인용’ QR 생성")
        if len(seniors):
            who = st.selectbox("QR 생성 대상", seniors["name"]+" ("+seniors["senior_id"]+")", key="qrsel")
            sid2 = who.split("(")[-1][:-1]
            checkin_url = f"{PUBLIC_URL}?mode=checkin&sid={urllib.parse.quote(sid2)}"
            st.write("체크인 URL:")
            st.code(checkin_url, language="text")

            png = qr_png_bytes(checkin_url, scale=6)
            if png:
                st.image(png, caption="스마트폰 스캔 → 체크인 화면", use_column_width=False)
                st.download_button("체크인 QR PNG 다운로드", data=png, file_name=f"senior_checkin_{sid2}.png", mime="image/png")
            else:
                qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + urllib.parse.quote_plus(checkin_url)
                st.image(qr_url, caption="(외부 서비스) 스캔하여 체크인", use_column_width=False)
                st.write(f"[QR 링크 열기]({qr_url})")

        st.markdown("### 방문 기록")
        st.dataframe(visits.sort_values("ts", ascending=False), use_container_width=True)
        st.download_button("방문기록 CSV", visits.to_csv(index=False).encode("utf-8-sig"), "visits.csv", "text/csv")

# ---- 4) 오퍼 연구소(QR 쿠폰) ----
with tabs[3]:
    st.subheader("🎟️ 오퍼 연구소 (QR 쿠폰)")
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
            "segment": seg,
            "days": days,
            "time_from": t_from.strftime("%H:%M"),
            "time_to": t_to.strftime("%H:%M"),
            "discount_pct": int(pct),
            "min_spend": int(minsp),
            "care_fund_rate_pct": int(donate),
            "code": code
        }
        st.success("쿠폰 규칙이 생성되었습니다.")
        st.json(rule, expanded=False)

        enc = urllib.parse.quote(json.dumps(rule, ensure_ascii=False))
        verify_url = f"{PUBLIC_URL}?r={enc}"
        st.write("검증 URL:")
        st.code(verify_url, language="text")

        png = qr_png_bytes(verify_url, scale=6)
        if png:
            st.image(png, caption="QR 스캔 → 쿠폰 검증 화면", use_column_width=False)
            st.download_button("쿠폰 QR PNG 다운로드", data=png, file_name=f"coupon_{code}.png", mime="image/png")
        else:
            qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + urllib.parse.quote_plus(verify_url)
            st.image(qr_url, caption="(외부 서비스) 스캔하여 쿠폰 검증", use_column_width=False)
            st.write(f"[QR 링크 열기]({qr_url})")

        st.download_button("쿠폰 규칙 JSON", data=pd.Series(rule).to_json(), file_name=f"coupon_{code}.json")

# ---- 5) 기금/대시보드 ----
with tabs[4]:
    st.subheader("💚 돌봄기금 · 경영 대시보드(경량)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 장부 기록")
        t = st.selectbox("유형", ["수입(적립/기부)","지출(돌봄지원)"])
        amt = st.number_input("금액(₩)", 0, 10**9, 0, step=1000)
        memo = st.text_input("메모", "체험 매출 1% 적립")
        rate = st.slider("적립율(%) 표기용", 0, 20, 1)
        if st.button("기록 추가"):
            rec = {"ts": datetime.utcnow().isoformat(), "type": ("in" if t.startswith("수입") else "out"),
                   "amount": amt, "store": STORE, "memo": memo, "donation_rate": rate}
            fund = pd.concat([fund, pd.DataFrame([rec])], ignore_index=True)
            save_df(PATH_FUND, fund)
            st.success("기록 완료")
        st.markdown("### 장부")
        st.dataframe(fund.sort_values("ts", ascending=False), use_container_width=True)
        st.download_button("장부 CSV 다운로드", fund.to_csv(index=False).encode("utf-8-sig"), "fund_ledger.csv", "text/csv")

    with c2:
        st.markdown("### 핵심 지표")
        total_in  = pd.to_numeric(fund.loc[fund["type"]=="in","amount"], errors="coerce").fillna(0).sum()
        total_out = pd.to_numeric(fund.loc[fund["type"]=="out","amount"], errors="coerce").fillna(0).sum()
        balance = int(total_in - total_out)
        at_df = seniors.copy()
        at_df["last_visit_date"] = at_df["last_visit_date"].apply(clean_date)
        at_df["days_from_last"] = at_df["last_visit_date"].apply(lambda d: (date.today()-d).days if isinstance(d, date) else 10**9)
        at_risk = int((at_df["days_from_last"]>=7).sum())

        m = st.columns(4)
        m[0].metric("어르신 수", len(seniors))
        m[1].metric("경보(7일↑) 대상", at_risk)
        m[2].metric("방문 기록(총)", len(visits))
        m[3].metric("돌봄기금 잔액(₩)", balance)

        try:
            if len(fund):
                fdf = fund.copy(); fdf["ts"] = pd.to_datetime(fdf["ts"]).dt.date
                st.bar_chart(fdf.groupby("ts")["amount"].sum())
            if len(visits):
                vdf = visits.copy(); vdf["ts"] = pd.to_datetime(vdf["ts"]).dt.date
                st.bar_chart(vdf.groupby("ts")["name"].count())
        except Exception:
            st.caption("차트 표시를 건너뜁니다.")
