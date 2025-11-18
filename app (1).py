# app.py  — Pre-Flight Safety Check (Polished UI)
import streamlit as st
import pandas as pd
import numpy as np
import joblib, os, re
import plotly.express as px
from io import BytesIO
from datetime import datetime
from fpdf import FPDF  # lightweight PDF generator

# ---------- Page config ----------
st.set_page_config(page_title="Pre-Flight Safety Check — AI", layout="wide",
                   initial_sidebar_state="expanded")

# ---------- Styling ----------
st.markdown("""
<style>
/* header gradient */
.header {
  background: linear-gradient(90deg,#0f172a 0%, #0ea5a3 100%);
  color: white;
  padding: 32px;
  border-radius: 10px;
  margin-bottom: 16px;
}
.kpi {
  background: white;
  padding: 12px;
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(14,20,42,0.06);
}
.small-muted { color: #6b7280; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ---------- Utilities ----------
STOPWORDS = {'the','and','a','an','in','on','at','of','to','for','with','from','by','is','was','were','has','had','that','this','it','as','be','are','or','but'}
def clean_text_simple(s):
    if pd.isna(s): return ""
    s = str(s).lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    tokens = s.split()
    tokens = [t for t in tokens if t not in STOPWORDS and len(t)>1]
    return " ".join(tokens)

@st.cache_resource
def load_optional_risk_model():
    try:
        return joblib.load("risk_model.pkl")
    except Exception:
        return None

risk_ml = load_optional_risk_model()

# ---------- Scoring rules ----------
def weather_severity_score(weather_str):
    if pd.isna(weather_str) or str(weather_str).strip()=="":
        return 0
    s = str(weather_str).lower()
    if any(x in s for x in ['cyclone','hurricane','blizzard','tornado','severe thunder','severe storm']):
        return 35
    if any(x in s for x in ['thunder','storm','heavy rain','sleet','hail']):
        return 25
    if any(x in s for x in ['rain','snow','gust','squall']):
        return 10
    return 0

def compute_rule_score(row):
    score = 0.0
    # Pilot hours in last 7 days
    try:
        ph = float(row.get('Pilot_Hours_Last_7_Days', 0) or 0)
        if ph > 60: score += 25
        elif ph > 45: score += 12
    except: pass
    # Pilot experience (lower -> risk)
    try:
        exp = float(row.get('Pilot_Experience_Hours', 0) or 0)
        if exp < 200: score += 15
        elif exp < 1000: score += 7
    except: pass
    # Maintenance overdue
    try:
        m = float(row.get('Last_Maintenance_Days_Ago', 0) or 0)
        if m > 180: score += 25
        elif m > 90: score += 10
    except: pass
    # Engine vibration
    try:
        vib = float(row.get('Engine_Vibration_mm_s', 0) or 0)
        if vib > 4.0: score += 20
        elif vib > 2.5: score += 10
    except: pass
    # Fuel imbalance
    try:
        fi = float(row.get('Fuel_Imbalance_pct', 0) or 0)
        if fi > 10: score += 15
        elif fi > 5: score += 7
    except: pass
    # weather
    score += weather_severity_score(row.get('Weather',''))
    # passenger load small effect
    try:
        pl = float(row.get('Passenger_Load_pct', 0) or 0)
        if pl > 98: score += 3
    except: pass
    score = min(score, 100)
    return round(score,1)

def risk_level_from_score(s):
    if s >= 65: return "High"
    if s >= 35: return "Medium"
    return "Low"

# recommendations mapping
RECOMM = {
    'Pilot Hours': "Reassign duty or add an additional experienced co-pilot.",
    'Maintenance': "Ground aircraft for deep maintenance inspection before flight.",
    'Engine Vibration': "Comprehensive engine inspection (bearings, mounts).",
    'Fuel Imbalance': "Resolve fuel distribution and sensors; postpone if persistent.",
    'Weather': "Delay or reroute flight based on updated MET forecasts."
}

# ---------- Header ----------
st.markdown('<div class="header"><h1 style="margin:0">✈️ Pre-Flight Safety Check — AI Assisted</h1><div class="small-muted">Upload batch flight data; get hybrid (rules + optional ML) risk scores, per-flight recommendations and downloadable reports.</div></div>', unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Upload & Settings")
    st.markdown("**Upload CSV** with flights (batch). Recommended columns below.")
    uploaded = st.file_uploader("Upload flights CSV", type=['csv'], accept_multiple_files=False)
    st.markdown("---")
    st.write("Optional: upload `risk_model.pkl` here if you want ML-based augmentation.")
    st.text("Or place risk_model.pkl in app folder on server.")
    st.markdown("---")
    st.markdown("**Recommended columns** (case sensitive):")
    st.markdown("`Flight_No,AC_Type,Registration,Date,Pilot_ID,Pilot_Hours_Last_7_Days,Pilot_Experience_Hours,Last_Maintenance_Days_Ago,Weather,Engine_Vibration_mm_s,Fuel_Imbalance_pct,Passenger_Load_pct`")
    st.markdown("---")
    st.write("Hybrid weight (Rules vs ML):")
    rule_w = st.slider("Rule weight", min_value=0.0, max_value=1.0, value=0.6, step=0.1)
    st.caption("Hybrid score = rule_weight * RuleScore + (1-rule_weight) * MLScore (if ML provided)")

# ---------- Main ----------
if uploaded is None:
    st.info("Upload a CSV to begin. Use example CSV generator below if you need a quick test file.")
    if st.button("Generate example CSV"):
        sample = pd.DataFrame([
            {"Flight_No":"AI101","AC_Type":"A320","Pilot_Hours_Last_7_Days":40,"Pilot_Experience_Hours":3500,"Last_Maintenance_Days_Ago":30,"Weather":"Clear","Engine_Vibration_mm_s":1.2,"Fuel_Imbalance_pct":1.0,"Passenger_Load_pct":85},
            {"Flight_No":"AI202","AC_Type":"B737","Pilot_Hours_Last_7_Days":68,"Pilot_Experience_Hours":120,"Last_Maintenance_Days_Ago":200,"Weather":"Heavy rain with thunder","Engine_Vibration_mm_s":3.5,"Fuel_Imbalance_pct":6.0,"Passenger_Load_pct":98},
            {"Flight_No":"AI303","AC_Type":"A330","Pilot_Hours_Last_7_Days":50,"Pilot_Experience_Hours":900,"Last_Maintenance_Days_Ago":100,"Weather":"Moderate rain","Engine_Vibration_mm_s":2.8,"Fuel_Imbalance_pct":0.5,"Passenger_Load_pct":70},
        ])
        sample.to_csv("example_flights.csv", index=False)
        st.success("Saved example_flights.csv in working directory. Download it and upload to app to test.")
    st.stop()

# Load CSV
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error("Failed to read CSV: " + str(e))
    st.stop()

st.markdown("### Uploaded flights — preview")
st.dataframe(df.head(10))

# Ensure columns exist and create cleaned summary if present
if 'Summary' in df.columns:
    df['Summary_clean'] = df['Summary'].apply(clean_text_simple)
else:
    df['Summary_clean'] = ""

# compute scores (rules)
with st.spinner("Computing rule-based scores..."):
    df['_Rule_Score'] = df.apply(compute_rule_score, axis=1)

# if ML present, compute ml scores and hybrid
ml_present = False
if risk_ml is not None:
    try:
        # prepare simple feature set — we only pick numeric columns present in df
        numeric_cols = ['Pilot_Hours_Last_7_Days','Pilot_Experience_Hours','Last_Maintenance_Days_Ago','Engine_Vibration_mm_s','Fuel_Imbalance_pct','Passenger_Load_pct']
        X_ml = df[[c for c in numeric_cols if c in df.columns]].fillna(0)
        # If classifier with predict_proba exists:
        if hasattr(risk_ml, "predict_proba"):
            proba = risk_ml.predict_proba(X_ml)
            # choose probability of 'unsafe' as second class if exists, else use max
            ml_score = proba[:, -1] * 100
        else:
            ml_score = risk_ml.predict(X_ml) * 100
        df['_ML_Score'] = ml_score
        ml_present = True
    except Exception as e:
        st.warning("ML risk model found but failed to compute scores — using rule-only. Error: " + str(e))
        df['_ML_Score'] = np.nan

# Hybrid
if ml_present:
    df['_Hybrid_Score'] = (rule_w * df['_Rule_Score']) + ((1-rule_w) * df['_ML_Score'])
else:
    df['_Hybrid_Score'] = df['_Rule_Score']

df['_Hybrid_Score'] = df['_Hybrid_Score'].round(1)
df['_Risk_Level'] = df['_Hybrid_Score'].apply(risk_level_from_score)

# KPIs
col1, col2, col3, col4 = st.columns([2,1,1,1])
col1.markdown("<div class='kpi'><h3 style='margin:0'>Total Flights: <strong>{}</strong></h3></div>".format(len(df)), unsafe_allow_html=True)
col2.markdown("<div class='kpi'><h4 style='margin:0; color:#ef4444'>High</h4><div style='font-size:20px'><strong>{}</strong></div></div>".format(int((df['_Risk_Level']=='High').sum())), unsafe_allow_html=True)
col3.markdown("<div class='kpi'><h4 style='margin:0; color:#f59e0b'>Medium</h4><div style='font-size:20px'><strong>{}</strong></div></div>".format(int((df['_Risk_Level']=='Medium').sum())), unsafe_allow_html=True)
col4.markdown("<div class='kpi'><h4 style='margin:0; color:#10b981'>Low</h4><div style='font-size:20px'><strong>{}</strong></div></div>".format(int((df['_Risk_Level']=='Low').sum())), unsafe_allow_html=True)

st.markdown("---")

# Risk distribution chart
fig = px.histogram(df, x='_Risk_Level', category_orders={'_Risk_Level':['Low','Medium','High']}, color='_Risk_Level',
                   color_discrete_map={'Low':'#10b981','Medium':'#f59e0b','High':'#ef4444'},
                   title="Risk Level Distribution")
fig.update_layout(margin=dict(t=30,b=10,l=10,r=10))
st.plotly_chart(fig, use_container_width=True)

# Display table with filters
st.markdown("### Flights table (click row to view details)")
display_cols = [c for c in df.columns if c not in ['Summary','Summary_clean']]
st.dataframe(df[display_cols].reset_index(drop=True).astype(str), height=300)

# pick flight to inspect
if 'Flight_No' in df.columns:
    sel = st.selectbox("Select Flight_No to view detailed check", df['Flight_No'].astype(str).tolist())
    row = df[df['Flight_No'].astype(str)==sel].iloc[0]
else:
    row = df.iloc[0]

st.markdown("## Detailed report — Flight: " + str(row.get('Flight_No','N/A')))
st.write("**Hybrid Score:**", row['_Hybrid_Score'], " — **Risk Level:**", row['_Risk_Level'])

# Explain why triggered
issues = []
if row['_Rule_Score'] > 0:
    ph = float(row.get('Pilot_Hours_Last_7_Days', 0) or 0)
    if ph > 45: issues.append(("Pilot Hours", ph, RECOMM.get('Pilot Hours')))
    m = float(row.get('Last_Maintenance_Days_Ago', 0) or 0)
    if m > 90: issues.append(("Maintenance overdue (days)", m, RECOMM.get('Maintenance')))
    vib = float(row.get('Engine_Vibration_mm_s', 0) or 0)
    if vib > 2.5: issues.append(("Engine vibration (mm/s)", vib, RECOMM.get('Engine Vibration')))
    fi = float(row.get('Fuel_Imbalance_pct', 0) or 0)
    if fi > 5: issues.append(("Fuel Imbalance (%)", fi, RECOMM.get('Fuel Imbalance')))
    w = row.get('Weather','')
    if weather_severity_score(w) > 0: issues.append(("Weather", w, RECOMM.get('Weather')))

if issues:
    st.subheader("Triggered checks & recommendations")
    for t, val, rec in issues:
        st.markdown(f"- **{t}**: {val}  \n  → Recommendation: *{rec}*")
else:
    st.success("No immediate rule-based issues detected for this flight.")

# Download processed CSV
def to_csv_bytes(dfv):
    return dfv.to_csv(index=False).encode('utf-8')

st.download_button("⬇️ Download processed results (CSV)", data=to_csv_bytes(df), file_name="safety_check_results.csv", mime="text/csv")

# Single flight PDF generation (simple)
def generate_pdf_report(rowdict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0,10, "Pre-Flight Safety Report", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0,8, f"Flight: {rowdict.get('Flight_No','N/A')}    Date: {rowdict.get('Date','')}", ln=1)
    pdf.cell(0,8, f"Hybrid Score: {rowdict.get('_Hybrid_Score','')}", ln=1)
    pdf.ln(4)
    pdf.set_font("Arial", size=11)
    pdf.cell(0,8, "Triggered Checks:", ln=1)
    for t, val, rec in issues:
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0,6, f"- {t}: {val}  Recommendation: {rec}")
    out = BytesIO()
    pdf.output(out)
    out.seek(0)
    return out

if st.button("📄 Download Single Flight PDF Report"):
    pdf_bytes = generate_pdf_report(row)
    st.download_button("Download PDF", data=pdf_bytes, file_name=f"report_{row.get('Flight_No','flight')}.pdf", mime="application/pdf")

st.markdown("----")
st.caption("Hybrid model = rule-based checks by default. Add 'risk_model.pkl' to app folder to enable ML augmentation.")
