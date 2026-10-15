"""Dashboard (home page). Run with: streamlit run app.py"""
import plotly.graph_objects as go
import streamlit as st

import api_client
import ui

ui.setup_page("Dashboard")

days = st.session_state.get("trend_days", 7)
try:
    stats = api_client.get_analytics(days=days)
except api_client.ApiError as exc:
    ui.page_header("Loan Intelligence", "Dashboard", "AI-powered loan risk assessment • Decision Tree model")
    ui.api_error(exc)
    st.stop()

try:
    info = api_client.get_model_info()
except api_client.ApiError:
    info = None

total = stats["total"]
if stats["seeded_count"] > 0:
    pill = "INCLUDES SEEDED DEMO DATA"
elif total == 0:
    pill = "NO PREDICTIONS YET"
else:
    pill = "LIVE DATA"
ui.page_header("Loan Intelligence", "Dashboard", "AI-powered loan risk assessment • Decision Tree model", pill)

# ---- KPI cards (all values come from stored records / the training evaluation) -------------
recent = sum(d["applications"] for d in stats["trend"])
acc = (info or {}).get("metrics", {}) or {}
acc_val = f'{acc["accuracy"]*100:.1f}%' if "accuracy" in acc else "N/A"
c1, c2, c3, c4 = st.columns(4)
with c1:
    ui.kpi_card("Total Predictions", f"{total:,}", f"{recent:,} in the last {days} days", "teal", "👥")
with c2:
    rate = stats["approval_rate"]
    ui.kpi_card("Approval Rate", f"{rate:.1f}%" if rate is not None else "—", f'{stats["approved"]:,} approved', "green", "✅")
with c3:
    share = f'{100*stats["rejected"]/total:.1f}% of predictions' if total else "No data yet"
    ui.kpi_card("Rejected", f'{stats["rejected"]:,}', share, "red", "❌")
with c4:
    ui.kpi_card("Model Accuracy", acc_val, "Held-out test set (synthetic labels)", "blue", "📈")

st.write("")
left, right = st.columns([2, 1])
with left:
    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        with h1:
            ui.card_title("Application Trends", f"Predictions and approvals in the last {days} days")
        with h2:
            st.selectbox("Period", [7, 14, 30], key="trend_days", format_func=lambda d: f"Last {d} Days",
                         label_visibility="collapsed")
        if total == 0:
            ui.empty_state("No predictions yet", "Submit an application on the Loan Prediction page.")
        else:
            t = stats["trend"]
            x = [d["date"] for d in t]
            fig = go.Figure()
            fig.add_scatter(x=x, y=[d["applications"] for d in t], name="Applications", mode="lines+markers",
                            line=dict(color=ui.BLUE, width=3), fill="tozeroy", fillcolor="rgba(47,140,255,0.15)")
            fig.add_scatter(x=x, y=[d["approved"] for d in t], name="Approved", mode="lines+markers",
                            line=dict(color=ui.GREEN, width=3), fill="tozeroy", fillcolor="rgba(16,212,142,0.12)")
            st.plotly_chart(ui.style_fig(fig), use_container_width=True)
with right:
    with st.container(border=True):
        ui.card_title("Prediction Distribution", "Overall prediction results")
        if total == 0:
            ui.empty_state("Nothing to show yet")
        else:
            fig = go.Figure(go.Pie(labels=["Approved", "Rejected"], values=[stats["approved"], stats["rejected"]],
                                   hole=0.72, marker=dict(colors=[ui.GREEN, ui.RED]), textinfo="none", sort=False))
            fig.add_annotation(text=f"<b>{total:,}</b><br>Total", showarrow=False, font=dict(size=20, color="#fff"))
            st.plotly_chart(ui.style_fig(fig, 300), use_container_width=True)
            st.caption(f'🟢 Approved {stats["approved"]:,} ({stats["approval_rate"]:.1f}%)  ·  '
                       f'🔴 Rejected {stats["rejected"]:,} ({100 - stats["approval_rate"]:.1f}%)')

st.write("")
left, right = st.columns([3, 2])
with left:
    with st.form("quick_form"):
        ui.card_title("Quick Loan Prediction", "Enter key details, then complete the remaining fields on the next page")
        a, b = st.columns(2)
        age = a.number_input("Age", 18, 100, 30)
        loan_amount = b.number_input("Requested Loan Amount (₹)", 1.0, 1e10, 300000.0, step=10000.0, format="%.0f")
        income = a.number_input("Annual Income (₹)", 1.0, 1e10, 600000.0, step=10000.0, format="%.0f")
        term = b.selectbox("Loan Term (Months)", [12, 24, 36, 48, 60, 84, 120, 180, 240], index=4)
        score = a.number_input("Credit Score", 300, 900, 720)
        years = b.number_input("Employment Years", 0, 60, 5)
        if st.form_submit_button("✨ Analyze Application →", use_container_width=True):
            st.session_state["prefill"] = dict(age=age, loan_amount=loan_amount, annual_income=income,
                                               loan_term=term, credit_score=score, employment_years=years)
            st.switch_page("pages/1_Loan_Prediction.py")
with right:
    with st.container(border=True):
        ui.card_title("Model Insights", "Top features used by the Decision Tree")
        if info:
            ui.feature_bars(info["feature_importances"])
            st.caption("From model.feature_importances_. Not causal.")
        else:
            ui.empty_state("Model information unavailable")

if stats["seeded_count"]:
    st.caption(f'ℹ️ {stats["seeded_count"]} of {total} records were seeded with scripts/seed_demo.py '
               "(real model predictions on rows from the synthetic dataset, backdated for the trend chart).")
