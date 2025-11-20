# --------------------------------------------------------
# FLIGHT CARDS
# --------------------------------------------------------
st.subheader("🛫 Flight Overview")

for i, row in df.iterrows():

    # OUTER FLIGHT CARD
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

        # FULL DETAILS EXPANDER
        with st.expander(f"View full details for {row['Flight_No']}", expanded=False):

            # STYLE FOR DETAIL CARD
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

            # DETAIL CARD CONTENT
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
