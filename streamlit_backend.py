import streamlit as st
import os
import json
from pathlib import Path
from datetime import datetime

# Import existing RAG components (assuming they are in the python path)
# from orchestrator import Orchestrator
# from ingestion.fetcher import run_fetch_phase

st.set_page_config(
    page_title="RAG Backend Orchestrator",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ RAG Backend Orchestrator")
st.markdown("### Mutual Fund FAQ Assistant - Management Dashboard")

tabs = st.tabs(["Dashboard", "Ingestion Status", "Query Logs", "Configuration"])

with tabs[0]:
    st.header("System Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Documents", "7")
    col2.metric("Last Sync", "Today 10:00 AM")
    col3.metric("System Health", "Healthy", delta="Operational")
    
    st.info("The frontend is currently served via **Vercel Edge** and communicates with this backend for real-time RAG processing.")

with tabs[1]:
    st.header("Ingestion Pipeline")
    if st.button("Trigger Manual Sync"):
        with st.spinner("Running ingestion pipeline..."):
            # result = run_fetch_phase()
            st.success("Ingestion complete!")
            st.json({"status": "success", "processed_urls": 7})

with tabs[2]:
    st.header("Recent Queries")
    # This would normally load from SQLite or JSON logs
    st.table([
        {"Time": "20:30:05", "Query": "What is the NAV of small cap fund?", "Status": "Factual"},
        {"Time": "20:31:12", "Query": "Should I invest in gold?", "Status": "Refused (Advisory)"}
    ])

with tabs[3]:
    st.header("Configuration")
    config_path = Path("data/config.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            config_data = json.load(f)
        
        updated_config = st.text_area("Edit fund_urls (JSON)", json.dumps(config_data, indent=2), height=300)
        if st.button("Save Configuration"):
            try:
                json.loads(updated_config)
                with open(config_path, "w") as f:
                    f.write(updated_config)
                st.success("Configuration saved! This will trigger a GitHub Action if pushed.")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
