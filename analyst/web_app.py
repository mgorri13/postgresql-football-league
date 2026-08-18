import streamlit as st

from main import graph


st.set_page_config(
    page_title="Football Database Analyst",
    page_icon="⚽",
    layout="centered",
)

WORKFLOW_DOT = """
digraph workflow {
    graph [
        rankdir=LR,
        bgcolor="transparent",
        pad="0.2",
        nodesep="0.45",
        ranksep="0.65"
    ];

    node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=11,
        color="#2B6CB0",
        fillcolor="#EBF8FF",
        margin="0.18,0.10"
    ];

    edge [
        fontname="Helvetica",
        fontsize=9,
        color="#4A5568"
    ];

    start [
        label="User question",
        shape=oval,
        fillcolor="#E6FFFA",
        color="#2C7A7B"
    ];

    normalise [label="1. Normalise question\\nPython"];
    assess [label="2. Assess question\\nLLM"];
    clarify [label="Ask for clarification\\nPython"];
    generate [label="3. Generate SQL\\nLLM"];
    validate [label="4. Validate SQL\\nSQLGlot / Python"];
    execute [label="5. Execute SQL\\nPostgreSQL / Python"];
    repair [label="Repair SQL\\nLLM"];
    explain [label="6. Explain results\\nLLM"];
    validation_failure [label="Report validation failure\\nPython"];
    query_failure [label="Report query failure\\nPython"];

    end [
        label="Answer shown to user",
        shape=oval,
        fillcolor="#E6FFFA",
        color="#2C7A7B"
    ];

    start -> normalise;
    normalise -> assess;

    assess -> clarify [label=" ambiguous"];
    clarify -> end;

    assess -> generate [label=" clear"];
    generate -> validate;

    validate -> execute [label=" valid"];
    validate -> repair [label=" invalid, retry available"];
    validate -> validation_failure [label=" invalid, no retries"];

    execute -> explain [label=" success"];
    execute -> repair [label=" database error, retry available"];
    execute -> query_failure [label=" error, no retries"];

    repair -> validate;
    explain -> end;
    validation_failure -> end;
    query_failure -> end;
}
"""


def add_message(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


def ask_graph(question: str) -> dict:
    with st.spinner("Checking the question and analysing the football database..."):
        return graph.invoke({"question": question})


if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


with st.sidebar:
    st.header("About this project")
    st.write(
        "Ask questions about the football league database in normal language."
    )
    st.caption(
        "The app generates SQL, validates it, runs a safe read-only query, "
        "and explains the returned data."
    )

    st.divider()

    st.subheader("Example questions")
    st.markdown(
        """
        - Who are the five top scorers of all time?
        - Which team has the best away record?
        - Which players received the most yellow cards?
        """
    )


def render_chat_tab() -> None:
    st.title("⚽ Football Database Analyst")
    st.write("Ask a question about the football league data.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if st.session_state.pending_question is None:
        question = st.chat_input("Ask a football database question...")

        if question:
            add_message("user", question)

            try:
                result = ask_graph(question)
            except Exception:
                answer = (
                    "Something went wrong while analysing that question. "
                    "Please try again."
                )
                add_message("assistant", answer)
            else:
                answer = result.get(
                    "answer",
                    "I could not create an answer for that question.",
                )
                add_message("assistant", answer)

                if result.get("needs_clarification"):
                    st.session_state.pending_question = question

            st.rerun()

    else:
        st.info("The analyst needs one clarification before it can continue.")

        clarification = st.chat_input("Add the missing detail...")

        if clarification:
            add_message("user", clarification)

            combined_question = (
                f"Original question: {st.session_state.pending_question}\n"
                f"User clarification: {clarification}"
            )

            try:
                result = ask_graph(combined_question)
            except Exception:
                answer = (
                    "Something went wrong while analysing that question. "
                    "Please try again."
                )
                add_message("assistant", answer)
            else:
                answer = result.get(
                    "answer",
                    "I could not create an answer for that question.",
                )
                add_message("assistant", answer)

                if result.get("needs_clarification"):
                    st.session_state.pending_question = combined_question
                else:
                    st.session_state.pending_question = None

            st.rerun()


def render_workflow_tab() -> None:
    st.title("How the LangGraph workflow works")

    st.write(
        "LangGraph coordinates the steps, decisions, and retries. "
        "It is the workflow controller; it is not the LLM itself."
    )

    st.graphviz_chart(WORKFLOW_DOT, use_container_width=True)

    st.subheader("What happens at each step")

    workflow_steps = [
        {
            "Step": "1. Normalise question",
            "What it does": "Removes unnecessary spaces from the user's question.",
            "LLM used?": "No",
        },
        {
            "Step": "2. Assess question",
            "What it does": "Decides whether the question is clear enough to answer.",
            "LLM used?": "Yes",
        },
        {
            "Step": "Ask for clarification",
            "What it does": "Returns a helpful question when important details are missing.",
            "LLM used?": "No",
        },
        {
            "Step": "3. Generate SQL",
            "What it does": "Turns the clear football question into a proposed SQL query.",
            "LLM used?": "Yes",
        },
        {
            "Step": "4. Validate SQL",
            "What it does": "Checks syntax, allows only one SELECT query, and blocks unknown tables.",
            "LLM used?": "No",
        },
        {
            "Step": "5. Execute SQL",
            "What it does": "Runs the approved query with the read-only PostgreSQL user.",
            "LLM used?": "No",
        },
        {
            "Step": "Repair SQL",
            "What it does": "Attempts one small correction if validation or execution fails.",
            "LLM used?": "Yes",
        },
        {
            "Step": "6. Explain results",
            "What it does": "Turns the exact database rows into a clear answer for the user.",
            "LLM used?": "Yes",
        },
        {
            "Step": "Failure reporting",
            "What it does": "Explains safely when SQL cannot be validated or executed.",
            "LLM used?": "No",
        },
    ]

    st.dataframe(
        workflow_steps,
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Important safety idea")

    st.info(
        "The LLM does not directly browse or control PostgreSQL. "
        "It proposes SQL, then Python validates it before PostgreSQL runs it. "
        "The LLM only receives the final query results to explain them."
    )


chat_tab, workflow_tab = st.tabs(
    ["Ask the analyst", "How the LangGraph workflow works"]
)

with chat_tab:
    render_chat_tab()

with workflow_tab:
    render_workflow_tab()