import streamlit as st
import subprocess

st.set_page_config(
    page_title="Client-Simulation Home",
    page_icon="🔥",
)

# Playwright 설치 및 모든 브라우저 다운로드


@st.cache_resource
def setup_playwright():
    try:
        # 모든 브라우저 설치
        subprocess.run(["playwright", "install"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to install Playwright browsers. Error: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during Playwright setup: {e}")
        return False


def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True


def main():
    if check_password():
        st.success("You are logged in!")
        st.title("Welcome to the Client-Simulation")
        st.write("Please select a page from the sidebar to continue.")

        # Playwright 설정 실행
        with st.spinner("Setting up Playwright..."):
            if setup_playwright():
                st.success(
                    "Playwright setup completed successfully. All browsers installed.")
            else:
                st.warning(
                    "Playwright setup failed. Some features may not work correctly.")
    else:
        st.stop()


if __name__ == "__main__":
    main()
