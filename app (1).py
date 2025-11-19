# app.py - Premium Dark Card-Centric L3 Dashboard (A+B combined)
import streamlit as st
import pandas as pd
import numpy as np
import re, os
from io import BytesIO
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# optional libs
try:
    import joblib
except Exception:
    joblib = None
try:
    from fpdf import FPDF
except Exception:
    FPDF = None

# ---------------- Page config ----------------
st.set_page_config(page_title="Flight Safety — Premium L3", layout="wide")

# ---------------- CSS - Dark premium theme ----------------
st.markdown(
    """
    <style>
    :root{
      --bg:#0b1020;
      --panel: rgba(255,255,255,0.04);
      --glass: rgba(255,255,255,0.03);
      --muted:#98a0b3;
      --accent1:#0ea5a3;
      --accent2:#7c3aed;
      --danger:#ff6b6b;
      --warn:#f59e0b;
      --safe:#34d399;
    }
    body { background: var(--bg); color: #e6eef8; }
    .topbar{ display:flex; justify-content:space-between; align-items:center; gap:12px; }
    .hero {
      background: linear-gradient(90deg, rgba(6,12,27,0.6) 0%, rgba(6,18,40,0.6) 100%);
      border-radius:14px;
      padding:18px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.65);
      margin-bottom:18px;
      border: 1px solid rgba(255,255,255,0.03);
    }
    .hero h1 { margin:0; font-size:26px; letter-spacing:0.2px; }
    .muted { color: var(--muted); font-size:13px; margin-top:6px; }
    .controls { background: var(--panel); padding:12px; border-radius:10px; border:1px solid rgba(255,255,255,0.03); }
    .grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap:14px; }
    .flight-card {
      background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
      border-radius:12px;
      padding:12px;
      transition: transform 0.14s ease, box-shadow 0.14s ease;
      border: 1px solid rgba(255,255,255,0.04);
      cursor: pointer;
    }
    .flight-card:hover { transform: translateY(-6px); box-shadow: 0 18px 40px rgba(12,20,40,0.6); }
    .flight-title { font-weight:700; font-size:15px; margin-bottom:6px; color:#eaf4ff; }
    .meta { color:var(--muted); font-size:12px; }
    .score-pill { padding:6px 10px; border-radius:10px; font-weight:700; font-size:13px; display:inline-block; }
    .pill-high { background: rgba(255,80,80,0.12); color:var(--danger); border: 1px solid rgba(255,80,80,0.12); }
    .pill-med { background: rgba(245,158,11,0.08); color:var(--warn); border: 1px solid rgba(245,158,11,0.08); }
    .pill-low { background: rgba(52,211,153,0.08); color:var(--safe); border: 1px solid rgba(52,211,153,0.08); }
    .detail-panel { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:16px; border-radius:12px; border:1px solid rgba(255,255,255,0.03); }
    .small { color:var(--muted); font-size:13px; }
    .recommend { background: linear-gradient(90deg,var(--accent1),var(--accent2)); padding:8px 10px; border-radius:8px; color:#001219; font-weight:700; display:inline-block; }
    /* responsive adjustments */
    @media (max-width:900px){
      .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Utilities & scoring ----------------
STOPWORDS = {'the','and','a','an','in','on','at','of','to','for','with','from','by','is','was','were','has','had','that','this','it','as','be','are','or','but'}
def clean_text_simple(s):
    if pd.isna(s): return ""
    s = str(s).lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    toks = s.split()
    toks = [t for t in toks if t not in STOPWORDS and len(t)>1]
    return " ".join(toks)

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
    try:
        ph = float(row.get('Pilot_Hours_Last_7_Days', 0) or 0)
        if ph > 60: score += 25
        elif ph > 45: score += 12
    except: pass
    try:
        exp = float(row.get('Pilot_Experience_Hours', 0) or 0)
        if exp < 200: score += 15
        elif exp < 1000: score += 7
    except: pass
    try:
        m = float(row.get('Last_Maintenance_Days_Ago', 0) or 0)
        if m > 180: score += 25
        elif m > 90: score += 10
    except: pass
    try:
        vib = float(row.get('Engine_Vibration_mm_s', 0) or 0)
        if vib > 4.0: score += 20
        elif vib > 2.5: score += 10
    except: pass
    try:
        fi = float(row.get('Fuel_Imbalance_pct', 0) or 0)
        if fi > 10: score += 15
        elif fi > 5: score += 7
    except: pass
    score += weather_severity_score(row.get('Weather',''))
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

RECOMM = {
    'Pilot Hours': "Reassign duty or add an experienced co-pilot.",
    'Maintenance': "Ground aircraft for detailed maintenance inspection.",
    'Engine Vibration': "Perform comprehensive engine checks.",
    'Fuel Imbalance': "Resolve fuel distribution before departure.",
    'Weather': "Delay or reroute based on forecast."
}

# optional ML model
risk_ml = None
if joblib is not None and os.path.exists("risk_model.pkl"):
    try:
        risk_ml = joblib.load("risk_model.pkl")
    except Exception:
        risk_ml = None

# ---------------- Top hero ----------------
st.markdown(f"""
<div class="hero">
  <div class="topbar">
    <div>
      <h1>✈️ Flight Safety — Live Pre-Flight Diagnostic</h1>
      <div class="muted">Card-centric flight explorer — click a flight card on left to open full detail panel.</div>
    </div>
    <div style="text-align:right">
      <div class="small">Demo • {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Upload & Demo")
    uploaded = st.file_uploader("Upload flights CSV (one row per flight)", type=["csv"])
    st.markdown("---")
    st.caption("If you want ML augmentation, place risk_model.pkl next to app.py")
    rule_w = st.slider("Rule weight (hybrid)", 0.0, 1.0, 0.7, 0.05)
    st.markdown("---")
    if st.button("Generate small demo CSV"):
        demo = pd.DataFrame([
            {"Flight_No":"FL1001","AC_Type":"A320","Registration":"VT-AAA","Date":"2025-11-20","Pilot_ID":"P102","Pilot_Hours_Last_7_Days":38,"Pilot_Experience_Hours":3500,"Last_Maintenance_Days_Ago":30,"Weather":"Clear","Engine_Vibration_mm_s":1.2,"Fuel_Imbalance_pct":1.0,"Passenger_Load_pct":85,"Summary":"Regular flight."},
            {"Flight_No":"FL1002","AC_Type":"B737","Registration":"VT-AAB","Date":"2025-11-20","Pilot_ID":"P103","Pilot_Hours_Last_7_Days":68,"Pilot_Experience_Hours":120,"Last_Maintenance_Days_Ago":200,"Weather":"Heavy rain with thunder","Engine_Vibration_mm_s":3.5,"Fuel_Imbalance_pct":6.0,"Passenger_Load_pct":98,"Summary":"Heavy rain, rough approach."},
            {"Flight_No":"FL1003","AC_Type":"A330","Registration":"VT-AAC","Date":"2025-11-20","Pilot_ID":"P104","Pilot_Hours_Last_7_Days":50,"Pilot_Experience_Hours":900,"Last_Maintenance_Days_Ago":100,"Weather":"Moderate rain","Engine_Vibration_mm_s":2.8,"Fuel_Imbalance_pct":0.5,"Passenger_Load_pct":70,"Summary":"Normal ops."},
        ])
        demo.to_csv("sample_flights_l3.csv", index=False)
        st.success("sample_flights_l3.csv saved in working directory. Download and upload to test.")

if uploaded is None:
    st.info("Upload a CSV to begin (or generate sample from sidebar).")
    st.stop()

# ---------------- Load CSV ----------------
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error("Failed to load CSV: " + str(e))
    st.stop()

# normalize / fill columns
if 'Summary' in df.columns:
    df['Summary_clean'] = df['Summary'].apply(clean_text_simple)
else:
    df['Summary_clean'] = ""

# compute rule score
df['_Rule_Score'] = df.apply(compute_rule_score, axis=1)

# optional ML scoring
ml_present = False
if risk_ml is not None:
    numeric_cols = ['Pilot_Hours_Last_7_Days','Pilot_Experience_Hours','Last_Maintenance_Days_Ago','Engine_Vibration_mm_s','Fuel_Imbalance_pct','Passenger_Load_pct']
    X_ml = df[[c for c in numeric_cols if c in df.columns]].fillna(0)
    try:
        if hasattr(risk_ml, "predict_proba"):
            proba = risk_ml.predict_proba(X_ml)
            ml_score = proba[:, -1] * 100
        else:
            ml_score = risk_ml.predict(X_ml) * 100
        df['_ML_Score'] = ml_score
        ml_present = True
    except Exception:
        df['_ML_Score'] = np.nan
        ml_present = False

# hybrid
if ml_present:
    df['_Hybrid_Score'] = (rule_w * df['_Rule_Score']) + ((1 - rule_w) * df['_ML_Score'])
else:
    df['_Hybrid_Score'] = df['_Rule_Score']
df['_Hybrid_Score'] = df['_Hybrid_Score'].round(1)
df['_Risk_Level'] = df['_Hybrid_Score'].apply(risk_level_from_score)

# ---------------- Main layout: left column cards, right detail ----------------
left_col, right_col = st.columns([1.6, 1])

# allocate selected flight in session_state
if 'selected_flight' not in st.session_state:
    st.session_state['selected_flight'] = None

with left_col:
    st.markdown('<div class="controls">', unsafe_allow_html=True)
    st.markdown("**Search / Filter**")
    q = st.text_input("Flight_No or AC_Type filter (case-insensitive)", value="")
    filtered = df.copy()
    if q.strip():
        mask = filtered.apply(lambda row: row.astype(str).str.contains(q, case=False).any(), axis=1)
        filtered = filtered[mask]
    filtered = filtered.sort_values('_Hybrid_Score', ascending=False)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    st.markdown("<div class='grid'>", unsafe_allow_html=True)
    # show cards
    for idx, row in filtered.iterrows():
        lvl = row['_Risk_Level']
        if lvl == "High":
            pill_class = "pill-high"
        elif lvl == "Medium":
            pill_class = "pill-med"
        else:
            pill_class = "pill-low"
        # small summary snippet
        summ = (row.get('Summary','') or '')[:120]
        html = f"""
        <div class="flight-card" onclick="window.location.hash='{row.get('Flight_No','')}'">
          <div>
            <div class="flight-title">{row.get('Flight_No','-')}</div>
            <div class="meta">{row.get('AC_Type','-')} • {row.get('Registration','-')}</div>
            <div class="small" style="margin-top:8px">{summ}</div>
          </div>
          <div style="text-align:right">
            <div class="score-pill {pill_class}">{row['_Hybrid_Score']} pts</div>
            <div class="small" style="margin-top:8px">{row['_Risk_Level']}</div>
          </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        # clicking: set selected flight
        if st.button(f"Open {row.get('Flight_No')}", key=f"open_{idx}"):
            st.session_state['selected_flight'] = row.get('Flight_No')

    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    sel = st.session_state.get('selected_flight')
    if sel is None:
        # default: pick top risk flight
        sel_row = df.sort_values('_Hybrid_Score', ascending=False).iloc[0]
        sel = sel_row.get('Flight_No')
        st.session_state['selected_flight'] = sel
    sel_row = df[df['Flight_No'].astype(str) == str(sel)]
    if sel_row.empty:
        st.warning("Selected flight not found. Pick from left cards.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        sel_row = sel_row.iloc[0]
        st.markdown(f"### {sel_row.get('Flight_No','-')}  •  {sel_row.get('AC_Type','-')}  ")
        st.markdown(f"<div class='small'>Reg: {sel_row.get('Registration','-')}  • Date: {sel_row.get('Date','-')}</div>", unsafe_allow_html=True)
        st.markdown("---")
        # gauge (plotly)
        val = float(sel_row['_Hybrid_Score'])
        gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=val,
            delta={'reference': 40, 'increasing': {'color': "red"}},
            gauge={
                'axis': {'range':[0,100]},
                'bar': {'color':'#0ea5a3'},
                'steps': [
                    {'range':[0,35],'color':'rgba(52,211,153,0.08)'},
                    {'range':[35,65],'color':'rgba(245,158,11,0.06)'},
                    {'range':[65,100],'color':'rgba(255,80,80,0.06)'}
                ],
                'threshold': {'line': {'color': "red", 'width': 4}, 'value': 65}
            },
            title={'text': "Hybrid Risk Score"}
        ))
        gauge.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=260)
        st.plotly_chart(gauge, use_container_width=True)

        # show detected issues & recommendations
        issues = []
        ph = float(sel_row.get('Pilot_Hours_Last_7_Days',0) or 0)
        if ph > 45: issues.append(("Pilot Hours (7d)", ph, RECOMM.get('Pilot Hours')))
        m = float(sel_row.get('Last_Maintenance_Days_Ago',0) or 0)
        if m > 90: issues.append(("Maintenance overdue (days)", m, RECOMM.get('Maintenance')))
        vib = float(sel_row.get('Engine_Vibration_mm_s',0) or 0)
        if vib > 2.5: issues.append(("Engine vibration (mm/s)", vib, RECOMM.get('Engine Vibration')))
        fi = float(sel_row.get('Fuel_Imbalance_pct',0) or 0)
        if fi > 5: issues.append(("Fuel Imbalance (%)", fi, RECOMM.get('Fuel Imbalance')))
        w = sel_row.get('Weather','')
        if weather_severity_score(w) > 0: issues.append(("Weather", w, RECOMM.get('Weather')))

        st.subheader("Triggered Checks & Recommendations")
        if issues:
            for t,v,rec in issues:
                st.markdown(f"- **{t}**: `{v}`  →  *{rec}*")
        else:
            st.success("No immediate rule-based issues detected for this flight.")

        st.markdown("---")
        st.subheader("Flight Summary")
        st.write(sel_row.get('Summary','No summary available'))

        # small historical chart: last maintenance days vs score (for demo show neighbors)
        st.subheader("Neighborhood: maintenance vs score (sample)")
        sample = df.sample(min(len(df), 30), random_state=1) if len(df)>1 else df
        fig = px.scatter(sample, x='Last_Maintenance_Days_Ago', y='_Hybrid_Score', color='_Risk_Level',
                         color_discrete_map={'Low':'#34d399','Medium':'#f59e0b','High':'#ff6b6b'},
                         size_max=8, hover_data=['Flight_No','AC_Type'])
        fig.update_layout(height=240, margin=dict(t=6,b=6,l=6,r=6))
        st.plotly_chart(fig, use_container_width=True)

        # Download buttons
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download processed CSV", data=csv_bytes, file_name="processed_flights.csv", mime="text/csv")

        # PDF generation (simple) — fallback if FPDF not installed create CSV
        def create_pdf_bytes(rowdict, issues_list):
            if FPDF is None:
                return None
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=14)
            pdf.cell(0,10, "Pre-Flight Safety Report", ln=1)
            pdf.set_font("Arial", size=10)
            pdf.cell(0,8, f"Flight: {rowdict.get('Flight_No','')}  |  AC: {rowdict.get('AC_Type','')}", ln=1)
            pdf.cell(0,8, f"Hybrid Score: {rowdict.get('_Hybrid_Score','')}", ln=1)
            pdf.ln(4)
            pdf.set_font("Arial", size=11)
            pdf.cell(0,8, "Triggered Checks:", ln=1)
            for t,v,rec in issues_list:
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0,6, f"- {t}: {v}  Recommendation: {rec}")
            out = BytesIO()
            pdf.output(out)
            out.seek(0)
            return out

        if st.button("📄 Generate Single-Flight PDF"):
            pdf_bytes = create_pdf_bytes(sel_row, issues)
            if pdf_bytes is not None:
                st.download_button("Download PDF", data=pdf_bytes, file_name=f"report_{sel_row.get('Flight_No')}.pdf", mime="application/pdf")
            else:
                st.warning("FPDF not installed in environment. PDF unavailable. Use CSV download.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Final note ----------------
st.markdown("<div style='margin-top:18px; color:var(--muted); font-size:13px'>Tip: Click a card's 'Open <Flight>' button to view details. Place a trained 'risk_model.pkl' next to app.py to enable ML augmentation.</div>", unsafe_allow_html=True)
