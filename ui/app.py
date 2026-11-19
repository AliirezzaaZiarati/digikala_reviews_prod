import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

# Direct image URL pattern; only the numeric status code changes
ERROR_IMAGE_URL = "https://httpstatusdogs.com/img/picture-perfect/{code}.jpg"

st.set_page_config(page_title="Digikala Review Analyzer", layout="centered")
st.title("Digikala Review Analyzer")


def show_error(resp: requests.Response):
    st.error(f"Error {resp.status_code}: {resp.text}")
    st.image(ERROR_IMAGE_URL.format(code=resp.status_code), width=400)

try:
    models = requests.get(f"{API_URL}/models", timeout=5).json()
except requests.RequestException:
    st.error("API is not reachable. Is the FastAPI service running?")
    st.stop()

names = {m["name"]: m["id"] for m in models}
choice = st.selectbox("Model", list(names))
text = st.text_area("Review text", height=150)

if st.button("Predict"):
    if not text.strip():
        st.warning("Please enter a review text first.")
        st.stop()
    resp = requests.post(
        f"{API_URL}/predict",
        json={"text": text, "model_id": names[choice]},
        timeout=120,
    )
    if resp.status_code != 200:
        show_error(resp)
    else:
        data = resp.json()
        st.caption(f"{data['model_name']} | {data['latency_ms']} ms")
        for head in ("recommendation", "rating_band"):
            st.subheader(f"{head}: {data[head]['label']}")
            st.bar_chart(data[head]["probabilities"])