import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import json


def initialize_firebase():
    if not firebase_admin._apps:
        try:

            if "firebase" not in st.secrets:
                raise ValueError(
                    "Firebase configuration not found in Streamlit secrets")

            firebase_config = st.secrets["firebase"]

            # Convert AttrDict to regular dictionary
            if hasattr(firebase_config, 'to_dict'):
                firebase_config = firebase_config.to_dict()
            elif isinstance(firebase_config, dict):
                pass
            elif isinstance(firebase_config, str):
                st.write(
                    "Firebase config is a string, attempting to parse as JSON")
                try:
                    firebase_config = json.loads(firebase_config)
                except json.JSONDecodeError as e:
                    st.error(
                        f"Failed to parse Firebase config as JSON: {str(e)}")
                    return None
            else:
                raise ValueError(
                    f"Firebase config must be a dictionary, but it is a {type(firebase_config)}")

            required_keys = ['type', 'project_id',
                             'private_key_id', 'private_key', 'client_email']
            for key in required_keys:
                if key not in firebase_config:
                    raise ValueError(
                        f"Missing required key in Firebase config: {key}")

            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["firebase_database_url"]
            })
            st.success("시스템 준비가 완료되었습니다.")
            return db.reference()
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {str(e)}")
            st.error(
                "Please check your Firebase configuration in Streamlit secrets.")
            return None
    else:
        try:
            return db.reference()
        except Exception as e:
            st.error(f"Failed to get database reference: {str(e)}")
            st.error(
                "Please check your Firebase Realtime Database settings and permissions.")
            return None


def get_firebase_ref():
    ref = initialize_firebase()
    if ref is None:
        st.error(
            "Firebase initialization failed. Check your configuration and try again.")
    return ref
