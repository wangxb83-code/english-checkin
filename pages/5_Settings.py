import streamlit as st
from src.settings import get_setting, set_setting

st.title("Settings")

current_n = int(get_setting("daily_n") or "15")
daily_n = st.slider("Daily target N (每天卡片数)", min_value=10, max_value=30, value=max(10, min(30, current_n)))
seed = st.text_input("Seed (固定随机种子)", value=get_setting("seed") or "42")

if st.button("Save"):
    set_setting("daily_n", str(daily_n))
    set_setting("seed", seed.strip() or "42")
    st.success("Saved.")
