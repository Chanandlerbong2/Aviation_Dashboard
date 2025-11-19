# ==========================================================
#   Pre-Flight Safety Dashboard — Premium Dark UI (Option C)
#   100% Streamlit Cloud–Safe + Professional Bluebook Style
# ==========================================================

import streamlit as st
import pandas as pd
import numpy as np
import joblib, os, re
import plotly.express as px
from datetime import datetime

# ----------- PAGE CONFIG -----------
st.set_page_config(
    page_title="AI Pre-Flight Safety",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------- SAFE DARK THEME CSS -----------
st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

:root {
    --bg-color: #0f172a;
    --card-bg: #1e293b;
    --accent: #38bdf8;
    --text-light: #e2e8f0;
    --text-dim: #94a3b8;
    --shadow: rgba(0,0,0,0.45);
}

/* Gradient header */
.header-box {
    background: linear-gradient(90deg, #1e293b 0%, #075985 100%);
    padding: 26px;
    border-radius: 16px;
    box-shadow: 0 6px 18px var(--shadow);
    margin-bottom: 20px;
}

/* Flight card styling */
.flight-card {
    background: var(--card-bg);
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 0 25px rgba(0,0,0,0.25);
    transition: 0.25s;
    border: 1px solid rgba(255,255,255,0.05);
}

.flight-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 0 35px rgba(0,0,0,0.5);
    border-color: rgba(255,255,255,0.25);
}

/* Risk badges */
.badge {
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    color: white;
}
.badge-low { background: #10b981; }
.badge-med { background: #f59e0b; }
.badge-high { background: #ef4444; }

</style>
""", unsafe_allow_html=True)


# ----------- SMALL UTILS -----------
def risk_label(score):
    if score >= 65: return "High", "badge-high"
    if score >= 35: return "Medium", "badge-med"
    return "Low", "badge-low"


# ----------- HEADER -----------
st.markdown(f"""
<div class="header-box">
    <h1 style="color:white; margin:0;">✈️ AI-Assisted Pre-Flight Safety Dashboard</h1>
    <p style="color:#cbd5e1; margin:0;">
        Modern aviation diagnostic panel • Upload → View Cards → Click for Deep Analysis
    </p>
</div>
""", unsafe_allow_html=True)


# ----------- SIDEBAR -----------
with st.sidebar:
    st.header("Upload Flight Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    st.markdown("---")
    st.subheader("Hybrid Scoring Weight")
    rule_w = st.slider("Rule Weight", 0.0, 1.0, 0.6, 0.1)

    st.markdown("---")
    if st.button("Generate Sample CSV"):
        sample = pd.DataFrame([
            {"Flight_No":"AI101","AC_Type":"A320","Pilot_Experience_Hours":3500,
             "Pilot_Hours_Last_7_Days":40,"Last_Maintenance_Days_Ago":30,
             "Weather":"Clear","Engine_Vibration_mm_s":1.2,"Fuel_Imbalance_pct":1.0},
            
            {"Flight_No":"AI202","AC_Type":"B737","Pilot_Experience_Hours":250,
             "Pilot_Hours_Last_7_Days":60,"Last_Maintenance_Days_Ago":180,
             "Weather":"Thunderstorm","Engine_Vibration_mm_s":3.2,"Fuel_Imbalance_pct":7.0},

            {"Flight_No":"AI330","AC_Type":"A330","Pilot_Experience_Hours":900,
             "Pilot_Hours_Last_7_Days":52,"Last_Maintenance_Days_Ago":120,
             "Weather":"Rain","Engine_Vibration_mm_s":2.5,"Fuel_Imbalance_pct":0.5},
        ])
        sample.to_csv("demo_flights.csv", index=False)
        st.success("Sample CSV saved as demo_flights.csv → Download and upload!")
    st.markdown("---")


# ----------- IF NO DATA -----------
if uploaded is None:
    st.info("Upload a CSV file to display flight cards.")
    st.stop()


# ----------- LOAD CSV -----------
df = pd.read_csv(uploaded)

# Compute rule score (simplified)
def compute_rule(row):
    sc = 0
    if row.get("Pilot_Hours_Last_7_Days",0) > 55: sc += 25
    if row.get("Pilot_Experience_Hours",0) < 300: sc += 20
    if row.get("Last_Maintenance_Days_Ago",0) > 150: sc += 30
    if row.get("Engine_Vibration_mm_s",0) > 3: sc += 15
    if row.get("Fuel_Imbalance_pct",0) > 6: sc += 10
    return min(sc, 100)

df["Rule_Score"] = df.apply(compute_rule, axis=1)
df["Hybrid_Score"] = (rule_w * df["Rule_Score"])
df["Hybrid_Score"] = df["Hybrid_Score"].round(1)

# ----------- CARD GRID DISPLAY -----------
st.subheader("📋 Flight Overview — Click Any Card")

cols = st.columns(3)

selected_flight = None

for idx, row in df.iterrows():
    col = cols[idx % 3]
    risk, badge_class = risk_label(row["Hybrid_Score"])

    with col:
        if st.button(
            f"🛫 {row['Flight_No']}",
            key=f"btn_{idx}",
            help="Click to open detailed view"
        ):
            selected_flight = row

        st.markdown(f"""
        <div class="flight-card">
            <h3 style="color:white; margin-bottom:6px;">{row['Flight_No']}</h3>
            <p style="color:#cbd5e1; margin:0;">Aircraft: {row['AC_Type']}</p>
            <p style="color:#cbd5e1; margin:0;">
    Pilot Exp: {row['Pilot_Hours_Total']} hrs (Last 30d: {row['Pilot_Hours_Last30']} hrs)
</p>

            <p style="color:#cbd5e1; margin:0;">Maint: {row['Last_Maintenance_Days_Ago']} days ago</p>

            <p style="margin-top:10px;">
                <span class="badge {badge_class}">{risk}: {row['Hybrid_Score']}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)


# ----------- DETAIL PANEL -----------
if selected_flight is not None:
    st.markdown("---")
    st.subheader(f"🔍 Detailed Diagnostics — {selected_flight['Flight_No']}")

    c1, c2 = st.columns([1.2,1])

    with c1:
        st.write("### Key Parameters")
        st.json(selected_flight.to_dict())

    with c2:
        st.write("### Risk Breakdown")
        fig = px.bar(
            x=["Hybrid Score", "Rule Score"],
            y=[selected_flight["Hybrid_Score"], selected_flight["Rule_Score"]],
            color=["Hybrid Score", "Rule Score"],
            labels={"x": "Score Type", "y": "Score"},
            title="Score Breakdown",
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
