import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import api_client
import ui

ui.setup_page("Analytics")
ui.page_header("Prediction", "Analytics", "Statistics computed from stored prediction records")

days = st.selectbox("Trend window", [7, 14, 30, 90], format_func=lambda d: f"Last {d} days")
try:
    with st.spinner("Loading analytics..."):
        s = api_client.get_analytics(days=days)
except api_client.ApiError as exc:
    ui.api_error(exc)
    st.stop()

if s["total"] == 0:
    ui.empty_state("No prediction records yet", "Analytics appear after the first prediction is saved.")
    st.stop()

a, b, c, d = st.columns(4)
with a: ui.kpi_card("Total Predictions", f'{s["total"]:,}', "All stored records", "teal", "👥")
with b: ui.kpi_card("Approved", f'{s["approved"]:,}', "Model predicted approve", "green", "✅")
with c: ui.kpi_card("Rejected", f'{s["rejected"]:,}', "Model predicted reject", "red", "❌")
with d: ui.kpi_card("Approval Percentage", f'{s["approval_rate"]:.1f}%', "Approved / total", "blue", "📈")
st.write("")

with st.container(border=True):
    ui.card_title("Prediction Trends", f"Daily predictions over the last {days} days (UTC)")
    t = s["trend"]
    x = [r["date"] for r in t]
    fig = go.Figure()
    fig.add_bar(x=x, y=[r["approved"] for r in t], name="Approved", marker_color=ui.GREEN)
    fig.add_bar(x=x, y=[r["rejected"] for r in t], name="Rejected", marker_color=ui.RED)
    fig.update_layout(barmode="stack")
    st.plotly_chart(ui.style_fig(fig), use_container_width=True)

dist = s["distributions"]
c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        ui.card_title("Loan Amount Distribution", "Requested loan amounts (₹)")
        fig = px.histogram(x=dist["loan_amount"], nbins=20, color_discrete_sequence=[ui.TEAL], labels={"x": "Loan amount (₹)"})
        st.plotly_chart(ui.style_fig(fig, 300), use_container_width=True)
with c2:
    with st.container(border=True):
        ui.card_title("Credit Score Distribution", "Applicant credit scores")
        fig = px.histogram(x=dist["credit_score"], nbins=20, color_discrete_sequence=[ui.BLUE], labels={"x": "Credit score"})
        st.plotly_chart(ui.style_fig(fig, 300), use_container_width=True)
with st.container(border=True):
    ui.card_title("Loan Term Distribution", "Number of applications per term (months)")
    terms = dist["loan_term"]
    fig = px.bar(x=list(terms.keys()), y=list(terms.values()), color_discrete_sequence=[ui.PURPLE],
                 labels={"x": "Term (months)", "y": "Applications"})
    fig.update_xaxes(type="category")
    st.plotly_chart(ui.style_fig(fig, 300), use_container_width=True)
if s["seeded_count"]:
    st.caption(f'ℹ️ {s["seeded_count"]} records were created by scripts/seed_demo.py (synthetic dataset rows scored by the real model).')
