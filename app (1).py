import streamlit as st
import pandas as pd
import numpy as np

# --------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------
st.set_page_config(page_title="AI Pre-Flight Safety Dashboard", layout="wide")

# --------------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------------
st.markdown("""
<style>
.card {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.25);
    margin-bottom: 18px;
    color: white;
}
.card h3 {
    margin: 0;
    font-size: 20px;
}
.card small {
    color: #94a3b8;
}
.expand-box {
    background: #f8fafc;
    padding: 16px;
    border-radius: 12px;
    margin-top: 10px;
    border: 1px solid #e2e8f0;
}
.kpi-box {
    background: white;
    padding: 14px;
    border-radius: 12px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.1);
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------
with st.sidebar:
    st.title("📂 Upload Flight Data")
    file = st.file_uploader("Upload CSV file", type="csv")

# --------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------
def compute_risk(row):
    score = 0

    # Pilot hours (fatigue)
    if row["Pilot_Hours_Last30"] > 55:
        score += 25
    elif row["Pilot_Hours_Last30"] > 45:
        score += 15

    # Weather impact
    w = str(row["Weather"]).lower()
    if "rain" in w:
        score += 15
    elif "cloud" in w:
        score += 8

    # Brake warning
    if str(row["Brake_Status"]).strip().upper() == "WARNING":
        score += 25

    # Fuel low
    if row["Fuel_Quantity"] < 7000:
        score += 15

    # Hydraulic pressure abnormal
    if row["Hydraulic_Pressure"] < 3000:
        score += 10

    return min(score, 100)

def risk_label(score):
    if score >= 60:
        return "High"
    elif score >= 30:
        return "Medium"
    return "Low"

# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
st.title("✈️ AI-Assisted Pre-Flight Safety Dashboard")
st.write("Upload flight data to view automated safety checks and detailed insights.")

if not file:
    st.info("Please upload a CSV file to continue.")
    st.stop()

# Load data
df = pd.read_csv(file)

# Compute risk
df["Risk_Score"] = df.apply(compute_risk, axis=1)
df["Risk_Level"] = df["Risk_Score"].apply(risk_label)

# --------------------------------------------------------
# KPI SECTION
# --------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='kpi-box'><h3>{len(df)}</h3><small>Total Flights</small></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-box'><h3>{(df['Risk_Level']=='High').sum()}</h3><small>High Risk</small></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-box'><h3>{(df['Risk_Level']=='Medium').sum()}</h3><small>Medium Risk</small></div>", unsafe_allow_html=True)

st.write("---")

# --------------------------------------------------------
# FLIGHT CARDS
# --------------------------------------------------------
st.subheader("🛫 Flight Overview")

for i, row in df.iterrows():

    with st.container():
        st.markdown(
            f"""
            <div class="card">
                <h3>{row['Flight_No']} • {row['AC_Type']}</h3>
                <small>{row['Airport_Dep']} → {row['Airport_Arr']} | Date: {row['Date']}</small>
                <p style='margin-top:8px;'>
                    Risk Score: <b>{row['Risk_Score']}</b> — 
                    <span style="color:{'#f87171' if row['Risk_Level']=='High' else ('#facc15' if row['Risk_Level']=='Medium' else '#4ade80')}">
                        {row['Risk_Level']}
                    </span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"View full details for {row['Flight_No']}", expanded=False):

            st.markdown("""
                <style>
                .detail-card {
                    background: #0f172a;
                    padding: 20px;
                    border-radius: 12px;
                    color: #f1f5f9;
                    font-size: 16px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                }
                .detail-title {
                    font-size: 22px;
                    font-weight: 700;
                    margin-bottom: 10px;
                    color: #38bdf8;
                }
                .detail-label {
                    font-size: 16px;
                    font-weight: 600;
                    color: #e2e8f0;
                }
                .detail-value {
                    font-size: 16px;
                    color: #cbd5e1;
                }
                .divider {
                    height: 1px;
                    background: #334155;
                    margin: 12px 0;
                }
                </style>
            """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="detail-card">

                    <div class="detail-title">Flight Details</div>

                    <span class="detail-label">Flight Number:</span>
                    <span class="detail-value">{row["Flight_No"]}</span><br>

                    <span class="detail-label">Aircraft Type:</span>
                    <span class="detail-value">{row["AC_Type"]}</span><br>

                    <span class="detail-label">Registration:</span>
                    <span class="detail-value">{row["Registration"]}</span><br>

                    <div class="divider"></div>

                    <span class="detail-label">Pilot ID:</span>
                    <span class="detail-value">{row["Pilot_ID"]}</span><br>

                    <span class="detail-label">Pilot Hours (30 Days):</span>
                    <span class="detail-value">{row["Pilot_Hours_Last30"]}</span><br>

                    <span class="detail-label">Total Experience:</span>
                    <span class="detail-value">{row["Pilot_Hours_Total"]} hours</span><br>

                    <div class="divider"></div>

                    <span class="detail-label">Fuel Quantity:</span>
                    <span class="detail-value">{row["Fuel_Quantity"]} L</span><br>

                    <span class="detail-label">Oil Pressure:</span>
                    <span class="detail-value">{row["Oil_Pressure"]} psi</span><br>

                    <span class="detail-label">Hydraulic Pressure:</span>
                    <span class="detail-value">{row["Hydraulic_Pressure"]} psi</span><br>

                    <span class="detail-label">Brake Status:</span>
                    <span class="detail-value">{row["Brake_Status"]}</span><br>

                    <div class="divider"></div>

                    <span class="detail-label">Weather:</span>
                    <span class="detail-value">{row["Weather"]}</span><br>

                    <span class="detail-label">Maintenance Remarks:</span>
                    <span class="detail-value">{row["Maintenance_Remarks"]}</span><br>

                </div>
            """, unsafe_allow_html=True)

st.write("---")
st.success("Dashboard Generated Successfully ✔️")
