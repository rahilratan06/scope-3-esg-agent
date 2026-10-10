import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import graphviz
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from fpdf import FPDF

# -----------------------------------------
# PAGE SETUP
# -----------------------------------------
st.set_page_config(page_title="Scope 3 ESG Process Agent", layout="wide", page_icon="🌱")
st.title("🌱 Autonomous Process Mining & Scope 3 ESG Agent")
st.markdown("Diagnose carbon waste, track dead-hauls, and generate circular logistics strategies. **(Defence Call Ready)**")

# -----------------------------------------
# CONFIGURATION & SENSITIVITY ANALYSIS
# -----------------------------------------
with st.sidebar:
    st.header("🔑 Authentication")
    api_key = st.text_input("Enter Free Gemini API Key", type="password")
    
    st.header("🌍 GHG Protocol Emission Factors")
    # Updated to Tonne-km as promised in the Innovation Brief
    EMISSION_FACTOR_PER_TONNE_KM = st.number_input("kg CO2e per Tonne-km (Transit)", value=0.10, step=0.01)
    IDLING_FACTOR_PER_HR = st.number_input("kg CO2e per hour (Idling)", value=2.50, step=0.1)
    
    st.header("🎚️ Sensitivity Analysis")
    st.caption("Stress-test the network by artificially multiplying wait times.")
    stress_test_multiplier = st.slider("Idling Delay Multiplier", min_value=1.0, max_value=5.0, value=1.0, step=0.5)

# -----------------------------------------
# AI SCHEMA
# -----------------------------------------
class DecarbonizationStrategy(BaseModel):
    root_cause_hypothesis: str = Field(description="Explanation of why this specific bottleneck and dead-haul is occurring.")
    circular_back_haul_match: str = Field(description="Recommendation for circular logistics or back-haul matching.")
    scope_3_reduction_roadmap: str = Field(description="Step-by-step executive roadmap to reduce this specific carbon waste.")

# -----------------------------------------
# PDF EXPORT FUNCTION
# -----------------------------------------
def generate_pdf_report(bottleneck_text, total_waste, current_total, optimized_total, reduction_pct, ai_report):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Scope 3 Decarbonization & Bottleneck Audit", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Deterministic Mined Metrics (Baseline vs Optimized)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Current Scope 3 Baseline: {round(current_total, 2)} kg CO2e", ln=True)
    pdf.cell(0, 5, f"Optimized Emissions (Post-AI): {round(optimized_total, 2)} kg CO2e", ln=True)
    pdf.cell(0, 5, f"Projected Reduction: {round(reduction_pct, 2)}%", ln=True)
    pdf.cell(0, 5, f"Critical Carbon Bottleneck: {bottleneck_text.replace('➔', '->')}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. AI CSO Strategic Analysis", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    
    def safe_text(text):
        return text.encode('latin-1', 'replace').decode('latin-1')
        
    pdf.cell(0, 5, "Root Cause Hypothesis:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, safe_text(ai_report.root_cause_hypothesis))
    pdf.ln(3)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "Circular Back-Haul Recommendation:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, safe_text(ai_report.circular_back_haul_match))
    pdf.ln(3)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "Scope 3 Reduction Roadmap:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, safe_text(ai_report.scope_3_reduction_roadmap))
    
    return pdf.output(dest='S').encode('latin-1')

# -----------------------------------------
# DATA INGESTION & UI
# -----------------------------------------
st.subheader("1. Log Ingestion & Domain Context")
domain = st.selectbox("Select Industry Domain:", ["General Supply Chain", "Agriculture & Agri-Tech", "Healthcare & Pharma Logistics", "E-Commerce"])
uploaded_file = st.file_uploader("Upload Logistics Event Log (CSV)", type=["csv"])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file, encoding='latin-1')
    
    st.markdown("### Map Your Columns")
    cols = df_raw.columns.tolist()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        id_col = st.selectbox("Order / Case ID:", cols, index=0)
        dist_col = st.selectbox("Distance Travelled (km):", cols, index=3 if len(cols)>3 else 0)
    with c2:
        act_col = st.selectbox("Activity / Stage:", cols, index=1 if len(cols)>1 else 0)
        weight_col = st.selectbox("Load Weight (kg):", cols, index=4 if len(cols)>4 else 0)
    with c3:
        time_col = st.selectbox("Timestamp:", cols, index=2 if len(cols)>2 else 0)
        
    if st.button("Calculate Scope 3 Footprint & Mine Process", use_container_width=True):
        
        # -----------------------------------------
        # CRITICAL: UNPREPARED INPUT CRASH PROTECTION
        # -----------------------------------------
        try:
            with st.spinner("Executing deterministic math and stress-testing log data..."):
                df = df_raw.copy()
                
                # Sanitize Dates (Drops corrupt formats)
                df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
                df = df.dropna(subset=[time_col]).sort_values(by=[id_col, time_col])
                
                # Sanitize Numerics (Forces negatives to 0, handles text strings gracefully)
                df[dist_col] = pd.to_numeric(df[dist_col], errors='coerce').fillna(0).clip(lower=0)
                df[weight_col] = pd.to_numeric(df[weight_col], errors='coerce').fillna(0).clip(lower=0)

                # Force Activity column to string to prevent Graphviz float errors
                df[act_col] = df[act_col].astype(str)
                
                # -----------------------------------------
                # PANDAS MATH ENGINE (LAYER 1)
                # -----------------------------------------
                df["next_act"] = df.groupby(id_col)[act_col].shift(-1)
                df["next_time"] = df.groupby(id_col)[time_col].shift(-1)
                
                ## Apply Sensitivity Analysis Multiplier
                base_duration = (df["next_time"] - df[time_col]).dt.total_seconds() / 3600.0
                df["duration_hrs"] = (base_duration * stress_test_multiplier).fillna(0)
                
                # Dead-haul flag (empty return trips)
                df["is_dead_haul"] = np.where(df[weight_col] <= 0, 1, 0)
                
                # Payload-Weighted CO2e emissions (GHG Protocol Alignment)
                # FIX: Added 5000kg base vehicle tare weight so empty trucks still produce emissions
                gross_weight_tonnes = (df[weight_col] + 5000) / 1000.0
                df["co2_transit_kg"] = (df[dist_col] * gross_weight_tonnes) * EMISSION_FACTOR_PER_TONNE_KM
                df["co2_idling_kg"] = df["duration_hrs"] * IDLING_FACTOR_PER_HR
                df["total_co2_kg"] = df["co2_transit_kg"] + df["co2_idling_kg"]
                
                # Aggregate bottlenecks
                transitions = df.dropna(subset=["next_act"]).groupby([act_col, "next_act"]).agg(
                    avg_duration_hrs=("duration_hrs", "mean"),
                    total_co2_kg=("total_co2_kg", "sum"),
                    dead_haul_count=("is_dead_haul", "sum"),
                    total_trips=("duration_hrs", "count")
                ).reset_index()

                if transitions.empty:
                    st.error("No valid transitions found. Ensure your data has sequential timestamps for IDs.")
                else:
                    bottleneck = transitions.loc[transitions['total_co2_kg'].idxmax()]
                    bottleneck_str = f"{str(bottleneck[act_col])} ➔ {str(bottleneck['next_act'])}"
                    
                    # -----------------------------------------
                    # BASELINE VS OPTIMIZED UI (PROOF OF VALUE)
                    # -----------------------------------------
                    current_total_co2 = df["total_co2_kg"].sum()
                    dead_haul_emissions = df[df["is_dead_haul"] == 1]["total_co2_kg"].sum()
                    optimized_co2 = current_total_co2 - dead_haul_emissions
                    reduction_pct = (dead_haul_emissions / current_total_co2) * 100 if current_total_co2 > 0 else 0

                    st.success("✅ Deterministic Scope 3 Arithmetic Complete! Data sanitized successfully.")
                    
                    st.markdown("---")
                    st.subheader("⚖️ Baseline vs. Optimized Projection")
                    
                    b1, b2, b3 = st.columns(3)
                    b1.metric("Current Scope 3 Emissions (Baseline)", f"{round(current_total_co2, 1)} kg")
                    b2.metric("Optimized Emissions (Post-AI)", f"{round(optimized_co2, 1)} kg", f"-{round(dead_haul_emissions, 1)} kg", delta_color="inverse")
                    b3.metric("Projected Carbon Reduction", f"{round(reduction_pct, 1)}%")

                    # -----------------------------------------
                    # REAL-WORLD DATA HOOK (NABCONS)
                    # -----------------------------------------
                    if domain == "Agriculture & Agri-Tech" and bottleneck['avg_duration_hrs'] > 10:
                        st.error(f"🚨 **Real-World Risk Alert:** Based on NABCONS 2022 benchmarks, this {round(bottleneck['avg_duration_hrs'], 1)}-hour staging delay introduces an estimated 11.6% post-harvest spoilage risk for perishable crops.")

                    st.markdown("---")
                    st.subheader("📊 Mined Carbon Metrics")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Worst Carbon Bottleneck", bottleneck_str)
                    m2.metric("Total CO2e Wasted at Bottleneck", f"{round(bottleneck['total_co2_kg'], 1)} kg")
                    m3.metric("Dead-Haul Legs Flagged", int(bottleneck['dead_haul_count']))
                    
                    # -----------------------------------------
                    # VISUALIZATIONS
                    # -----------------------------------------
                    col_chart, col_graph = st.columns(2)
                    
                    with col_chart:
                        st.write("**Top Carbon-Intensity Transitions**")
                        top_co2 = transitions.sort_values(by='total_co2_kg', ascending=False).head(5).copy()
                        top_co2['Transition'] = top_co2[act_col].astype(str) + " ➔ " + top_co2['next_act'].astype(str)
                        fig = px.bar(top_co2, x='total_co2_kg', y='Transition', orientation='h', color='total_co2_kg', color_continuous_scale='Reds')
                        fig.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig, use_container_width=True)

                    with col_graph:
                        st.write("**Carbon-Weighted Process Map**")
                        dot = graphviz.Digraph()
                        dot.attr(rankdir='TB', size='4,4')
                        for _, row in transitions[transitions['total_trips'] >= (transitions['total_trips'].max() * 0.1)].iterrows():
                            dot.edge(str(row[act_col]), str(row['next_act']), label=f"{round(row['total_co2_kg'], 1)} kg CO2e")
                        st.graphviz_chart(dot)

                    # -----------------------------------------
                    # AI CSO CONSULTANT (LAYER 2)
                    # -----------------------------------------
                    st.markdown("---")
                    st.subheader("🤖 AI Sustainability Consultant (CSO)")
                    
                    if not api_key:
                        st.warning("⚠️ Enter Gemini API Key in the sidebar to generate the AI strategy.")
                    else:
                        with st.spinner("Gemini is analyzing deterministic carbon metrics..."):
                            client = genai.Client(api_key=api_key)
                            prompt = f"""
                            You are a Chief Sustainability Officer (CSO) operating in the {domain} sector. 
                            Here is the deterministic data for our worst carbon bottleneck:
                            - Transition: '{bottleneck[act_col]}' to '{bottleneck['next_act']}'
                            - Total CO2e Emitted here: {round(bottleneck['total_co2_kg'], 1)} kg
                            - Empty Dead-Haul Returns: {bottleneck['dead_haul_count']} out of {bottleneck['total_trips']} total trips.
                            - Average Waiting/Idling Time: {round(bottleneck['avg_duration_hrs'], 1)} hours.
                            
                            Provide a highly actionable, structured JSON strategy targeting this exact bottleneck.
                            """
                            
                            try:
                                response = client.models.generate_content(
                                    model='gemini-3.5-flash-lite',
                                    contents=prompt,
                                    config=types.GenerateContentConfig(
                                        response_mime_type="application/json",
                                        response_schema=DecarbonizationStrategy
                                    )
                                )
                                
                                ai_report = DecarbonizationStrategy(**json.loads(response.text))
                                
                                st.error(f"**Root Cause Hypothesis 🔍**\n\n{ai_report.root_cause_hypothesis}")
                                st.success(f"**Circular Back-Haul Match 🔄**\n\n{ai_report.circular_back_haul_match}")
                                st.info(f"**Scope 3 Reduction Roadmap 🗺️**\n\n{ai_report.scope_3_reduction_roadmap}")
                                
                                # PDF Export includes Baseline vs Optimized data
                                pdf_bytes = generate_pdf_report(
                                    bottleneck_str, bottleneck['total_co2_kg'], 
                                    current_total_co2, optimized_co2, reduction_pct, ai_report
                                )
                                st.download_button(
                                    label="📄 Download Executive Scope 3 Decarbonization PDF Audit",
                                    data=pdf_bytes,
                                    file_name="Scope3_Executive_Audit.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"AI Generation Error: {e}")

        # Catches any fatal errors from completely unreadable inputs during the defence call
        except Exception as e:
            st.error(f"❌ **Data Processing Error:** The uploaded file structure is invalid or corrupt. Please ensure it contains sequential tracking IDs and valid numerics. (System Log: {e})")