# Jeju SME Dual-Positioning Strategy App

## 실행
pip install streamlit pandas plotly python-dateutil
# (선택) 그래프비즈 사용 시: pip install graphviz  + 시스템 Graphviz 설치
streamlit run streamlit_app.py

## 기능
- 전략 맵 시각화(Graphviz 없으면 Sankey로 대체)
- 로드맵 CRUD/필터/CSV 저장
- 오퍼 연구소: 도민/관광객 맞춤 쿠폰 규칙 JSON 생성
