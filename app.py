import streamlit as st
import pandas as pd
from agent.core import react_agent
import json

# --- Page config ---
# Must be the first Streamlit call in the file
st.set_page_config(
    page_title="Open Bus Agent",
    page_icon="🚌",
    layout="wide",
)

# --- Example questions shown in the sidebar ---
EXAMPLES = [
    "What is the first stop of line 189?",
    "What is the first stop of line 480?",
    "How many rides does line 19 have between 07:00 and 08:00 on Jan 1, 2023?",
    "How many rides does line 18 have on Jan 1, 2023?",
    "Show the first 5 stops of line 189 on a map",
]

# --- Things the agent cannot answer ---
CANNOT = [
    "Real-time delay — data often unmatched / unreliable",
    "Passenger counts / occupancy — not in Open Bus",
    "Long time ranges — exceed the token limit",
]

# --- Sidebar ---
with st.sidebar:
    st.header("Open Bus Agent 🚍")
    st.caption("Ask questions about Israeli public transport using the STRIDE API.")

    st.markdown("### Example questions")
    # Each button loads its question into the input box
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state["question"] = example

    st.divider()

    st.markdown("### Out of scope")
    for item in CANNOT:
        st.caption(f"• {item}")

# --- Main area ---
st.title("Open Bus Agent")
st.caption("Ask in plain language about stops, ride counts, and bus locations.")

# The text input — pre-filled if an example button was clicked
question = st.text_input(
    label="Your question",
    value=st.session_state.get("question", ""),
    placeholder="e.g. What is the first stop of line 189?",
)
run = st.button("Run", type="primary")

# --- Agent execution ---
if run and question.strip():

    # Clear any previous question from session state
    st.session_state["question"] = ""

    # Placeholders let us update the same spot in the UI as the agent runs
    status_placeholder = st.empty()
    log_placeholder = st.empty()

    final_answer = None
    final_coords = []
    final_log = []

    # Consume the generator — each yield updates the UI
    for update in react_agent(question):
        final_log = update.get("log", [])
        final_coords = update.get("coords", [])

        # Update the status line
        if update["status"] == "calling":
            status_placeholder.info(f"⚙️ Calling **{update['tool']}**...")
        elif update["status"] == "step":
            status_placeholder.info(f"✅ {len(final_log)} step(s) done, thinking...")
        elif update["status"] == "retry":
            status_placeholder.warning("⟳ Retrying...")

        # Update the live log expander
        with log_placeholder.container():
            with st.expander("Agent steps", expanded=True):
                for i, step in enumerate(final_log, 1):
                    if step["type"] == "retry":
                        st.warning(f"{i}. ⟳ {step['text']}")
                    else:
                        st.markdown(f"**{i}. {step['tool']}**")
                        st.code(json.dumps(step["args"], ensure_ascii=False), language="json")
                        st.text(step["observation"])

    # --- Final answer ---
    status_placeholder.success("✅ Done")
    final_answer = update.get("answer")

    st.subheader("Answer")
    st.write(final_answer)

    # --- Map (only shown if the agent returned coordinates) ---
    if final_coords:
        st.subheader("Map")
        df = pd.DataFrame(final_coords)
        st.map(df[["lat", "lon"]])

        with st.expander("Map points"):
            st.dataframe(df, use_container_width=True)