import streamlit as st
import subprocess

st.set_page_config(
    page_title="검증 시스템",
    page_icon="🔥",
)


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
    def name_entered():
        if st.session_state["name_input"] in st.secrets["participant"]:
            st.session_state["name"] = st.session_state["name_input"]
            st.session_state["name_correct"] = True
        else:
            st.session_state["name_correct"] = False

    if "name" not in st.session_state or not st.session_state.get("name_correct", False):
        # st.text_input(
        #     """"테스트" 라고 입력하세요 (쌍따옴표 제외). Please type "test" (without quotation marks)""", on_change=name_entered, key="name_input"
        # )
        st.text_input(
            "로그인 (성함을 입력해주세요)", on_change=name_entered, key="name_input"
        )
        if "name_correct" in st.session_state and not st.session_state["name_correct"]:
            st.error("😕 등록되지 않은 이름입니다.")
        return False
    else:
        return True


def main():
    if check_participant():
        st.success(f"환영합니다, {st.session_state['name']}님!")
        st.title("연구에 참여해주셔서 감사합니다!")
        st.write("가상면담가와 가상환자에 대한 검증을 수행해주십시오. 사이드바에서 각 검증 페이지로 이동할 수 있습니다.")

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
