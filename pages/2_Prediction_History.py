import pandas as pd
import streamlit as st

import api_client
import ui

ui.setup_page("Prediction History")
ui.page_header("Prediction", "History", "Predictions stored in MongoDB, newest first")

f1, f2, f3, f4 = st.columns([3, 2, 1.3, 1])
search = f1.text_input("Search by Application ID", placeholder="e.g. LID-20261009")
status_label = f2.selectbox("Outcome", ["All", "Approved", "Rejected"])
page_size = f3.selectbox("Rows per page", [10, 25, 50], index=0)
f4.write("")
f4.button("🔄 Refresh", use_container_width=True)  # any click triggers a rerun, which re-fetches

page = st.session_state.get("hist_page", 1)
status = None if status_label == "All" else status_label.lower()
try:
    with st.spinner("Loading history..."):
        data = api_client.get_history(page=page, page_size=page_size, status=status, search=search.strip() or None)
except api_client.ApiError as exc:
    ui.api_error(exc)
    st.stop()

if data["total"] > 0 and not data["items"] and page > 1:  # filters changed and the old page no longer exists
    st.session_state["hist_page"] = 1
    st.rerun()

if data["total"] == 0:
    ui.empty_state("No matching predictions", "Run an analysis on the Loan Prediction page, or clear the filters.")
    st.stop()

df = pd.DataFrame(data["items"])
df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M UTC")
df["approval_probability"] = df["approval_probability"] * 100
df = df.rename(columns={"application_id": "Application ID", "created_at": "Date & Time", "loan_amount": "Loan Amount (₹)",
                        "credit_score": "Credit Score", "loan_term": "Term (months)", "prediction_label": "Outcome",
                        "approval_probability": "Approval Probability"})
st.dataframe(df, use_container_width=True, hide_index=True, column_config={
    "Loan Amount (₹)": st.column_config.NumberColumn(format="%.0f"),
    "Approval Probability": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
})

p1, p2, p3 = st.columns([1, 2, 1])
if p1.button("← Previous", disabled=page <= 1):
    st.session_state["hist_page"] = page - 1
    st.rerun()
p2.markdown(f"<div style='text-align:center;color:#8CA3BD'>Page {data['page']} of {data['total_pages']} · "
            f"{data['total']:,} records</div>", unsafe_allow_html=True)
if p3.button("Next →", disabled=page >= data["total_pages"]):
    st.session_state["hist_page"] = page + 1
    st.rerun()

st.download_button("⬇️ Download this page as CSV", df.to_csv(index=False).encode("utf-8"),
                   file_name="prediction_history.csv", mime="text/csv")
