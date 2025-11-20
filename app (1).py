# app.py — Pre-Flight Safety Dashboard with AI recommendations + PDF export
import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
import os

# ----------------- Page config -----------------
st.set_page_config(page_title="AI Pre-Flight Safety Dashboard", layout="wide")

# ----------------- Optional banner image (uploaded earlier) -----------------
# Developer/upload path present in conversation:
BANNER_PATH = '/mnt/data/A_screenshot_of_a_web-based_application_titled_"AI.png'
if os.path.exists(BANNER_PATH):
    st.image(BANNER_PATH, use_column_width=True)

# ----------------- Styling (dark theme look) -----------------
st.markdown("""
<style>
body { background-color: #071029; color: #e6eef8; }
.card { background: linear-gradient(135deg,#0b1220,#17202b); padding:18px; border-radius:12px; box-shadow:0 8px 30px rgba(0,0,0,.6); color: #e6eef8; margin-bottom:12px; }
.kpi { background:#0f1724; padding:12px; border-radius:10px; text-align:center; }
.detail-card { background:#071225; padding:16px; border-radius:10px; color:#dbeafe; }
.small-muted { color:#94a3b8; }
a { color: #7dd3fc; }
</style>
""", unsafe_allow_html=True)

# ----------------- Sidebar: upload -----------------
with st.sidebar:
    st.title("📁 Upload Flights CSV")
    uploaded = st.file_uploader("CSV (one row per flight)", type="csv")
    st.markdown("---")
    st.markdown("**Demo / testing:** click to create a sample CSV to upload")
    if st.button("Generate sample CSV"):
        sample = pd.DataFrame([
            {"Flight_No":"AI101","AC_Type":"A320","Registration":"VT-ABC","Date":"2025-11-19","Pilot_ID":"P001","Pilot_Hours_Last30":45,"Pilot_Hours_Total":1200,"Weather":"Clear","Airport_Dep":"DEL","Airport_Arr":"BLR","Fuel_Quantity":8000,"Oil_Pressure":70,"Hydraulic_Pressure":3000,"Brake_Status":"OK","ATC_Clearance":"YES","Maintenance_Remarks":"None","Engine_Vibration_mm_s":1.2,"Fuel_Imbalance_pct":1.0,"Passenger_Load_pct":85},
            {"Flight_No":"AI202","AC_Type":"B737","Registration":"VT-XYZ","Date":"2025-11-19","Pilot_ID":"P002","Pilot_Hours_Last30":68,"Pilot_Hours_Total":980,"Weather":"Heavy rain with thunder","Airport_Dep":"BOM","Airport_Arr":"DEL","Fuel_Quantity":7500,"Oil_Pressure":65,"Hydraulic_Pressure":3200,"Brake_Status":"OK","ATC_Clearance":"YES","Maintenance_Remarks":"Minor scratch on nose gear","Engine_Vibration_mm_s":3.5,"Fuel_Imbalance_pct":6.0,"Passenger_Load_pct":98},
            {"Flight_No":"AI303","AC_Type":"A350","Registration":"VT-PQR","Date":"2025-11-19","Pilot_ID":"P003","Pilot_Hours_Last30":60,"Pilot_Hours_Total":1500,"Weather":"Cloudy","Airport_Dep":"BLR","Airport_Arr":"HYD","Fuel_Quantity":9000,"Oil_Pressure":72,"Hydraulic_Pressure":3100,"Brake_Status":"WARNING","ATC_Clearance":"YES","Maintenance_Remarks":"Brake check required","Engine_Vibration_mm_s":2.8,"Fuel_Imbalance_pct":0.5,"Passenger_Load_pct":70},
        ])
        sample.to_csv("sample_flights.csv", index=False)
        st.success("Saved sample_flights.csv in working directory — download & re-upload to test.")

# ----------------- Helper: compute rule checks and recommendations -----------------
def compute_rule_score(row):
    score = 0.0
    # pilot hours fatigue
    try:
        ph = float(row.get("Pilot_Hours_Last30", 0))
        if ph > 60: score += 25
        elif ph > 45: score += 12
    except: pass
    # maintenance overdue (example: days since maintenance not provided — uses Maintenance_Remarks presence)
    rm = str(row.get("Maintenance_Remarks", "")).lower()
    if "brake" in rm or "check" in rm or "overdue" in rm: score += 18
    # engine vibration
    try:
        vib = float(row.get("Engine_Vibration_mm_s", 0))
        if vib > 4.0: score += 22
        elif vib > 2.5: score += 10
    except: pass
    # fuel imbalance
    try:
        fi = float(row.get("Fuel_Imbalance_pct", 0))
        if fi > 10: score += 15
        elif fi > 5: score += 7
    except: pass
    # brake warning
    bs = str(row.get("Brake_Status", "")).lower()
    if "warning" in bs or "fail" in bs: score += 20
    # weather severity
    w = str(row.get("Weather", "")).lower()
    if any(x in w for x in ["thunder","storm","hurricane","severe"]): score += 20
    elif any(x in w for x in ["rain","sleet","snow","hail"]): score += 10
    # cap
    return min(round(score,1), 100.0)

# map small set of recommendation actions
RECOMM_MAP = {
    "Pilot Hours": "Crew rest / reassign duty or add experienced relief pilot.",
    "Maintenance": "Ground aircraft and perform maintenance inspection per checklist.",
    "Engine Vibration": "Immediate engine diagnostic and borescope inspection.",
    "Fuel Imbalance": "Rebalance tanks, verify sensors and fuel pumps.",
    "Brake Warning": "Brake system deep inspection before dispatch.",
    "Weather": "Delay flight or obtain updated MET brief; consider alternate routing.",
    "ATC": "Verify clearance with tower and confirm routing."
}

def generate_recommendations(row):
    recs = []
    # Pilot hours
    try:
        if float(row.get("Pilot_Hours_Last30", 0)) > 60:
            recs.append(("Pilot Hours", RECOMM_MAP["Pilot Hours"]))
        elif float(row.get("Pilot_Hours_Last30", 0)) > 45:
            recs.append(("Pilot Hours", "Monitor fatigue and consider relief pilot."))
    except: pass
    # maintenance text
    rm = str(row.get("Maintenance_Remarks", "")).lower()
    if rm and any(x in rm for x in ["brake","overdue","check","replace","leak","scratch"]):
        recs.append(("Maintenance", RECOMM_MAP["Maintenance"]))
    # engine vibration
    try:
        vib = float(row.get("Engine_Vibration_mm_s", 0))
        if vib > 4.0:
            recs.append(("Engine Vibration", RECOMM_MAP["Engine Vibration"]))
        elif vib > 2.5:
            recs.append(("Engine Vibration", "Schedule immediate engine monitoring & precautionary checks."))
    except: pass
    # fuel imbalance
    try:
        fi = float(row.get("Fuel_Imbalance_pct", 0))
        if fi > 5:
            recs.append(("Fuel Imbalance", RECOMM_MAP["Fuel Imbalance"]))
    except: pass
    # brake
    bs = str(row.get("Brake_Status", "")).lower()
    if "warning" in bs or "fail" in bs:
        recs.append(("Brake Warning", RECOMM_MAP["Brake Warning"]))
    # weather
    w = str(row.get("Weather", "")).lower()
    if any(x in w for x in ["thunder","storm","hurricane","severe"]):
        recs.append(("Weather", RECOMM_MAP["Weather"]))
    elif any(x in w for x in ["rain","snow","sleet","hail"]):
        recs.append(("Weather", "Check runway conditions and performance margins."))
    # ATC clearance
    atc = str(row.get("ATC_Clearance", "")).lower()
    if atc not in ["yes","y","true","1"]:
        recs.append(("ATC", RECOMM_MAP["ATC"]))
    # If nothing triggered
    if not recs:
        recs.append(("OK", "No immediate recommendations: normal dispatch checks only."))
    return recs

# ----------------- PDF generation -----------------
def build_pdf_for_row(row, recs):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 8, "Pre-Flight Safety Report", ln=True)
    pdf.ln(4)
    pdf.set_font("Arial", size=11)
    # flight header
    pdf.cell(0, 7, f"Flight: {row.get('Flight_No', 'N/A')}  |  AC: {row.get('AC_Type','')}  |  Reg: {row.get('Registration','')}", ln=True)
    pdf.cell(0, 7, f"Date: {row.get('Date','')}  |  Route: {row.get('Airport_Dep','')} -> {row.get('Airport_Arr','')}", ln=True)
    pdf.ln(4)
    # risk score
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, f"Risk Score: {row.get('_Rule_Score', 'N/A')}", ln=True)
    pdf.ln(4)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 6, "Triggered Checks and Recommendations:")
    pdf.ln(2)
    for t, rec in recs:
        pdf.set_font("Arial", "B", 11)
        pdf.multi_cell(0, 6, f"- {t}:")
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, f"    {rec}")
    pdf.ln(4)
    # add table of numeric fields (simple)
    pdf.set_font("Courier", size=9)
    keys = ["Pilot_ID","Pilot_Hours_Last30","Pilot_Hours_Total","Fuel_Quantity","Oil_Pressure","Hydraulic_Pressure","Brake_Status"]
    for k in keys:
        pdf.cell(0, 6, f"{k}: {row.get(k,'')}", ln=True)
    # output bytes
    out = io.BytesIO()
    pdf.output(out)
    out.seek(0)
    return out

# ----------------- Main UI logic -----------------
st.header("AI-assisted Pre-Flight Diagnostic")

if uploaded is None:
    st.info("Upload the CSV (or generate sample) to display flight cards.")
    st.stop()

# read CSV into dataframe (simple parsing)
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Failed to read CSV: {e}")
    st.stop()

# ensure expected numeric columns exist, coerce when missing
numeric_cols_defaults = {
    "Pilot_Hours_Last30": 0, "Engine_Vibration_mm_s": 0.0, "Fuel_Imbalance_pct": 0.0,
    "Fuel_Quantity": 0, "Hydraulic_Pressure": 0, "Oil_Pressure": 0
}
for c, d in numeric_cols_defaults.items():
    if c not in df.columns:
        df[c] = d
    else:
        # try to coerce to numeric safely
        try:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(d)
        except:
            df[c] = d

# compute rule score and recommendations
df["_Rule_Score"] = df.apply(compute_rule_score, axis=1)
df["_Risk_Level"] = df["_Rule_Score"].apply(lambda s: "High" if s>=65 else ("Medium" if s>=35 else "Low"))

# display KPIs
c1, c2, c3 = st.columns([1,1,1])
c1.metric("Total Flights", len(df))
c2.metric("High Risk", int((df["_Risk_Level"]=="High").sum()))
c3.metric("Medium Risk", int((df["_Risk_Level"]=="Medium").sum()))

st.markdown("---")

# flight cards — grid layout using columns
st.subheader("Flight Cards — click expand for details & PDF")
cols = st.columns(3)
for i, row in df.iterrows():
    col = cols[i % 3]
    with col:
        st.markdown(f"""<div style='background:linear-gradient(180deg,#0b1220,#0e1a2a);padding:12px;border-radius:10px;box-shadow:0 8px 20px rgba(0,0,0,0.6);'>
            <h4 style='margin:0;color:#c7f9ff'>{row.get('Flight_No','')}</h4>
            <div style='color:#9fbfdc'>{row.get('AC_Type','')}  •  {row.get('Registration','')}</div>
            <div style='margin-top:8px;color:#dbeafe'>Route: {row.get('Airport_Dep','')} → {row.get('Airport_Arr','')}</div>
            <div style='margin-top:8px;font-weight:700;color:{("#f87171" if row["_Rule_Score"]>=65 else ("#f59e0b" if row["_Rule_Score"]>=35 else "#4ade80"))}'>Risk: {row["_Risk_Level"]} ({row["_Rule_Score"]})</div>
        </div>""", unsafe_allow_html=True)

        with st.expander(f"Details & Actions — {row.get('Flight_No','')}", expanded=False):
            # build recommendation list
            recs = generate_recommendations(row)
            st.markdown("<div class='detail-card'>", unsafe_allow_html=True)
            st.markdown(f"**Flight:** {row.get('Flight_No','')}   •   **AC Type:** {row.get('AC_Type','')}")
            st.markdown(f"**Registration:** {row.get('Registration','')}   •   **Date:** {row.get('Date','')}")
            st.markdown(f"**Pilot ID:** {row.get('Pilot_ID','')}   •   **Pilot Hours (30d):** {row.get('Pilot_Hours_Last30','')}")
            st.markdown(f"**Fuel:** {row.get('Fuel_Quantity','')} L   •   **Brake:** {row.get('Brake_Status','')}")
            st.markdown(f"**Engine Vibration:** {row.get('Engine_Vibration_mm_s','')} mm/s   •   **Fuel Imbalance:** {row.get('Fuel_Imbalance_pct','')}%")
            st.markdown("---")
            st.markdown("**Triggered recommendations:**")
            for t, r in recs:
                st.write(f"- **{t}** — {r}")
            st.markdown("---")
            # Download CSV row
            single_df = pd.DataFrame([row.to_dict()])
            csv_bytes = single_df.to_csv(index=False).encode('utf-8')
            st.download_button(f"📥 Download flight CSV ({row.get('Flight_No','')})", data=csv_bytes, file_name=f"{row.get('Flight_No','flight')}_row.csv", mime="text/csv")

            # Generate PDF and provide download
            pdf_bytes = build_pdf_for_row(row, recs)
            st.download_button("📄 Download PDF Report", data=pdf_bytes, file_name=f"report_{row.get('Flight_No','flight')}.pdf", mime="application/pdf")

            st.markdown("</div>", unsafe_allow_html=True)

st.success("Analysis complete — use the expanders to view details and download reports.")
