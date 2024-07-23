import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import json


def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Streamlit Secrets에서 Firebase 설정을 가져옵니다
            firebase_config = st.secrets["firebase"]

            # 문자열로 저장된 경우 JSON으로 파싱합니다
            if isinstance(firebase_config, str):
                firebase_config = json.loads(firebase_config)

            # 딕셔너리가 아니라면 오류를 발생시킵니다
            if not isinstance(firebase_config, dict):
                raise ValueError("Firebase config must be a dictionary")

            # 필수 키가 모두 있는지 확인합니다
            required_keys = ['type', 'project_id',
                             'private_key_id', 'private_key', 'client_email']
            for key in required_keys:
                if key not in firebase_config:
                    raise ValueError(
                        f"Missing required key in Firebase config: {key}")

            # 인증 정보를 사용하여 Firebase 앱을 초기화합니다
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["firebase_database_url"]
            })
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {e}")
            # Be careful not to expose sensitive information
            st.error(f"Firebase config: {firebase_config}")
            return None

    try:
        return db.reference()
    except Exception as e:
        st.error(f"Failed to get database reference: {e}")
        return None


def get_firebase_ref():
    return initialize_firebase()
