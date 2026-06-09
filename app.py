"""
Conversational Exploratory Data Analysis (EDA) Chatbot
======================================================

A production-grade, single-file Streamlit application that lets non-technical
stakeholders ask plain-English questions about an e-commerce MySQL database and
receive raw tables, clear text summaries, or fully interactive charts.

Architecture
------------
    [User Prompt]
          |
          v
    +--------------------------+
    |  Phase A : SQL Agent     |  ZERO_SHOT_REACT_DESCRIPTION
    |  - inspects schema       |  read-only SELECT guardrail
    |  - generates MySQL       |
    |  - returns text table    |
    +-----------+--------------+
                |
                v
    +--------------------------+
    |  Visual Routing Logic    |  keyword classifier
    +-----------+--------------+
                |
        +-------+-------+
        |               |
        v               v
    [Text answer]   [Phase B : Pandas Agent]
                        - writes plotly / matplotlib code
                        - exec() inside Streamlit sandbox
                        - renders st.plotly_chart / st.pyplot

Run
---
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import io
import re
import textwrap
import traceback
from typing import Optional

import pandas as pd
import streamlit as st

# LangChain - SQL stack
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

# LangChain - Pandas / experimental stack (visualization)
from langchain_experimental.agents import create_pandas_dataframe_agent

# Plotting libraries made available to the exec() sandbox
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Constants & Guardrails
# ---------------------------------------------------------------------------

VISUAL_TRIGGERS = (
    "chart", "charts", "plot", "plots", "graph", "graphs", "visual",
    "visualize", "visualise", "visualization", "visualisation",
    "bar", "line", "pie", "scatter", "histogram", "heatmap", "boxplot",
    "trend", "distribution", "draw", "render", "diagram",
)

# Strict read-only system prefix for the SQL agent.
SQL_SYSTEM_PREFIX = textwrap.dedent(
    """
    You are an expert MySQL data analyst agent connected to a production
    e-commerce database. Always behave under the following non-negotiable
    rules:

    1. READ-ONLY MODE - You are permitted to issue ONLY `SELECT` statements.
       You must REFUSE and never generate any of the following: INSERT,
       UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, REPLACE, GRANT,
       REVOKE, RENAME, LOCK, CALL, MERGE, or any DDL/DML mutation.
    2. SAFETY - If a user asks you to modify, delete or drop anything,
       politely refuse and explain that the assistant is read-only.
    3. SCHEMA AWARENESS - Always inspect the schema (tables, columns,
       sample rows) before composing the final query.
    4. EFFICIENCY - Add a reasonable `LIMIT` clause when the user's
       question does not require an exhaustive scan, to keep responses fast.
    5. OUTPUT - After running the query, return the resulting dataset as
       a clean, well-aligned textual table the downstream layer can parse,
       followed by a concise plain-English summary.

    Never reveal credentials, connection strings, or internal tool names.
    """
).strip()

PANDAS_VIZ_INSTRUCTIONS = textwrap.dedent(
    """
    You are a senior Python data-visualization engineer working inside a
    Streamlit chat container. You will be given a pandas DataFrame named
    `df` already loaded in memory and a user request describing the chart.

    Your job:
    - Produce a SINGLE block of clean, executable Python code (no prose,
      no markdown fences, no explanations).
    - Prefer `plotly.express as px` for interactivity. Fall back to
      `matplotlib.pyplot as plt` only when explicitly requested.
    - The DataFrame is already available as `df`. Do NOT recreate it,
      reload it, or read any file.
    - For plotly, assign the figure to a variable named `fig` and then
      call `st.plotly_chart(fig, use_container_width=True)`.
    - For matplotlib, build the figure with `plt.figure(...)` and then
      call `st.pyplot(plt.gcf())`.
    - Always set a meaningful title and axis labels.
    - Never call `df = ...` or `import` statements for libraries other
      than the ones already provided (px, go, plt, pd, st are in scope).
    - Never write to disk, never call network APIs, never use `eval`,
      `os`, `sys`, `subprocess`, or `open`.

    Output ONLY the Python code. No backticks. No commentary.
    """
).strip()


# ---------------------------------------------------------------------------
# Connection & Infrastructure Layer
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Connecting to MySQL...")
def get_database(
    host: str, user: str, password: str, port: int, database: str
) -> SQLDatabase:
    """Create (and cache) a pooled SQLDatabase connection via pymysql."""
    uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return SQLDatabase.from_uri(uri, sample_rows_in_table_info=3)


@st.cache_resource(show_spinner=False)
def get_llm(api_key: str, model: str = "gpt-4o") -> ChatOpenAI:
    """Instantiate a deterministic ChatOpenAI client (temperature=0)."""
    return ChatOpenAI(
        model=model,
        temperature=0,
        api_key=api_key,
        timeout=60,
        max_retries=2,
    )


@st.cache_resource(show_spinner=False)
def get_sql_agent(_llm: ChatOpenAI, _db: SQLDatabase):
    """
    Build a ZERO_SHOT_REACT_DESCRIPTION SQL agent.

    Underscore-prefixed parameters tell Streamlit not to hash these
    unhashable LangChain objects when caching the resource.
    """
    return create_sql_agent(
        llm=_llm,
        db=_db,
        agent_type="tool-calling",
        prefix=SQL_SYSTEM_PREFIX,
        verbose=False,
        max_iterations=12,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )


# ---------------------------------------------------------------------------
# Phase A - SQL execution
# ---------------------------------------------------------------------------

def run_sql_agent(sql_agent, question: str) -> str:
    """
    Invoke the SQL agent on the user's question. Returns the agent's
    textual output (which generally includes a tabular dataset and/or
    a summary string).
    """
    result = sql_agent.invoke({"input": question})
    if isinstance(result, dict):
        return str(result.get("output", "")).strip()
    return str(result).strip()


def parse_agent_output_to_df(agent_output: str) -> Optional[pd.DataFrame]:
    """
    Best-effort parse of the SQL agent's textual output into a DataFrame.

    The agent typically returns a Markdown-style table. We try several
    parsers, then fall back to None (in which case the downstream layer
    will hand the raw text to the Pandas agent and let it cope).
    """
    if not agent_output:
        return None

    # 1) Markdown pipe-table extraction.
    table_lines = [
        line for line in agent_output.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(table_lines) >= 2:
        # Drop the markdown separator row, e.g. |---|---|
        cleaned = [
            ln for ln in table_lines
            if not re.match(r"^\s*\|?\s*[:\-\s|]+\s*\|?\s*$", ln)
        ]
        if cleaned:
            try:
                buffer = io.StringIO("\n".join(cleaned))
                df = pd.read_csv(
                    buffer, sep="|", engine="python", skipinitialspace=True
                )
                df = df.dropna(axis=1, how="all")
                df.columns = [str(c).strip() for c in df.columns]
                if not df.empty:
                    return df.reset_index(drop=True)
            except Exception:
                pass

    # 2) List-of-tuples fallback, e.g. "[(1, 'A'), (2, 'B')]"
    m = re.search(r"\[\s*\(.*\)\s*\]", agent_output, flags=re.S)
    if m:
        try:
            data = eval(m.group(0), {"__builtins__": {}}, {})  # noqa: S307
            if isinstance(data, list) and data and isinstance(data[0], tuple):
                return pd.DataFrame(data)
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# Phase B - Visualization router & sandbox
# ---------------------------------------------------------------------------

def is_visual_request(question: str) -> bool:
    """Explicit keyword classifier deciding whether to invoke Phase B."""
    if not question:
        return False
    tokens = re.findall(r"[a-zA-Z]+", question.lower())
    token_set = set(tokens)
    return any(trigger in token_set for trigger in VISUAL_TRIGGERS)


def strip_code_fences(code: str) -> str:
    """Remove ```python ... ``` wrappers the LLM sometimes adds."""
    code = code.strip()
    fenced = re.match(r"^```(?:python)?\s*(.*?)\s*```$", code, flags=re.S)
    if fenced:
        return fenced.group(1).strip()
    return code


def generate_visualization_code(
    llm: ChatOpenAI, df: pd.DataFrame, question: str
) -> str:
    """Run the experimental pandas agent to produce plotting code."""
    pandas_agent = create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        agent_type="tool-calling",
        verbose=False,
        allow_dangerous_code=True,  # required by newer langchain-experimental
        prefix=PANDAS_VIZ_INSTRUCTIONS,
        max_iterations=8,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )

    prompt = (
        f"User request: {question}\n\n"
        "Write the Streamlit-ready Python visualization code now. "
        "Return ONLY raw Python code, no commentary, no markdown fences."
    )
    response = pandas_agent.invoke({"input": prompt})
    raw_code = response.get("output", "") if isinstance(response, dict) else str(response)
    return strip_code_fences(raw_code)


def execute_visualization_code(code: str, df: pd.DataFrame) -> Optional[str]:
    """
    Execute the generated visualization code inside a constrained namespace.

    Returns None on success, or an error string on failure (so the caller
    can surface a friendly message instead of crashing the Streamlit thread).
    """
    sandbox_globals = {
        "__builtins__": __builtins__,
        "st": st,
        "pd": pd,
        "px": px,
        "go": go,
        "plt": plt,
        "df": df,
    }
    try:
        exec(code, sandbox_globals, sandbox_globals)  # noqa: S102
        return None
    except Exception:
        return traceback.format_exc()


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_sidebar() -> dict:
    """Render credential inputs and return the collected config dict."""
    st.sidebar.header("Configuration")
    st.sidebar.caption(
        "Credentials stay in memory for this session only and are never "
        "written to disk."
    )

    with st.sidebar.expander("OpenAI", expanded=True):
        openai_api_key = st.text_input(
            "OpenAI API Key", type="password", key="openai_api_key"
        )
        model_name = st.selectbox(
            "Model", options=["gpt-4o", "gpt-4", "gpt-4-turbo"], index=0
        )

    with st.sidebar.expander("MySQL", expanded=True):
        mysql_host = st.text_input("Host", value="localhost", key="mysql_host")
        mysql_port = st.number_input(
            "Port", value=3306, min_value=1, max_value=65535, key="mysql_port"
        )
        mysql_user = st.text_input("User", value="root", key="mysql_user")
        mysql_password = st.text_input(
            "Password", type="password", key="mysql_password"
        )
        mysql_db = st.text_input("Database", key="mysql_db")

    st.sidebar.divider()
    if st.sidebar.button("Reset conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    return {
        "openai_api_key": openai_api_key,
        "model_name": model_name,
        "host": mysql_host,
        "port": int(mysql_port),
        "user": mysql_user,
        "password": mysql_password,
        "database": mysql_db,
    }


def render_history():
    """Replay prior turns from st.session_state.messages."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("text"):
                st.markdown(msg["text"])
            if msg.get("dataframe") is not None:
                st.dataframe(msg["dataframe"], use_container_width=True)
            if msg.get("code"):
                with st.expander("Generated visualization code"):
                    st.code(msg["code"], language="python")
            if msg.get("error"):
                st.error(msg["error"])


def config_is_complete(cfg: dict) -> bool:
    required = ("openai_api_key", "host", "user", "database")
    return all(cfg.get(k) for k in required)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Conversational EDA Chatbot",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Conversational EDA Chatbot")
    st.caption(
        "Ask plain-English questions about your e-commerce MySQL database. "
        "Get tables, summaries, or interactive charts on demand."
    )

    cfg = render_sidebar()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not config_is_complete(cfg):
        st.info(
            "Enter your OpenAI API key and MySQL connection details in the "
            "sidebar to begin.",
            icon="ℹ️",
        )
        st.stop()

    # Build (cached) resources.
    try:
        db = get_database(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            port=cfg["port"],
            database=cfg["database"],
        )
        llm = get_llm(cfg["openai_api_key"], model=cfg["model_name"])
        sql_agent = get_sql_agent(llm, db)
    except Exception as exc:
        st.error(f"Failed to initialize backend resources: {exc}")
        st.stop()

    render_history()

    user_input = st.chat_input("Ask a question about your data...")
    if not user_input:
        return

    # Echo the user's turn.
    st.session_state.messages.append({"role": "user", "text": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # -------------------------------------------------------------------
    # Phase A : SQL agent
    # -------------------------------------------------------------------
    with st.chat_message("assistant"):
        with st.spinner("Querying the database..."):
            try:
                sql_output = run_sql_agent(sql_agent, user_input)
            except Exception:
                err = traceback.format_exc()
                st.error("The SQL agent failed to answer this question.")
                with st.expander("Traceback"):
                    st.code(err)
                st.session_state.messages.append(
                    {"role": "assistant", "text": "SQL agent failed.", "error": err}
                )
                return

        st.markdown(sql_output)

        df = parse_agent_output_to_df(sql_output)
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)

        assistant_msg = {
            "role": "assistant",
            "text": sql_output,
            "dataframe": df if df is not None and not df.empty else None,
        }

        # ---------------------------------------------------------------
        # Phase B : Visualization router
        # ---------------------------------------------------------------
        if is_visual_request(user_input):
            if df is None or df.empty:
                st.warning(
                    "I could not extract a tabular dataset from the SQL "
                    "answer, so I can't draw a chart for this turn. Try "
                    "rephrasing the question to return rows of data first."
                )
            else:
                with st.spinner("Designing the visualization..."):
                    try:
                        viz_code = generate_visualization_code(
                            llm, df, user_input
                        )
                    except Exception:
                        err = traceback.format_exc()
                        st.error("The visualization agent failed.")
                        with st.expander("Traceback"):
                            st.code(err)
                        assistant_msg["error"] = err
                        st.session_state.messages.append(assistant_msg)
                        return

                with st.expander("Generated visualization code"):
                    st.code(viz_code, language="python")

                exec_error = execute_visualization_code(viz_code, df)
                assistant_msg["code"] = viz_code
                if exec_error:
                    st.error(
                        "The generated chart code raised an error during "
                        "execution. See the traceback below."
                    )
                    with st.expander("Traceback"):
                        st.code(exec_error)
                    assistant_msg["error"] = exec_error

        st.session_state.messages.append(assistant_msg)


if __name__ == "__main__":
    main()
