import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- 1. 페이지 설정 (앱 이름과 아이콘) ---
st.set_page_config(page_title="스튜디오 매니저", page_icon="📸", layout="wide")

# --- 2. 구글 시트 연동 함수 ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def get_data(sheet_name):
    client = get_client()
    try:
        sh = client.open("studio_db")
        worksheet = sh.worksheet(sheet_name)
    except:
        # 시트가 없으면 생성 시도 (첫 실행 대비)
        sh = client.open("studio_db")
        worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")
    
    data = worksheet.get_all_records()
    return worksheet, pd.DataFrame(data)

# --- 3. 로그인 및 회원가입 화면 ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>📸 STUDIO MANAGER</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>스튜디오 통합 관리 시스템 (Python Ver)</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 로그인", "📝 회원가입"])

    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_id = st.text_input("아이디", key="login_id")
            login_pw = st.text_input("비밀번호", type="password", key="login_pw")
            
            if st.button("로그인 시작", use_container_width=True):
                try:
                    sheet, df = get_data("users")
                    if df.empty:
                        st.error("등록된 사용자가 없습니다.")
                    else:
                        user = df[df['id'] == login_id]
                        if not user.empty:
                            if str(user.iloc[0]['password']) == login_pw:
                                if str(user.iloc[0]['approved']).upper() == "TRUE":
                                    st.session_state['logged_in'] = True
                                    st.session_state['user_id'] = login_id
                                    st.session_state['role'] = user.iloc[0]['role']
                                    st.session_state['name'] = user.iloc[0]['name']
                                    st.rerun()
                                else:
                                    st.warning("🔒 관리자 승인 대기 중입니다.")
                            else:
                                st.error("비밀번호가 틀렸습니다.")
                        else:
                            st.error("존재하지 않는 아이디입니다.")
                except Exception as e:
                    st.error(f"로그인 오류: {e}")

    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            new_id = st.text_input("아이디 (이메일)", key="new_id")
            new_pw = st.text_input("비밀번호", type="password", key="new_pw")
            new_name = st.text_input("이름 (실명)", key="new_name")
            job_role = st.selectbox("직무 신청", ["촬영", "편집", "상담", "기타"], key="new_role")
            
            if st.button("가입 신청하기", use_container_width=True):
                if new_id and new_pw and new_name:
                    sheet, df = get_data("users")
                    # 헤더가 없으면 생성
                    if len(sheet.get_all_values()) == 0:
                        sheet.append_row(['id', 'password', 'name', 'role', 'approved', 'signup_date'])
                        df = pd.DataFrame(columns=['id', 'password', 'name', 'role', 'approved', 'signup_date'])
                    
                    if not df.empty and new_id in df['id'].values:
                        st.error("이미 존재하는 아이디입니다.")
                    else:
                        new_row = [new_id, new_pw, new_name, job_role, "FALSE", str(datetime.now())]
                        sheet.append_row(new_row)
                        st.success(f"✅ {new_name}님 가입 신청 완료! 관리자 승인을 기다려주세요.")
                else:
                    st.warning("모든 정보를 입력해주세요.")

# --- 4. 메인 앱 화면 ---
def main_app():
    # 사이드바 (네비게이션)
    with st.sidebar:
        st.title(f"반갑습니다, {st.session_state['name']}님")
        st.write(f"권한: **{st.session_state['role']}**")
        
        menu = st.radio("메뉴 이동", ["📅 일일 스케줄", "👥 전체 고객 리스트", "➕ 일정 등록", "⚙️ 관리자 페이지"])
        
        st.divider()
        if st.button("로그아웃"):
            st.session_state.clear()
            st.rerun()

    # 데이터 가져오기
    sheet, df_schedule = get_data("schedules")
    
    # 데이터가 비어있으면 헤더 생성
    if len(sheet.get_all_values()) == 0:
        headers = ['id', 'type', 'date', 'time', 'groom_name', 'bride_name', 'phone', 'venue', 'product', 'manager', 'status_usb', 'status_album', 'notes']
        sheet.append_row(headers)
        df_schedule = pd.DataFrame(columns=headers)

    # --- [탭 1] 일일 스케줄 (React의 CalendarView 기능) ---
    if menu == "📅 일일 스케줄":
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("날짜 선택")
            selected_date = st.date_input("확인할 날짜", datetime.now())
            str_date = selected_date.strftime("%Y-%m-%d")
        
        with col2:
            st.subheader(f"{str_date} 스케줄")
            
            # 해당 날짜 데이터 필터링
            if not df_schedule.empty:
                daily_data = df_schedule[df_schedule['date'] == str_date]
            else:
                daily_data = pd.DataFrame()
                
            if daily_data.empty:
                st.info("등록된 스케줄이 없습니다.")
            else:
                for idx, row in daily_data.iterrows():
                    # 색상 구분 (React 코드의 스타일 반영)
                    card_color = "blue" if row['type'] == "리허설" else "red" if row['type'] == "본식" else "green"
                    
                    with st.expander(f"[{row['time']}] {row['groom_name']} ❤️ {row['bride_name']} ({row['type']})"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**📞 연락처:** {row['phone']}")
                            st.write(f"**📍 장소:** {row['venue']}")
                            st.write(f"**📸 상품:** {row['product']}")
                        with c2:
                            st.write(f"**👤 담당:** {row['manager']}")
                            st.write(f"**📝 메모:** {row['notes']}")
                            st.write("---")
                            # 출고 상태 표시
                            if str(row['status_usb']) == "TRUE": st.success("💾 USB 출고완료")
                            if str(row['status_album']) == "TRUE": st.success("📒 앨범 출고완료")

    # --- [탭 2] 전체 고객 리스트 (검색 기능) ---
    elif menu == "👥 전체 고객 리스트":
        st.subheader("전체 고객 스케줄 조회")
        
        search_term = st.text_input("🔍 이름, 연락처 검색")
        
        if not df_schedule.empty:
            if search_term:
                # 검색 로직
                mask = df_schedule.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
                display_df = df_schedule[mask]
            else:
                display_df = df_schedule
                
            # 데이터프레임 표시 (보기 좋게 컬럼 선택)
            st.dataframe(
                display_df[['date', 'time', 'type', 'groom_name', 'bride_name', 'phone', 'venue', 'manager']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("데이터가 없습니다.")

    # --- [탭 3] 일정 등록 (React의 Modal Form 기능) ---
    elif menu == "➕ 일정 등록":
        st.subheader("새로운 스케줄 등록")
        
        with st.form("add_schedule_form"):
            col1, col2 = st.columns(2)
            with col1:
                sType = st.selectbox("구분", ["리허설", "본식", "일반촬영", "셀렉"])
                sDate = st.date_input("날짜")
                sTime = st.time_input("시간")
                sGroom = st.text_input("신랑님 이름")
                sBride = st.text_input("신부님 이름")
            
            with col2:
                sPhone = st.text_input("대표 연락처")
                sVenue = st.text_input("장소 (웨딩홀 등)")
                sProduct = st.text_input("계약 상품")
                sManager = st.text_input("담당자")
                sNotes = st.text_area("특이사항/메모")
                
            submit = st.form_submit_button("일정 등록하기")
            
            if submit:
                new_data = [
                    datetime.now().strftime("%Y%m%d%H%M%S"), # ID 생성
                    sType,
                    sDate.strftime("%Y-%m-%d"),
                    sTime.strftime("%H:%M"),
                    sGroom, sBride, sPhone, sVenue, sProduct, sManager,
                    "FALSE", "FALSE", # USB, 앨범 출고 상태 기본값
                    sNotes
                ]
                sheet.append_row(new_data)
                st.success("일정이 등록되었습니다!")
                st.rerun() # 새로고침

    # --- [탭 4] 관리자 페이지 (기존 기능 유지) ---
    elif menu == "⚙️ 관리자 페이지":
        if st.session_state['role'] == "Master":
            st.subheader("👑 직원 승인 및 권한 관리")
            user_sheet, user_df = get_data("users")
            
            edited_df = st.data_editor(
                user_df[['id', 'name', 'role', 'approved', 'signup_date']],
                key="user_editor",
                num_rows="dynamic",
                disabled=["id", "signup_date"]
            )
            
            if st.button("변경사항 저장 (승인 처리)"):
                # 전체 데이터를 다시 쓰는 방식 (간단 구현)
                user_sheet.clear()
                user_sheet.append_row(['id', 'password', 'name', 'role', 'approved', 'signup_date'])
                
                # 원본 데이터와 병합하여 비밀번호 유실 방지 로직 필요하나
                # 여기서는 편의상 Editor 내용을 우선시하여 덮어쓰기 (실무에선 주의)
                # (비밀번호 보존을 위해 기존 DF에서 password 컬럼을 가져와서 합쳐야 함)
                final_rows = []
                for i, row in edited_df.iterrows():
                    # 기존 비밀번호 찾기
                    orig_pw = user_df[user_df['id'] == row['id']]['password'].values[0] if not user_df.empty else ""
                    final_rows.append([row['id'], orig_pw, row['name'], row['role'], row['approved'], row['signup_date']])
                
                user_sheet.append_rows(final_rows)
                st.success("회원 정보가 업데이트 되었습니다!")
        else:
            st.error("관리자(Master) 권한이 필요한 페이지입니다.")

# --- 앱 실행 흐름 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_page()
else:
    main_app()
