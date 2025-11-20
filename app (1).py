import streamlit as st
import pandas as pd

# --------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------
st.set_page_config(page_title="AI Pre-Flight Safety Dashboard", layout="wide")

# --------------------------------------------------------
# GLOBAL CUSTOM CSS
# --------------------------------------------------------
st.markdown("""
<style>

body {
    background-color: #0f172a;
}

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

.kpi-box {
    background: #1e293b;
    padding: 18px;
    border-radius: 12px;
    color: white;
    text-align: center;
    box-shadow: 0 3px 12px rgba(0,0,0,0.2);
}

.kpi-box h3 {
    font-size: 28px;
}

.kpi-box small {
    color: #94a3b8;
}

/* Styling inside the expander */
.detail-card {
    background: #0f172a;
    padding: 22px;
    border-radius: 12px;
    color: #e2e8f0;
    box-shadow: 0 4px 25px rgba(0,0,0,0.4);
    font-size: 17px;
}

.detail-title {
    font-size: 24px;
    font-weight: 700;
    color: #38bdf8;
    margin-bottom: 12px;
}

.detail-label {
    font-weight: 600;
    color: #f1f5f9;
}

.detail-value {
    color: #cbd5e1;
}

.divider {
    height: 1px;
    background: #334155;
    margin: 14px 0;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------
with st.sidebar:
    st.title("📂 Upload Flight Data")
    uploaded_file = st.file_uploader("Upload CSV file", type="csv")

# --------------------------------------------------------
# RISK COMPUTATION FUNCTIONS
# --------------------------------------------------------
def compute_risk(row):
    score = 0

    # Pilot fatigue
    if row["Pilot_Hours_Last30"] > 55:
        score += 25
    elif row["Pilot_Hours_Last30"] > 45:
        score += 15

    # Weather
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

    # Hydraulic pressure low
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
# MAIN CONTENT
# --------------------------------------------------------
st.title("✈️ AI-Assisted Pre-Flight Safety Dashboard")
st.write("Upload flight data to automatically analyze pre-flight risks and generate detailed operational insights.")

if not uploaded_file:
    st.info("📄 Please upload a CSV file to continue.")
    st.stop()

# Read data
df = pd.read_csv(uploaded_file)

# Compute risk
df["Risk_Score"] = df.apply(compute_risk, axis=1)
df["Risk_Level"] = df["Risk_Score"].apply(risk_label)

# --------------------------------------------------------
# KPI CARDS
# --------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div class='kpi-box'><h3>{len(df)}</h3><small>Total Flights</small></div>", unsafe_allow_html=True)

with col2:
    st.markdown(f"<div class='kpi-box'><h3>{(df['Risk_Level']=='High').sum()}</h3><small>High Risk Flights</small></div>", unsafe_allow_html=True)

with col3:
    st.markdown(f"<div class='kpi-box'><h3>{(df['Risk_Level']=='Medium').sum()}</h3><small>Medium Risk Flights</small></div>", unsafe_allow_html=True)

st.write("---")

# --------------------------------------------------------
# FLIGHT CARDS
# --------------------------------------------------------
st.subheader("🛫 Flight Overview")

for idx, row in df.iterrows():

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

    # Details Expander
    with st.expander(f"View full details for {row['Flight_No']}", expanded=False):

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

                <span class="detail-label">Pilot Hours (Last 30 Days):</span>
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
