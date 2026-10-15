import pandas as pd
import plotly.express as px
import streamlit as st

import api_client
import ui

ui.setup_page("Model Insights")
ui.page_header("Model", "Insights", "How the Decision Tree behaves - from the saved model and its real evaluation")

try:
    info = api_client.get_model_info()
except api_client.ApiError as exc:
    ui.api_error(exc)
    st.stop()

hp = info["hyperparameters"]
with st.container(border=True):
    ui.card_title("About the model", f'{info["model_type"]} · version {info["model_version"]}')
    st.write(f'A Decision Tree learns a sequence of yes/no questions about the applicant (for example "is credit score above X?") '
             f'and ends in a leaf that gives the approve/reject class and its probability. This tree has depth {info["depth"]} '
             f'(max_depth={hp["max_depth"]}), {info["n_leaves"]} leaves, min_samples_leaf={hp["min_samples_leaf"]}, '
             f'and uses {len(info["feature_names"])} input features.')

m = info.get("metrics")
st.write("")
if m:
    a, b, c, d = st.columns(4)
    with a: ui.kpi_card("Accuracy", f'{m["accuracy"]*100:.1f}%', f'{m["test_size"]:,} held-out test rows', "blue", "🎯")
    ap, rj = m["per_class"]["approved"], m["per_class"]["rejected"]
    with b: ui.kpi_card("Approved: Precision / Recall", f'{ap["precision"]:.2f} / {ap["recall"]:.2f}', f'F1 {ap["f1-score"]:.2f}', "green", "✅")
    with c: ui.kpi_card("Rejected: Precision / Recall", f'{rj["precision"]:.2f} / {rj["recall"]:.2f}', f'F1 {rj["f1-score"]:.2f}', "red", "❌")
    with d: ui.kpi_card("Training rows", f'{m["train_size"]:,}', "80/20 stratified split", "teal", "🧪")
    st.write("")
    cm = pd.DataFrame(m["confusion_matrix"], index=["Actual: Rejected", "Actual: Approved"], columns=["Predicted: Rejected", "Predicted: Approved"])
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.container(border=True):
            ui.card_title("Confusion matrix", "Held-out test set")
            fig = px.imshow(cm, text_auto=True, color_continuous_scale=["#0C1C31", ui.TEAL], aspect="auto")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(ui.style_fig(fig, 300), use_container_width=True)
    with c2:
        with st.container(border=True):
            ui.card_title("Important caveat")
            st.warning(m["label_note"], icon="⚠️")
            st.caption(f'Metrics source: {m.get("provenance", "model/metrics.json")}')
else:
    st.info("No evaluation metrics found. Run `python model/train_model.py` to generate model/metrics.json. "
            "No accuracy figure is shown because none has been verified.")

imp = pd.Series(info["feature_importances"]).sort_values()
st.write("")
with st.container(border=True):
    ui.card_title("Feature importance", "From model.feature_importances_ (sums to 100%)")
    fig = px.bar(x=imp.values * 100, y=[ui.pretty(i) for i in imp.index], orientation="h",
                 color_discrete_sequence=[ui.TEAL], labels={"x": "Importance (%)", "y": ""})
    st.plotly_chart(ui.style_fig(fig, 480), use_container_width=True)
    zero = [ui.pretty(k) for k, v in info["feature_importances"].items() if v == 0]
    if zero:
        st.caption("Features the tree never split on (importance 0): " + ", ".join(zero) + ".")

MEANING = {
    "credit_score": "Creditworthiness score (300-900). Higher generally means lower perceived risk.",
    "loan_income_ratio": "Requested loan ÷ annual income. How large the loan is relative to earnings.",
    "dti": "Existing loan amount ÷ annual income. Existing debt burden.",
    "previous_defaults": "Number of earlier loan defaults.",
    "savings_loan_ratio": "Savings ÷ requested loan. Cushion available against the loan.",
    "employment_years": "Years in employment - a proxy for income stability.",
    "monthly_emi": "Current monthly instalment payments.",
}
rows = [{"Feature": ui.pretty(k), "Importance": f"{v*100:.1f}%", "Meaning": MEANING.get(k, "-")}
        for k, v in sorted(info["feature_importances"].items(), key=lambda kv: -kv[1]) if v > 0]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
ui.html('<div class="lid-note"><b>Feature importance is not causation.</b> It shows which inputs the tree used to split the '
        'training data, not that changing an input would change a real lender’s decision. The training labels are synthetic '
        '(a hand-written point system plus noise), so this model has not been validated for real banking decisions.</div>')
