# app.py - Option D: Corporate Aero Blue Theme (Production-style)
import streamlit as st
import pandas as pd
import numpy as np
import joblib, os, re
import plotly.express as px, plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

# ---------------- Page config ----------------
st.set_page_config(page_title="Pre-Flight Safety Check — Corporate", layout="wide")

# ---------------- CSS - Corporate Aero Blue Theme ----------------
st.markdown(
    """
    <style>
    :root{
      --bg: #f4f7fb;
      --card: #ffffff;
      --muted: #6b7280;
      --accent: #0b7285; /* deep aqua */
      --accent-2: #0ea5a3; /* teal */
      --danger: #ef4444;
      --warn: #f59e0b;
      --safe: #10b981;
    }
    body { background: var(--bg); }
    .hero {
      background: linear-gradient(90deg, rgba(11,114,133,1) 0%, rgba(14,165,163,1) 100%);
      color: white;
      padding: 28px;
      border-radius: 10px;
      box-shadow: 0 10px 30px rgba(11,114,133,0.08);
      margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-weight:700; }
    .muted { color: var(--muted); font-size:13px; }
    .card {
      background: var(--card);
      border-radius: 10px;
      padding: 12px;
      box-shadow: 0 8px 20px rgba(16,24,40,0.04);
    }
    .kpi { text-align:center; padding:12px; border-radius:8px; }
    .kpi h3 { margin:6px 0 2px 0; }
    .kpi p { margin:0; color:var(--muted); font-size:13px; }
    .flight-card { padding:10px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; }
    .badge { padding:6px 10px; border-radius:8px; font-weight:600; font-size:13px; }
    .badge-high { background:#fff1f2; color:var(--danger); border:1px solid rgba(239,68,68,0.08); }
    .badge-med { background:#fffbeb; color:var(--warn); border:1px solid rgba(245,158,11,0.08); }
    .badge-low { background:#ecfdf5; color:var(--safe); border:1px solid rgba(16,185,129,0.06); }
    .small { color:var(--muted); font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Utilities ----------------
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
    'Weather': "Delay or reroute based on latest forecasts."
}

# ---------------- Hero / Header ----------------
st.markdown(f"""
<div class="hero">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
      <h1>✈️ Pre-Flight Safety Check</h1>
      <div class="small">Corporate demo • Hybrid checks (rules + optional ML) • Automated recommendations</div>
    </div>
    <div style="text-align:right">
      <div class="small">Status: <strong>Demo</strong></div>
      <div class="small">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Upload & Settings")
    uploaded = st.file_uploader("Upload flights CSV (batch)", type=['csv'], help="CSV with one row per flight.")
    st.markdown("---")
    st.caption("Optional: place risk_model.pkl in app root to enable ML augmentation.")
    rule_w = st.slider("Rule weight (hybrid)", 0.0, 1.0, 0.6, 0.1)
    st.markdown("---")
    st.markdown("**Recommended CSV columns** (case sensitive):")
    st.text("Flight_No,AC_Type,Registration,Date,Pilot_ID,Pilot_Hours_Last_7_Days,Pilot_Experience_Hours,Last_Maintenance_Days_Ago,Weather,Engine_Vibration_mm_s,Fuel_Imbalance_pct,Passenger_Load_pct")
    st.markdown("---")
    if st.button("Generate demo CSV (120 rows)"):
        # small demo generator to help testing quickly
        import numpy as np, pandas as pd
        from datetime import datetime, timedelta
        np.random.seed(2)
        ac_types = ['A320','A330','B737','B777','B787','A350','Embraer E190']
        airports = ['DEL','BOM','BLR','MAA','CCU','HYD','PNQ','GOI']
        rows=[]
        for i in range(120):
            rows.append({
                "Flight_No":f"DF{1000+i}",
                "AC_Type":np.random.choice(ac_types),
                "Registration":f"VT-{np.random.choice(list('ABCDEFG'))}{np.random.randint(100,999)}",
                "Date":(datetime.now()-pd.to_timedelta(np.random.randint(0,5),'D')).strftime('%Y-%m-%d'),
                "Pilot_ID":f"P{np.random.randint(1000,9999)}",
                "Pilot_Hours_Last_7_Days":int(np.clip(np.random.normal(38,12),5,90)),
                "Pilot_Experience_Hours":int(np.clip(np.random.normal(1500,1200),50,10000)),
                "Last_Maintenance_Days_Ago":int(np.clip(np.random.exponential(60),0,400)),
                "Weather":np.random.choice(['Clear','Light rain','Heavy rain with thunder','Storm','Clear, gusty winds'],p=[0.6,0.18,0.08,0.06,0.08]),
                "Engine_Vibration_mm_s":round(float(np.clip(np.random.normal(1.5,1.0),0.2,8.0)),2),
                "Fuel_Imbalance_pct":round(abs(np.random.normal(1.0,3.5)),2),
                "Passenger_Load_pct":int(np.clip(np.random.normal(85,10),10,100))
            })
        df_demo = pd.DataFrame(rows)
        df_demo.to_csv("demo_flights_corporate.csv", index=False)
        st.success("Saved demo_flights_corporate.csv in working directory. Download & upload to test.")

# ---------------- If no file uploaded, prompt ----------------
if uploaded is None:
    st.info("Upload a flights CSV (or use the demo CSV generator in the sidebar).")
    st.stop()

# ---------------- Load CSV ----------------
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error("Failed to read CSV: " + str(e))
    st.stop()

# ensure columns & clean
if 'Summary' in df.columns:
    df['Summary_clean'] = df['Summary'].apply(clean_text_simple)
else:
    df['Summary_clean'] = ""

# compute rule scores
with st.spinner("Computing rule-based risk scores..."):
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
    except Exception as e:
        st.warning("Loaded risk_model.pkl but failed to compute ML scores: "+str(e))
        df['_ML_Score'] = np.nan

# hybrid score
if ml_present:
    df['_Hybrid_Score'] = (rule_w * df['_Rule_Score']) + ((1-rule_w) * df['_ML_Score'])
else:
    df['_Hybrid_Score'] = df['_Rule_Score']

df['_Hybrid_Score'] = df['_Hybrid_Score'].round(1)
df['_Risk_Level'] = df['_Hybrid_Score'].apply(risk_level_from_score)

# ---------------- Layout: Left list | Center overview | Right detail ----------------
left, center, right = st.columns([2,3,2])

# LEFT: Flight list (card-like)
with left:
    st.markdown("<div class='card'><h4 style='margin:4px 0'>Flights</h4>", unsafe_allow_html=True)
    q = st.text_input("Filter Flight_No / AC_Type", "")
    limit = st.number_input("Show top N", min_value=5, max_value=500, value=20, step=5)
    df_list = df.copy()
    if q.strip():
        mask = df_list.astype(str).apply(lambda r: r.str.contains(q, case=False).any(), axis=1)
        df_list = df_list[mask]
    df_list = df_list.sort_values("_Hybrid_Score", ascending=False).head(limit)
    for idx, r in df_list.iterrows():
        lvl = r['_Risk_Level']
        badge_cls = "badge-low" if lvl=="Low" else ("badge-med" if lvl=="Medium" else "badge-high")
        st.markdown(
            f"<div class='flight-card'><div><b>{r.get('Flight_No','-')}</b><div class='small'>{r.get('AC_Type','')}, {r.get('Registration','')}</div></div>"
            f"<div style='text-align:right'><div class='{badge_cls} badge'>{lvl}</div><div class='small' style='margin-top:6px'>{r['_Hybrid_Score']} pts</div></div></div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# CENTER: KPIs and charts
with center:
    st.markdown("<div class='card'><h4 style='margin:4px 0'>Overview</h4>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><h3>{len(df)}</h3><p>Total Flights</p></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><h3 style='color:var(--danger)'>{int((df['_Risk_Level']=='High').sum())}</h3><p>High Risk</p></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><h3 style='color:var(--accent)'>{df['_Hybrid_Score'].mean():.1f}</h3><p>Average Hybrid Score</p></div>", unsafe_allow_html=True)
    st.markdown("---")
    # Risk distribution
    fig = px.histogram(df, x='_Risk_Level', color='_Risk_Level',
                       category_orders={'_Risk_Level':['Low','Medium','High']},
                       color_discrete_map={'Low':'#10b981','Medium':'#f59e0b','High':'#ef4444'},
                       title="Risk Level Distribution")
    fig.update_layout(margin=dict(t=30,b=10,l=10,r=10), height=320, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    if 'Last_Maintenance_Days_Ago' in df.columns:
        fig2 = px.scatter(df, x='Last_Maintenance_Days_Ago', y='_Hybrid_Score', color='_Risk_Level',
                          color_discrete_map={'Low':'#10b981','Medium':'#f59e0b','High':'#ef4444'},
                          title="Hybrid Score vs Days Since Last Maintenance", height=300)
        st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# RIGHT: Selected flight details + gauge + PDF
with right:
    st.markdown("<div class='card'><h4 style='margin:4px 0'>Selected Flight</h4>", unsafe_allow_html=True)
    if 'Flight_No' in df.columns:
        sel = st.selectbox("Select flight", df['Flight_No'].astype(str).tolist())
        row = df[df['Flight_No'].astype(str) == sel].iloc[0]
    else:
        row = df.iloc[0]
    st.write(f"**{row.get('Flight_No','-')}**  •  {row.get('AC_Type','-')}  •  {row.get('Registration','-')}")
    st.write(f"<div class='small'>Date: {row.get('Date','-')}  • Pilot: {row.get('Pilot_ID','-')}</div>", unsafe_allow_html=True)
    st.markdown("---")
    # Gauge
    val = float(row['_Hybrid_Score'])
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        gauge={
            'axis': {'range': [0,100]},
            'bar': {'color': "#0b7285"},
            'steps':[ {'range':[0,35],'color':'#ecfdf5'}, {'range':[35,65],'color':'#fffbeb'}, {'range':[65,100],'color':'#fff1f2'} ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 65}
        },
        title={'text': "Hybrid Risk Score"}
    ))
    gauge.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=260)
    st.plotly_chart(gauge, use_container_width=True)
    st.markdown("---")
    st.subheader("Triggered Checks")
    issues = []
    ph = float(row.get('Pilot_Hours_Last_7_Days',0) or 0)
    if ph>45: issues.append(("Pilot Hours", ph, RECOMM.get('Pilot Hours')))
    m = float(row.get('Last_Maintenance_Days_Ago',0) or 0)
    if m>90: issues.append(("Maintenance overdue (days)", m, RECOMM.get('Maintenance')))
    vib = float(row.get('Engine_Vibration_mm_s',0) or 0)
    if vib>2.5: issues.append(("Engine vibration (mm/s)", vib, RECOMM.get('Engine Vibration')))
    fi = float(row.get('Fuel_Imbalance_pct',0) or 0)
    if fi>5: issues.append(("Fuel Imbalance (%)", fi, RECOMM.get('Fuel Imbalance')))
    w = row.get('Weather','')
    if weather_severity_score(w)>0: issues.append(("Weather", w, RECOMM.get('Weather')))
    if issues:
        for t, v, rec in issues:
            st.markdown(f"**{t}**: {v}  \n→ *{rec}*")
    else:
        st.success("No immediate rule-based issues detected.")
    st.markdown("---")
    # PDF creation
    def create_pdf(rowdict, issues_list):
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
    if st.button("📄 Generate Flight PDF"):
        pdf_bytes = create_pdf(row, issues)
        st.download_button("Download PDF", data=pdf_bytes, file_name=f"report_{row.get('Flight_No','flight')}.pdf", mime="application/pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Footer: processed table + download ----------------
st.markdown("<div style='margin-top:18px' class='card'>", unsafe_allow_html=True)
st.markdown("### Processed results (preview)")
display_cols = [c for c in df.columns if c not in ['Summary','Summary_clean']]
st.dataframe(df[display_cols].head(50), height=300)
csv_bytes = df.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download processed results (CSV)", data=csv_bytes, file_name="safety_check_results.csv", mime="text/csv")
st.markdown("</div>", unsafe_allow_html=True)
