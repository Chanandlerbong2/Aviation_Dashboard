import streamlit as st
import pandas as pd
import numpy as np
import joblib
import re

# ---------------- Load trained model & encoders ----------------
@st.cache_resource
def load_artifacts():
    clf = joblib.load("model.pkl")
    tf = joblib.load("tfidf.pkl")
    le = joblib.load("labelencoder.pkl")
    return clf, tf, le

clf, tf, le = load_artifacts()

# ---------------- Text cleaning ----------------
STOPWORDS = {'the','and','a','an','in','on','at','of','to','for','with','from','by','is','was','were','has','had','that','this','it','as','be','are','or','but'}
def clean_text_simple(s):
    if pd.isna(s): return ""
    s = str(s).lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    tokens = s.split()
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return " ".join(tokens)

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="AI-Based Aviation Safety Dashboard", layout="wide")
st.title("✈️ AI-Based Aviation Accident Cause Prediction System")

st.markdown("""
Upload a **flight incident summary** to predict the likely cause and get recommendations
based on historical aviation safety data.
""")

# Input text box
summary_input = st.text_area("✍️ Enter or paste the flight incident summary:", height=200)

if st.button("Predict Cause"):
    if summary_input.strip() == "":
        st.warning("Please enter a valid summary.")
    else:
        cleaned = clean_text_simple(summary_input)
        X_text = tf.transform([cleaned]).toarray()
        pred = clf.predict(X_text)[0]
        cause = le.inverse_transform([pred])[0]
        proba = clf.predict_proba(X_text)[0]
        confidence = np.max(proba) * 100 if hasattr(clf, "predict_proba") else None

        if confidence:
            st.metric("Predicted Cause", cause, f"{confidence:.1f}% confidence")
        else:
            st.metric("Predicted Cause", cause)

        rec_map = {
            'Pilot Error': ['Crew re-training', 'Fatigue monitoring'],
            'Mechanical Failure': ['Immediate part inspection', 'Maintenance schedule review'],
            'Weather': ['Improved forecasting', 'Route planning adjustments'],
            'Security Issue': ['Security protocol review', 'Background checks'],
            'Other/Unknown': ['Detailed investigation required']
        }

        st.subheader("🛠 Recommendations")
        for rec in rec_map.get(cause, ["No recommendations available"]):
            st.write("- " + rec)
