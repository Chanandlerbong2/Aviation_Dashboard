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

/* FIXED — EXPANDER CONTENT BOX NOW DARK & READABLE */
.expand-box {
    background: #1e293b !important;
    padding: 20px;
    border-radius: 12px;
    margin-top: 10px;
    border: 1px solid #334155;
    color: #e2e8f0 !important;
}
.expand-box h4, .expand-box h3, .expand-box p, .expand-box li {
    color: #e2e8f0 !important;
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

    if row["Pilot_Hours_Last30"] > 55:
        score += 25
    elif row["Pilot_Hours_Last30"] > 45:
        score += 15

    w = str(row["Weather"]).lower()
    if "rain" in w:
        score += 15
    elif "cloud" in w:
        score += 8

    if str(row["Brake_Status"]).strip().upper() == "WARNING":
        score += 25

    if row["Fuel_Quantity"] < 7000:
        score += 15

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

df = pd.read_csv(file)
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
        risk_color = "#f87171" if row["Risk_Level"]=="High" else ("#facc15" if row["Risk_Level"]=="Medium" else "#4ade80")

        st.markdown(
            f"""
            <div class="card">
                <h3>{row['Flight_No']} • {row['AC_Type']}</h3>
                <small>{row['Airport_Dep']} → {row['Airport_Arr']} | Date: {row['Date']}</small>
                <p style='margin-top:8px;'>
                    Risk Score: <b>{row['Risk_Score']}</b> — 
                    <span style="color:{risk_color};">{row['Risk_Level']}</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("🔍 View Full Flight Details"):
            st.markdown(f"""
            <div class='expand-box'>
            <h4>Flight Details</h4>
            • **Registration:** {row['Registration']}  
            • **Pilot ID:** {row['Pilot_ID']}  
            • **Pilot Hours (30 days):** {row['Pilot_Hours_Last30']}  
            • **Pilot Total Hours:** {row['Pilot_Hours_Total']}  

            ### Technical Readings  
            • **Fuel Quantity:** {row['Fuel_Quantity']}  
            • **Oil Pressure:** {row['Oil_Pressure']}  
            • **Hydraulic Pressure:** {row['Hydraulic_Pressure']}  
            • **Brake Status:** {row['Brake_Status']}  

            ### Other  
            • **Weather:** {row['Weather']}  
            • **ATC Clearance:** {row['ATC_Clearance']}  
            • **Maintenance Remarks:** {row['Maintenance_Remarks']}
            </div>
            """, unsafe_allow_html=True)

st.write("---")
st.success("Dashboard Generated Successfully ✔️")
