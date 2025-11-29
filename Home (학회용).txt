import streamlit as st
import subprocess
import uuid
from datetime import datetime, timedelta

# 세션 타임아웃 설정 (15분)
SESSION_TIMEOUT = 15 * 60  # seconds

st.set_page_config(
    page_title="Client-Simulation Home",
    page_icon="🔥",
)


def get_session_id():
    """세션 ID 생성 및 관리"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id


def check_session_timeout():
    """세션 타임아웃 체크 및 관리"""
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
        return True

    last_activity = st.session_state.last_activity
    if datetime.now() - last_activity > timedelta(seconds=SESSION_TIMEOUT):
        # 세션 만료 시 상태 초기화
        for key in ['name', 'name_correct', 'last_activity', 'session_id']:
            if key in st.session_state:
                del st.session_state[key]
        return False

    # 활동 시간 갱신
    st.session_state.last_activity = datetime.now()
    return True


@st.cache_resource
def setup_playwright():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to install Playwright browsers. Error: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during Playwright setup: {e}")
        return False


def check_participant():
    # 세션 타임아웃 체크
    if not check_session_timeout():
        st.warning("세션이 만료되었습니다. 다시 로그인해 주세요.")
        return False

    def name_entered():
        if st.session_state["name_input"] in st.secrets["participant"]:
            st.session_state["name"] = st.session_state["name_input"]
            st.session_state["name_correct"] = True
            st.session_state.last_activity = datetime.now()  # 로그인 성공 시 활동 시간 갱신
        else:
            st.session_state["name_correct"] = False

    if "name" not in st.session_state or not st.session_state.get("name_correct", False):
        st.text_input(
            """"테스트" 라고 입력하세요 (쌍따옴표 제외). Please type "test" (without quotation marks)""",
            on_change=name_entered,
            key="name_input"
        )
        if "name_correct" in st.session_state and not st.session_state["name_correct"]:
            st.error("😕 등록되지 않은 이름입니다.")
        return False
    else:
        return True


def show_session_info():
    """세션 정보 표시"""
    if 'last_activity' in st.session_state:
        time_elapsed = datetime.now() - st.session_state.last_activity
        remaining_time = max(0, SESSION_TIMEOUT - time_elapsed.seconds)
        minutes = remaining_time // 60
        seconds = remaining_time % 60

        # 세션 정보를 사이드바에 표시
        with st.sidebar:
            st.divider()
            st.write("### 세션 정보")
            st.info(f"세션 ID: {get_session_id()}")
            st.info(f"남은 시간: {minutes}분 {seconds}초")


def main():
    if check_participant():
        st.success(f"환영합니다, {st.session_state['name']}님!")
        st.title("Client-Simulation에 오신 것을 환영합니다")
        st.write("계속하려면 사이드바에서 페이지를 선택하세요.")

        # 세션 정보 표시
        show_session_info()

        # Playwright 설정 실행
        with st.spinner("Playwright 설정 중..."):
            if setup_playwright():
                st.success("Playwright 설정이 성공적으로 완료되었습니다. 모든 브라우저가 설치되었습니다.")
            else:
                st.warning("Playwright 설정에 실패했습니다. 일부 기능이 제대로 작동하지 않을 수 있습니다.")
    else:
        st.stop()


if __name__ == "__main__":
    main()
