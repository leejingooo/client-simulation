import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import json


def initialize_firebase():
    if not firebase_admin._apps:
        try:
            firebase_config = st.secrets["firebase"]
            if isinstance(firebase_config, str):
                firebase_config = json.loads(firebase_config)

            if not isinstance(firebase_config, dict):
                raise ValueError("Firebase config must be a dictionary")

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
            st.success("Firebase app initialized successfully")
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {str(e)}")
            st.error(
                "Please check your Firebase configuration in Streamlit secrets.")
            return None

    try:
        ref = db.reference()
        st.success("Database reference obtained successfully")
        return ref
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
