import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(st.secrets["firebase"])
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["firebase_database_url"]
            })
        return db.reference()
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        st.error(f"Failed to initialize Firebase: {e}")
        return None


def get_firebase_ref():
    ref = initialize_firebase()
    if ref is None:
        st.error(
            "Failed to get Firebase reference. Check your configuration and network connection.")
    return ref


def test_firebase_connection():
    ref = get_firebase_ref()
    if ref:
        try:
            # 테스트 데이터 쓰기
            ref.child("test").set({"connection": "successful"})
            # 테스트 데이터 읽기
            test_data = ref.child("test").get()
            if test_data and test_data.get("connection") == "successful":
                st.success("Firebase connection test successful!")
            else:
                st.warning("Firebase connection test failed: Unexpected data")
        except Exception as e:
            st.error(f"Firebase connection test failed: {e}")
    else:
        st.error("Firebase connection test failed: Could not get reference")
