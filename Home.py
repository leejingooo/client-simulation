import streamlit as st
import subprocess

st.set_page_config(
    page_title="Client-Simulation Home",
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
    """Returns `True` if the user's name is in the list of participants."""

    def name_entered():
        """Checks whether the entered name is in the list of participants."""
        if st.session_state["name"] in st.secrets["participant"]:
            st.session_state["name_correct"] = True
        else:
            st.session_state["name_correct"] = False

    if "name" not in st.session_state or "name_correct" not in st.session_state:
        # First run, show input for name.
        st.text_input(
            "이름을 입력하세요 (한글)", on_change=name_entered, key="name"
        )
        return False
    elif not st.session_state["name_correct"]:
        # Name not in the list, show input + error.
        st.text_input(
            "이름을 입력하세요 (한글)", on_change=name_entered, key="name"
        )
        st.error("😕 등록되지 않은 이름입니다.")
        return False
    else:
        # Name is in the list.
        return True


def main():
    if check_participant():
        st.success(f"환영합니다, {st.session_state['name']}님!")
        st.title("Client-Simulation에 오신 것을 환영합니다")
        st.write("계속하려면 사이드바에서 페이지를 선택하세요.")

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
