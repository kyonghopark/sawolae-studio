import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. 구글 시트 연동 설정 ---
def get_connection():
    # Streamlit Secrets에서 인증 정보 가져오기
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# 시트와 데이터 가져오기 (없으면 생성)
def get_data():
    client = get_connection()
    try:
        # 시트 이름은 편한대로 설정 (여기서는 'studio_db'로 함)
        sheet = client.open("studio_db").sheet1
    except:
        st.error("구글 드라이브에 'studio_db'라는 이름의 빈 스프레드시트를 먼저 만들어주세요!")
        st.stop()
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return sheet, df

# --- 2. 로그인 & 회원가입 화면 ---
def login_page():
    st.title("📸 스튜디오 스케줄 관리 (로그인)")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    # [로그인 탭]
    with tab1:
        login_id = st.text_input("아이디", key="login_id")
        login_pw = st.text_input("비밀번호", type="password", key="login_pw")
        
        if st.button("로그인"):
            sheet, df = get_data()
            if df.empty:
                st.error("등록된 사용자가 없습니다.")
            else:
                user = df[df['id'] == login_id]
                if not user.empty:
                    if str(user.iloc[0]['password']) == login_pw:
                        if user.iloc[0]['approved'] == "TRUE": # 승인된 사용자만
                            st.session_state['logged_in'] = True
                            st.session_state['user_id'] = login_id
                            st.session_state['role'] = user.iloc[0]['role']
                            st.session_state['name'] = user.iloc[0]['name']
                            st.rerun()
                        else:
                            st.warning("아직 관리자 승인 대기 중입니다.")
                    else:
                        st.error("비밀번호가 틀렸습니다.")
                else:
                    st.error("존재하지 않는 아이디입니다.")

    # [회원가입 탭]
    with tab2:
        new_id = st.text_input("사용할 아이디")
        new_pw = st.text_input("사용할 비밀번호", type="password")
        new_name = st.text_input("이름 (실명)")
        # 직무 선택 (신청만 가능, 권한은 마스터가 줌)
        job_role = st.selectbox("직무 선택", ["촬영", "편집", "상담", "기타"])
        
        if st.button("가입 신청"):
            if new_id and new_pw and new_name:
                sheet, df = get_data()
                
                # 아이디 중복 확인
                if not df.empty and new_id in df['id'].values:
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    # 구글 시트에 데이터 추가 (승인 상태는 FALSE로 시작)
                    # 컬럼 순서: id, password, name, role, approved, signup_date
                    new_row = [new_id, new_pw, new_name, job_role, "FALSE", str(datetime.now())]
                    sheet.append_row(new_row)
                    st.success(f"{new_name}님 가입 신청 완료! 관리자 승인을 기다려주세요.")
            else:
                st.warning("모든 정보를 입력해주세요.")

# --- 3. 메인 앱 화면 ---
def main_app():
    st.sidebar.write(f"환영합니다, **{st.session_state['name']}**님")
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    # --- 관리자(Master) 전용 메뉴 ---
    if st.session_state['role'] == "Master":
        st.subheader("👑 관리자 페이지")
        
        # [사용자 승인 관리]
        st.write("### 👥 회원 승인 관리")
        sheet, df = get_data()
        
        # 데이터프레임 보여주기 (수정 가능하게)
        edited_df = st.data_editor(
            df[['id', 'name', 'role', 'approved', 'signup_date']],
            key="user_editor",
            num_rows="dynamic",
            disabled=["id", "signup_date"] # 아이디랑 날짜는 수정 불가
        )

        if st.button("변경사항 저장 (승인 처리)"):
            # 변경된 내용을 구글 시트에 업데이트하는 로직 (간단하게 구현)
            # 실제로는 전체 데이터를 덮어씌우거나, 변경된 셀만 찾아서 업데이트해야 함
            # 여기서는 편의상 헤더 포함 전체 업데이트 방식 사용
            
            # 원본 데이터(비밀번호 포함) 보존하면서 업데이트 필요
            # (이 부분은 코드가 길어지므로, 실제 운영 시에는 '비밀번호' 컬럼이 날아가지 않게 주의해야 해.
            # 지금은 로직 흐름만 보여주는 거라, 시트의 모든 데이터를 다시 씁니다.)
            
            # 기존 비밀번호 유지를 위해 병합
            final_df = df.copy()
            final_df.update(edited_df) # 수정된 내용(승인여부 등) 반영
            
            # 시트 클리어 후 재작성
            sheet.clear()
            # 헤더 다시 쓰기 (id, password, name, role, approved, signup_date)
            sheet.append_row(['id', 'password', 'name', 'role', 'approved', 'signup_date'])
            # 데이터 쓰기
            sheet.append_rows(final_df.values.tolist())
            st.success("회원 정보가 업데이트 되었습니다!")

    # --- 일반 직원 메뉴 ---
    st.divider()
    st.subheader("📅 스튜디오 스케줄")
    st.info("여기에 나중에 캘린더나 스케줄 표가 들어갈 자리야.")

# --- 앱 실행 흐름 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_page()
else:
    main_app()
