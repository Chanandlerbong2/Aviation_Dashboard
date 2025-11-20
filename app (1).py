import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import io

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

/* Detail Panel (Fixed Visibility) */
.detail-card {
    background: #0a0f1a !important;
    padding: 20px;
    border-radius: 12px;
    color: #e2e8f0 !important;
    font-size: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
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
    color: #f8fafc;
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

/* KPI Boxes */
.kpi-box {
    background: #1e293b;
    padding: 14px;
    border-radius: 12px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.2);
    text-align: center;
    color: #f8fafc;
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
# RISK CALCULATION
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
# PDF GENERATOR (FIXED)
# --------------------------------------------------------
def build_pdf_for_row(row, recommendations):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "Pre-Flight Safety Report", ln=True)

    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Flight: {row['Flight_No']} | Aircraft: {row['AC_Type']} | Reg: {row['Registration']}", ln=True)
    pdf.cell(0, 8, f"Route: {row['Airport_Dep']} → {row['Airport_Arr']} | Date: {row['Date']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, f"Risk Score: {row['Risk_Score']} ({row['Risk_Level']})", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, "AI Recommendations:", ln=True)

    pdf.set_font("Arial", size=10)
    for r in recommendations:
        pdf.multi_cell(0, 6, f"- {r}")

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, "Flight Parameters:", ln=True)

    pdf.set_font("Courier", size=10)
    for col in row.index:
        pdf.cell(0, 6, f"{col}: {row[col]}", ln=True)

    # FIX → Return PDF BytesIO
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    return io.BytesIO(pdf_bytes)


# --------------------------------------------------------
# AI SAFETY RECOMMENDATIONS
# --------------------------------------------------------
def get_recommendations(row):
    recs = []

    if row["Pilot_Hours_Last30"] > 55:
        recs.append("Pilot fatigue risk detected. Recommend crew replacement or extended rest.")

    if "rain" in row["Weather"].lower():
        recs.append("Wet-weather landing/takeoff risk. Require braking action assessment.")

    if row["Fuel_Quantity"] < 7000:
        recs.append("Fuel below optimal reserve. Confirm refueling before dispatch.")

    if row["Brake_Status"] == "WARNING":
        recs.append("Brake warning detected. Mandatory engineering inspection required.")

    if row["Hydraulic_Pressure"] < 3000:
        recs.append("Hydraulic pressure low. Require check for system leaks.")

    if row["Oil_Pressure"] < 65:
        recs.append("Oil pressure slightly low. Maintenance review recommended.")

    if len(recs) == 0:
        recs.append("No major risks detected. Aircraft cleared for dispatch.")

    return recs


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
st.title("✈️ AI-Assisted Pre-Flight Safety Dashboard")
st.write("Upload flight data to view automated safety checks, recommendations and reports.")

if not file:
    st.info("Upload a CSV file to begin.")
    st.stop()

df = pd.read_csv(file)
df["Risk_Score"] = df.apply(compute_risk, axis=1)
df["Risk_Level"] = df["Risk_Score"].apply(risk_label)


# --------------------------------------------------------
# KPI SECTION
# --------------------------------------------------------
c1, c2, c3 = st.columns(3)

c1.markdown(f"<div class='kpi-box'><h3>{len(df)}</h3><small>Total Flights</small></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='kpi-box'><h3>{(df['Risk_Level']=='High').sum()}</h3><small>High Risk</small></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='kpi-box'><h3>{(df['Risk_Level']=='Medium').sum()}</h3><small>Medium Risk</small></div>", unsafe_allow_html=True)


st.write("---")

# --------------------------------------------------------
# FLIGHT CARDS
# --------------------------------------------------------
st.subheader("🛫 Flight Overview")

for i, row in df.iterrows():

    card_color = "#f87171" if row["Risk_Level"] == "High" else ("#fb923c" if row["Risk_Level"] == "Medium" else "#4ade80")

    st.markdown(
        f"""
        <div class="card">
            <h3>{row['Flight_No']} • {row['AC_Type']}</h3>
            <small>{row['Airport_Dep']} → {row['Airport_Arr']} | {row['Date']}</small>
            <p style='margin-top:8px;'>
                Risk Score: <b>{row['Risk_Score']}</b> — 
                <span style="color:{card_color};"><b>{row['Risk_Level']}</b></span>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander(f"View full details for {row['Flight_No']}"):
        st.markdown("<div class='detail-card'>", unsafe_allow_html=True)

        st.markdown("<div class='detail-title'>Flight Details</div>", unsafe_allow_html=True)

        for col in df.columns:
            st.markdown(
                f"<span class='detail-label'>{col}:</span> "
                f"<span class='detail-value'>{row[col]}</span><br>",
                unsafe_allow_html=True
            )

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # AI Recommendations
        recs = get_recommendations(row)
        st.markdown("<div class='detail-title'>AI Safety Recommendations</div>", unsafe_allow_html=True)
        for r in recs:
            st.markdown(f"- {r}")

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # PDF BUTTON
        pdf_bytes = build_pdf_for_row(row, recs)
        st.download_button(
            "📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"Report_{row['Flight_No']}.pdf",
            mime="application/pdf"
        )

        st.markdown("</div>", unsafe_allow_html=True)

st.success("Dashboard Ready ✔️")
