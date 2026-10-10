# Scope 3 ESG Process Agent

An autonomous process mining tool that ingests unstandardized logistics logs to deterministically calculate Scope 3 emissions and generate AI-driven back-haul strategies to eliminate zero-load return trips.

## The Problem
Logistics networks suffer from uncoordinated return trips (dead-hauls), where empty trucks return to hubs, burning fuel without generating business value. Tracking and eliminating these dead-haul emissions is a massive challenge due to siloed tracking data and a lack of dynamic back-haul pooling. 

## What This Does
The system takes an unstandardized logistics event log (CSV) as input. It automatically sanitizes the data, mathematically flags empty return trips, and outputs a GHG Protocol-aligned Scope 3 footprint. It then uses an AI agent to generate a circular logistics strategy to eliminate the flagged dead-hauls.

## Example
**Input:** `DataCo_With_DeadHauls.csv` (180,000+ rows)
**Action:** Map Activity to `Delivery Status` and Weight to `Order Item Quantity`.
**Output:** 
- Current Scope 3 Emissions: 4,130,910.5 kg
- Projected Carbon Reduction: ~30.0% (By eliminating 36,000+ flagged empty return legs)
- AI Strategy: "Implement a dynamic slot-booking system combined with regional back-haul pooling."

## How It Works
We built a robust three-layer architecture:
1. **Deterministic Engine (Pandas):** Cleans unprepared data (`errors='coerce'`), calculates payload-weighted Tonne-km emissions, and explicitly catches missing data.
2. **Qualitative AI (Google Gemini API):** Analyzes the mathematically derived bottlenecks to recommend physical supply chain interventions.
3. **Audit Reporting (FPDF):** Packages the baseline metrics and AI strategy into an automated PDF.

## Data
We utilize the **DataCo Smart Supply Chain** dataset. 
*Note on Data Generation:* Because the original dataset only tracks outbound sales (no zero-weight return trips exist), we wrote a Python script (`inject_deadhauls.py`) to synthetically generate empty return trips for 20% of the orders. This simulates real-world dead-hauls to demonstrate the AI optimization engine.

## Installation
```bash
git clone https://github.com/rahilratan06/scope-3-esg-agent.git
cd scope-3-esg-agentcd YOUR_REPOSITORY_NAME
pip install -r requirements.txt