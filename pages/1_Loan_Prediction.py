import streamlit as st

import api_client
import ui

ui.setup_page("Loan Prediction")
ui.page_header("Loan", "Prediction", "Enter applicant details; the saved Decision Tree model scores them through the API")

pre = st.session_state.pop("prefill", {})  # set by the dashboard's quick form
TERMS = [12, 24, 36, 48, 60, 84, 120, 180, 240]

with st.form("loan_form"):
    st.subheader("Applicant Information")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, int(pre.get("age", 30)), step=1)
    annual_income = c2.number_input("Annual Income (₹)", 1.0, 1e10, float(pre.get("annual_income", 600000.0)), step=10000.0, format="%.2f")
    credit_score = c1.number_input("Credit Score", 300, 900, int(pre.get("credit_score", 700)), step=1)
    employment_years = c2.number_input("Employment Years", 0, 60, int(pre.get("employment_years", 5)), step=1)
    dependents = c1.number_input("Dependents", 0, 20, 0, step=1)
    previous_defaults = c2.number_input("Previous Defaults", 0, 50, 0, step=1)
    savings = c1.number_input("Savings (₹)", 0.0, 1e10, 200000.0, step=5000.0, format="%.2f")
    assets = c2.number_input("Assets (₹)", 0.0, 1e11, 500000.0, step=10000.0, format="%.2f")

    st.subheader("Loan & Existing Obligations")
    c3, c4 = st.columns(2)
    loan_amount = c3.number_input("Requested Loan Amount (₹)", 1.0, 1e10, float(pre.get("loan_amount", 300000.0)), step=10000.0, format="%.2f")
    default_term = pre.get("loan_term", 60)
    loan_term = c4.selectbox("Loan Term (months)", TERMS, index=TERMS.index(default_term) if default_term in TERMS else 4)
    existing_loans = c3.number_input("Existing Loans", 0, 50, 0, step=1)
    existing_loan_amount = c4.number_input("Existing Loan Amount (₹)", 0.0, 1e10, 0.0, step=5000.0, format="%.2f")
    monthly_emi = c3.number_input("Monthly EMI (₹)", 0.0, 1e9, 0.0, step=500.0, format="%.2f")
    submitted = st.form_submit_button("✨ Analyze Application →", use_container_width=True)

if submitted:
    payload = dict(age=age, annual_income=annual_income, credit_score=credit_score, loan_amount=loan_amount,
                   loan_term=loan_term, existing_loans=existing_loans, existing_loan_amount=existing_loan_amount,
                   monthly_emi=monthly_emi, dependents=dependents, savings=savings,
                   employment_years=employment_years, previous_defaults=previous_defaults, assets=assets)
    # light client-side sanity checks (the backend remains the authority)
    problems = []
    if existing_loans == 0 and existing_loan_amount > 0:
        problems.append("Existing Loan Amount is greater than 0 but Existing Loans is 0.")
    if existing_loans > 0 and existing_loan_amount == 0:
        st.warning("Existing Loans is above 0 but Existing Loan Amount is 0 - please double-check.")
    if problems:
        for p in problems:
            st.error(p)
    else:
        try:
            with st.spinner("Analyzing application..."):
                st.session_state["last_result"] = api_client.predict(payload)
        except api_client.ApiError as exc:
            st.session_state.pop("last_result", None)
            ui.api_error(exc)

res = st.session_state.get("last_result")
if res:
    approved = res["prediction"] == 1
    cls, icon = ("res-ok", "✅") if approved else ("res-bad", "❌")
    word = "MODEL PREDICTION: APPROVE" if approved else "MODEL PREDICTION: REJECT"
    st.write("")
    ui.html(f'<div class="res-card {cls}"><div class="big">{icon} {word}</div>'
            f'<div class="ref">Application reference: <b>{res["application_id"]}</b> · {res["created_at"][:19].replace("T", " ")} UTC '
            f'· model {res["model_version"]}</div></div>')
    st.write("")
    a, b = st.columns(2)
    a.metric("Approval Probability", f'{res["approval_probability"]*100:.2f}%')
    b.metric("Rejection Probability", f'{res["rejection_probability"]*100:.2f}%')
    st.progress(min(max(res["approval_probability"], 0.0), 1.0))
    r = res["ratios"]
    d, e, f = st.columns(3)
    d.metric("Debt-to-Income (DTI)", f'{r["dti"]:.3f}')
    e.metric("Loan-to-Income Ratio", f'{r["loan_income_ratio"]:.3f}')
    f.metric("Savings-to-Loan Ratio", f'{r["savings_loan_ratio"]:.3f}')

    if res["storage"]["saved"]:
        st.success(res["storage"]["message"], icon="💾")
    else:
        st.warning(res["storage"]["message"], icon="⚠️")
    for w in res.get("warnings", []):
        st.warning(w, icon="📏")
    with st.expander("🔎 View the exact 16 values sent to the model"):
        st.dataframe({"Value": res["model_features"]}, use_container_width=True)
    ui.html(f'<div class="lid-note">{res["disclaimer"]} A "predict approve" result is a statistical output of a demo model, '
            'not a guarantee that any lender would approve this loan.</div>')
