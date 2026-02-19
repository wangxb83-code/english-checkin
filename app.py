
### 3) `app.py`

import streamlit as st
from src.db import init_db

st.set_page_config(page_title="English Check-in", layout="wide")
init_db()

st.title("English Check-in")
st.write("Use the left sidebar to navigate: Upload / Today / Stats / Library / Settings.")
