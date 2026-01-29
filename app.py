import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import json
import random

# --- 1. 페이지 설정 및 디자인 CSS ---
st.set_page_config(page_title="STUDIO MANAGER", page_icon="📷", layout="wide")

st.markdown("""
    <style>
    /* 상단 네이비 바 느낌 */
    header[data-testid="stHeader"] { background-color: #1e2e3f; }
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

# --- 2. 구글 시트 연동 로직 ---
# Streamlit Secrets에 저장된 정보를 사용한다고 가정합니다.
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # .streamlit/secrets.toml 에 저장된 credentials 사용
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"구글 시트 인증 에러: {e}")
        return None

def load_data(sheet_name):
    client = get_gspread_client()
    if client:
        try:
            sh = client.open("studio_db") # 사진 2번에 있는 시트 이름
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data), worksheet
        except Exception as e:
            # 시트가 비어있을 경우 기본 컬럼 생성
            if sheet_name == "schedules":
                cols = ["id", "date", "type", "time", "groomName", "groomPhone", "brideName", "bridePhone", "venue", "product", "price", "paymentStatus", "selectionDate", "selectionTime", "memoList"]
                return pd.DataFrame(columns=cols), None
            return pd.DataFrame(), None
    return pd.DataFrame(), None

# --- 3. 데이터 업데이트 함수 ---
def save_to_sheet(sheet_name, df):
    client = get_gspread_client()
    if client:
        sh = client.open("studio_db")
        worksheet = sh.worksheet(sheet_name)
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- 4. 세션 상태 초기화 ---
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- 5. 로그인 화면 ---
if st.session_state.current_user is None:
    st.title("STUDIO MANAGER")
    with st.form("login_form"):
        st.subheader("로그인")
        u_id = st.text_input("아이디")
        u_pw = st.text_input("비밀번호", type="password")
        if st.form_submit_button("로그인"):
            df_u, _ = load_data("users")
            user = df_u[(df_u['id'] == u_id) & (df_u['password'].astype(str) == u_pw)]
            if not user.empty:
                st.session_state.current_user = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")
    st.stop()

# --- 6. 메인 네비게이션 ---
user = st.session_state.current_user

with st.sidebar:
    st.markdown(f"### 👤 {user['name']} 님")
    st.caption(f"권한: {user['role']}")
    if st.button("로그아웃"):
        st.session_state.current_user = None
        st.rerun()
    
    st.divider()
    menu = st.radio("메뉴", ["📅 일정 관리", "👥 고객 관리", "⚙️ 사용자 관리"])

# 데이터 로드
df_s, ws_s = load_data("schedules")

# --- 7. 기능 구현 ---

# 시간 선택 옵션 (10분 단위)
HOURS = [f"{h:02d}" for h in range(8, 22)]
MINUTES = [f"{m:02d}" for m in range(0, 60, 10)]

if menu == "📅 일정 관리":
    col_cal, col_list = st.columns([1, 2.5])
    
    with col_cal:
        st.subheader("📅 날짜 선택")
        selected_date = st.date_input("날짜", value=date(2026, 1, 29))
        date_str = selected_date.strftime("%Y-%m-%d")
        
        st.divider()
        if st.button("➕ 새 일정 등록", use_container_width=True):
            st.session_state.editing_id = "NEW"

    with col_list:
        st.header(f"{selected_date.strftime('%m월 %d일')} 스케줄")
        
        # 에러 방지용: date 컬럼이 있는지 확인
        if 'date' in df_s.columns:
            daily_data = df_s[df_s['date'] == date_str]
        else:
            daily_data = pd.DataFrame()

        if daily_data.empty:
            st.info("해당 날짜에 등록된 일정이 없습니다.")
        else:
            for _, item in daily_data.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 4, 1])
                    c1.subheader(item['time'])
                    c2.markdown(f"**{item['groomName']} / {item['brideName']}**")
                    c2.caption(f"{item['product']} | {item['venue']}")
                    if c3.button("보기", key=f"edit_{item['id']}"):
                        st.session_state.editing_id = item['id']
                        st.rerun()

# --- 8. 상세 정보 대화창 (Streamlit Dialog 스타일 시뮬레이션) ---
if 'editing_id' in st.session_state and st.session_state.editing_id:
    eid = st.session_state.editing_id
    
    if eid == "NEW":
        item = {"id": random.randint(1000, 9999), "date": date_str, "type": "rehearsal", "time": "10:00", "groomName": "", "groomPhone": "", "brideName": "", "bridePhone": "", "venue": "", "product": "", "price": 0, "paymentStatus": "미정산", "selectionDate": "", "selectionTime": "14:00", "memoList": "[]"}
    else:
        item = df_s[df_s['id'] == eid].iloc[0].to_dict()

    st.divider()
    st.subheader(f"📝 일정 상세 정보 ({'신규' if eid == 'NEW' else eid})")
    
    with st.form("detail_form"):
        # 시간 선택 (10분 단위)
        curr_h, curr_m = item['time'].split(':')
        t_c1, t_c2 = st.columns(2)
        new_h = t_c1.selectbox("시", HOURS, index=HOURS.index(curr_h))
        new_m = t_c2.selectbox("분", MINUTES, index=MINUTES.index(curr_m))
        
        # 고객 정보
        g_c1, g_c2 = st.columns(2)
        u_groom = g_c1.text_input("신랑님 성함", value=item['groomName'])
        u_groom_p = g_c2.text_input("신랑님 연락처", value=item['groomPhone'])
        
        b_c1, b_c2 = st.columns(2)
        u_bride = b_c1.text_input("신부님 성함", value=item['brideName'])
        u_bride_p = b_c2.text_input("신부님 연락처", value=item['bridePhone'])
        
        u_venue = st.text_input("장소", value=item['venue'])
        u_product = st.text_input("상품명", value=item['product'])
        
        # 매출 (권한 확인)
        if user['role'] == 'Master':
            p_c1, p_c2 = st.columns(2)
            u_price = p_c1.number_input("공급가", value=int(item['price']))
            u_status = p_c2.selectbox("정산 상태", ["미정산", "정산완료"], index=0 if item['paymentStatus'] == "미정산" else 1)
        else:
            st.warning("💰 매출 정보: 권한이 없습니다.")
            u_price, u_status = item['price'], item['paymentStatus']

        # 셀렉 일정
        st.markdown("---")
        st.markdown("**📸 셀렉 예약**")
        s_c1, s_c2 = st.columns(2)
        u_sel_date = s_c1.text_input("셀렉 날짜 (YYYY-MM-DD)", value=item['selectionDate'])
        u_sel_time = s_c2.text_input("셀렉 시간", value=item['selectionTime'])

        submit = st.form_submit_button("저장하기")
        if submit:
            new_item = item.copy()
            new_item.update({
                "time": f"{new_h}:{new_m}", "groomName": u_groom, "groomPhone": u_groom_p,
                "brideName": u_bride, "bridePhone": u_bride_p, "venue": u_venue,
                "product": u_product, "price": u_price, "paymentStatus": u_status,
                "selectionDate": u_sel_date, "selectionTime": u_sel_time
            })
            
            if eid == "NEW":
                df_s = pd.concat([df_s, pd.DataFrame([new_item])], ignore_index=True)
            else:
                df_s.loc[df_s['id'] == eid] = new_item.values()
            
            save_to_sheet("schedules", df_s)
            st.session_state.editing_id = None
            st.success("저장되었습니다!")
            st.rerun()

    # 메모 히스토리
    st.markdown("---")
    st.subheader("💬 상담 메모 히스토리")
    memos = json.loads(item['memoList']) if isinstance(item['memoList'], str) else []
    
    for idx, m in enumerate(memos):
        with st.chat_message("user"):
            st.write(f"**{m['date']} | {m['writer']}**")
            st.write(m['content'])

    with st.expander("📝 새 메모 등록"):
        m_content = st.text_area("내용")
        if st.button("메모 추가"):
            new_m = {"id": len(memos)+1, "date": datetime.now().strftime("%Y-%m-%d"), "writer": user['name'], "content": m_content}
            memos.insert(0, new_m)
            df_s.loc[df_s['id'] == eid, 'memoList'] = json.dumps(memos, ensure_ascii=False)
            save_to_sheet("schedules", df_s)
            st.rerun()

    if st.button("❌ 닫기"):
        st.session_state.editing_id = None
        st.rerun()

elif menu == "👥 고객 관리":
    st.header("👥 전체 고객 명단")
    search_q = st.text_input("이름 또는 연락처 뒷자리 검색")
    if search_q:
        search_results = df_s[df_s['groomName'].str.contains(search_q) | df_s['brideName'].str.contains(search_q) | df_s['groomPhone'].str.contains(search_q)]
        st.dataframe(search_results, use_container_width=True)
    else:
        st.dataframe(df_s, use_container_width=True)

elif menu == "⚙️ 사용자 관리":
    st.header("⚙️ 직원 및 외주 관리")
    df_u, _ = load_data("users")
    st.table(df_u[["id", "name", "role"]])
    # 추가/수정 로직은 일정 관리와 동일하게 구현 가능
