"""Streamlit interface:  streamlit run app.py"""
from pathlib import Path

import streamlit as st

from citecheck import check_answer, summarize

HERE = Path(__file__).parent
COLORS = {"Supported": "#1b7f4b", "Partly supported": "#b7791f",
          "Possible contradiction": "#c05621", "Unsupported": "#c53030"}

st.set_page_config(page_title="Citation Checker", page_icon="🔎", layout="wide")
st.title("Citation Checker")
st.caption("Paste an AI answer and the source text it relied on. Each claim is "
           "matched to the closest passage and labelled. This checks wording "
           "overlap, not meaning, so treat it as a first pass and read the "
           "matched passage yourself.")

if st.button("Load example"):
    st.session_state["answer"] = (HERE / "examples/sample_answer.txt").read_text()
    st.session_state["source"] = (HERE / "examples/bees.txt").read_text()

left, right = st.columns(2)
answer = left.text_area("AI answer", key="answer", height=240)
source = right.text_area("Source text", key="source", height=240,
                         help="Paste one source. Several sources: separate "
                              "them with a line containing only ---")

if st.button("Check claims", type="primary"):
    if not answer.strip() or not source.strip():
        st.warning("Add both an answer and a source.")
    else:
        parts = [p.strip() for p in source.split("\n---\n") if p.strip()]
        sources = {f"Source {i + 1}": t for i, t in enumerate(parts)}
        results = check_answer(answer, sources)
        counts = summarize(results)
        cols = st.columns(4)
        for col, (label, n) in zip(cols, counts.items()):
            col.metric(label, n)
        for r in results:
            color = COLORS[r.label]
            st.markdown(
                f"<div style='border-left:6px solid {color};padding:6px 12px;"
                f"margin:10px 0'><b style='color:{color}'>{r.label}</b> "
                f"(overlap {r.coverage:.2f})<br>{r.claim}</div>",
                unsafe_allow_html=True)
            if r.passage and r.coverage >= 0.3:
                st.caption(f"Closest passage ({r.source}): {r.passage}")
            for why in r.reasons:
                st.caption(f"Note: {why}")
