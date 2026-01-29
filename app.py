import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 CSS ---
st.set_page_config(page_title="STUDIO MANAGER", page_icon="📸", layout="wide")

st.markdown("""
    <style>
    /* 상단 네이비 바 느낌 */
    header[data-testid="stHeader"] { background-color: #1e1e2f; }
    .stApp { background-color: #f8f9fa; }
    
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #eee; }
    
    /* 카드형 디자인 */
    .schedule-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .card-title { font-weight: bold; color: #333; font-size: 1.1em; margin-bottom: 10px; }
    .card-content { color: #666; font-size: 0.9em; }
    
    /* 버튼 스타일 */
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연동 ---
def get_data(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sh = client.open("studio_db")
    worksheet = sh.worksheet(sheet_name)
    return worksheet, pd.DataFrame(worksheet.get_all_records())

# --- 3. 메인 로직 ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # 로그인 화면 (간략)
    st.title("📸 STUDIO MANAGER")
    user_id = st.text_input("아이디")
    user_pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        _, df = get_data("users")
        user = df[(df['id'] == user_id) & (df['password'].astype(str) == user_pw)]
        if not user.empty:
            st.session_state['logged_in'] = True
            st.session_state['name'] = user.iloc[0]['name']
            st.rerun()
else:
    # --- 상단 바 (React 느낌) ---
    t1, t2, t3 = st.columns([2, 5, 2])
    with t1: st.subheader("📸 STUDIO MANAGER")
    with t3: st.write(f"**{st.session_state['name']} 님** | 관리자")

    st.divider()

    # --- 메인 레이아웃 (좌측 달력 / 우측 스케줄) ---
    col_left, col_right = st.columns([1, 3])

    with col_left:
        st.write("### 📅 1월 달력")
        selected_date = st.date_input("날짜 선택", datetime.now(), label_visibility="collapsed")
        st.info(f"선택됨: {selected_date.strftime('%m월 %d일')}")
        if st.button("+ 일정 등록", use_container_width=True):
            st.toast("일정 등록 메뉴로 이동하세요!")

    with col_right:
        st.write(f"### {selected_date.strftime('%m월 %d일')} 스케줄")
        
        _, df_s = get_data("schedules")
        daily = df_s[df_s['date'] == selected_date.strftime("%Y-%m-%d")]

        # 카테고리별 섹션 (React 디자인 이식)
        for cat in ["리허설", "본식", "일반", "셀렉"]:
            with st.container():
                st.markdown(f"<div class='card-title'>{cat} 촬영</div>", unsafe_allow_html=True)
                items = daily[daily['type'] == cat]
                if items.empty:
                    st.markdown(f"<div class='schedule-card'><p style='color:#ccc; text-align:center;'>등록된 {cat} 일정이 없습니다.</p></div>", unsafe_allow_html=True)
                else:
                    for _, row in items.iterrows():
                        st.markdown(f"""
                            <div class='schedule-card'>
                                <div class='card-title'>{row['time']} | {row['groom_name']} ❤️ {row['bride_name']}</div>
                                <div class='card-content'>📍 {row['venue']} | 👤 {row['manager']} | 📞 {row['phone']}</div>
                            </div>
                        """, unsafe_allow_html=True)
