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
import os
import re
import textwrap
import traceback
from typing import Optional

import pandas as pd
import streamlit as st

# LangChain - SQL stack
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase

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


def generate_ecommerce_dataset(n_customers: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generate the same realistic e-commerce churn dataset used in the
    companion Jupyter notebook (fixed seed -> identical data every run).
    """
    import numpy as np

    rng = np.random.default_rng(seed)

    age = rng.integers(18, 70, n_customers)
    gender = rng.choice(["Male", "Female"], n_customers, p=[0.48, 0.52])
    region = rng.choice(["North", "South", "East", "West"], n_customers)
    membership = rng.choice(
        ["Basic", "Silver", "Gold", "Platinum"],
        n_customers, p=[0.40, 0.30, 0.20, 0.10],
    )
    payment = rng.choice(["Card", "Mobile", "Cash", "BankTransfer"], n_customers)

    tenure_months = rng.integers(1, 60, n_customers)
    avg_order_value = rng.gamma(5, 20, n_customers).round(2)
    orders_per_month = np.clip(rng.normal(3, 1.5, n_customers), 0.1, None).round(2)
    return_rate = np.clip(rng.beta(2, 8, n_customers), 0, 1).round(3)
    support_tickets = rng.poisson(2, n_customers)
    days_since_last_order = rng.integers(0, 180, n_customers)
    discount_usage = rng.beta(2, 5, n_customers).round(3)

    churn_score = (
        0.020 * days_since_last_order
        + 1.500 * return_rate
        + 0.150 * support_tickets
        - 0.030 * tenure_months
        - 0.400 * (membership == "Platinum")
        - 0.200 * (membership == "Gold")
        - 0.300 * orders_per_month / 5
        + rng.normal(0, 0.5, n_customers)
    )
    churned = (churn_score > np.percentile(churn_score, 73)).astype(int)

    return pd.DataFrame({
        "customer_id": np.arange(1, n_customers + 1),
        "age": age,
        "gender": gender,
        "region": region,
        "membership_tier": membership,
        "preferred_payment": payment,
        "tenure_months": tenure_months,
        "avg_order_value": avg_order_value,
        "orders_per_month": orders_per_month,
        "return_rate": return_rate,
        "support_tickets": support_tickets,
        "days_since_last_order": days_since_last_order,
        "discount_usage": discount_usage,
        "churned": churned,
    })


@st.cache_resource(show_spinner="Building the demo dataset...")
def get_demo_database() -> SQLDatabase:
    """
    Generate the notebook's synthetic e-commerce dataset and load it into a
    local SQLite database. Requires no MySQL server and no credentials --
    only an OpenAI API key is needed to use the chatbot.

    The data is written to a `customers` table in `ecommerce_demo.db`.
    """
    from sqlalchemy import create_engine

    df = generate_ecommerce_dataset()
    engine = create_engine("sqlite:///ecommerce_demo.db")
    df.to_sql("customers", engine, if_exists="replace", index=False)
    return SQLDatabase(engine, sample_rows_in_table_info=3)


@st.cache_resource(show_spinner=False)
def get_llm(provider: str, api_key: str, model: str):
    """
    Instantiate a deterministic chat model (temperature=0) for the chosen
    provider. Imports are lazy so that providers you do not use need not
    be installed.

    Supported providers:
      - "OpenAI"        -> langchain_openai.ChatOpenAI
      - "Groq"          -> langchain_groq.ChatGroq          (free API key)
      - "Google Gemini" -> langchain_google_genai.ChatGoogleGenerativeAI (free)
    """
    if provider.startswith("OpenAI"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model, temperature=0, api_key=api_key,
            timeout=60, max_retries=2,
        )
    if provider.startswith("Groq"):
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model, temperature=0, api_key=api_key,
            timeout=60, max_retries=2,
        )
    if provider.startswith("Google"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model, temperature=0, google_api_key=api_key,
        )
    raise ValueError(f"Unknown provider: {provider}")


@st.cache_resource(show_spinner=False)
def get_sql_agent(_llm, _db: SQLDatabase, cache_key: str):
    """
    Build a tool-calling SQL agent.

    The LangChain objects (_llm, _db) are underscore-prefixed so Streamlit
    does not try to hash them. `cache_key` is a plain string that varies
    with the provider, model, API key and database, so switching provider
    in the sidebar correctly rebuilds the agent instead of reusing a stale
    one. (This is the fix for "still hitting OpenAI after switching to Groq".)
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
    llm, df: pd.DataFrame, question: str
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

    model_options = {
        "Groq (free)": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "Google Gemini (free)": ["gemini-2.0-flash", "gemini-1.5-flash"],
        "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    }
    key_help = {
        "Groq (free)": "console.groq.com/keys  (free, no credit card)",
        "Google Gemini (free)": "aistudio.google.com/apikey  (free, no credit card)",
        "OpenAI": "platform.openai.com/api-keys  (requires account credit)",
    }
    # Environment variable that each provider's key is auto-loaded from.
    key_env = {
        "Groq (free)": "GROQ_API_KEY",
        "Google Gemini (free)": "GOOGLE_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
    }

    with st.sidebar.expander("Language model", expanded=True):
        provider = st.selectbox(
            "Provider",
            options=["Groq (free)", "Google Gemini (free)", "OpenAI"],
            index=0,
            help="Groq and Google Gemini give you a free API key with no credit card.",
        )

        # Auto-load the key from an environment variable or Streamlit secrets,
        # so it can be set once instead of pasted every session.
        env_name = key_env[provider]
        prefilled = os.environ.get(env_name, "")
        if not prefilled:
            try:
                prefilled = st.secrets.get(env_name, "")  # type: ignore[attr-defined]
            except Exception:
                prefilled = ""

        api_key = st.text_input(
            f"{provider.split(' ')[0]} API Key",
            value=prefilled,
            type="password",
            key=f"api_key_{provider}",  # per-provider so keys never cross over
        )
        if prefilled:
            st.caption(f"Loaded from {env_name}.")
        else:
            st.caption(f"Get a free key: {key_help[provider]}")
        model_name = st.selectbox("Model", options=model_options[provider], index=0)

    data_source = st.sidebar.radio(
        "Data source",
        options=["Demo dataset (no server needed)", "My MySQL database"],
        index=0,
        help=(
            "The demo dataset is the same 5,000-customer e-commerce data "
            "from the companion Jupyter notebook, loaded into a local "
            "SQLite file. No MySQL server or credentials required."
        ),
    )
    use_demo = data_source.startswith("Demo")

    mysql_host = "localhost"
    mysql_port = 3306
    mysql_user = "root"
    mysql_password = ""
    mysql_db = ""

    if use_demo:
        st.sidebar.success(
            "Using the built-in demo dataset (table: `customers`, "
            "5,000 rows). Just add your OpenAI key and start asking.",
            icon="✅",
        )
    else:
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
        "provider": provider,
        "api_key": api_key,
        "model_name": model_name,
        "use_demo": use_demo,
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
    if not cfg.get("api_key"):
        return False
    if cfg.get("use_demo"):
        return True  # demo mode only needs the model API key
    required = ("host", "user", "database")
    return all(cfg.get(k) for k in required)


def friendly_error_message(exc: Exception) -> str:
    """Turn common provider errors into a clear, actionable message."""
    text = str(exc).lower()
    if "insufficient_quota" in text or "exceeded your current quota" in text:
        return (
            "Your OpenAI account has no available credit, so OpenAI rejected "
            "the request. Either add credit at platform.openai.com/account/billing, "
            "or switch the **Provider** in the sidebar to **Groq** or "
            "**Google Gemini** — both give you a free API key with no credit card."
        )
    if "rate limit" in text or "rate_limit" in text or " 429" in text:
        return (
            "The model provider rate-limited this request. Wait a few seconds "
            "and ask again."
        )
    if any(s in text for s in ("invalid api key", "incorrect api key",
                               "authentication", "401", "unauthorized",
                               "api key not valid")):
        return (
            "The API key was rejected. Check that the key matches the selected "
            "provider and was copied in full."
        )
    if "no module named" in text:
        return (
            "A provider package is not installed. Run:  "
            "`py -m pip install -r requirements.txt`  then restart the app."
        )
    return "The SQL agent failed to answer this question. See details below."


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
        "Ask plain-English questions about your e-commerce database. "
        "Get tables, summaries, or interactive charts on demand."
    )

    cfg = render_sidebar()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not config_is_complete(cfg):
        provider_name = cfg.get("provider", "model").split(" ")[0]
        if cfg.get("use_demo"):
            st.info(
                f"Enter your {provider_name} API key in the sidebar to begin. "
                "The demo e-commerce dataset is ready to query.",
                icon="ℹ️",
            )
        else:
            st.info(
                f"Enter your {provider_name} API key and MySQL connection "
                "details in the sidebar to begin.",
                icon="ℹ️",
            )
        st.stop()

    # Build (cached) resources.
    try:
        if cfg["use_demo"]:
            db = get_demo_database()
            db_id = "demo"
        else:
            db = get_database(
                host=cfg["host"],
                user=cfg["user"],
                password=cfg["password"],
                port=cfg["port"],
                database=cfg["database"],
            )
            db_id = f"{cfg['host']}:{cfg['port']}/{cfg['database']}"
        llm = get_llm(cfg["provider"], cfg["api_key"], cfg["model_name"])
        # Cache key ties the agent to this exact provider/model/key/db so a
        # sidebar change rebuilds the agent instead of reusing a stale one.
        cache_key = "|".join([
            cfg["provider"], cfg["model_name"],
            str(hash(cfg["api_key"])), db_id,
        ])
        sql_agent = get_sql_agent(llm, db, cache_key)
    except Exception as exc:
        st.error(friendly_error_message(exc))
        with st.expander("Technical details"):
            st.code(str(exc))
        st.stop()

    # Visible confirmation of which model is actually answering.
    st.caption(f"🧠 Active model: **{cfg['provider']}** · `{cfg['model_name']}`")

    if cfg["use_demo"]:
        st.caption(
            "Demo mode • table `customers` (5,000 rows) • try: "
            "*“churn rate by membership tier as a bar chart”* or "
            "*“top 10 customers by average order value”*."
        )

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
            except Exception as exc:
                err = traceback.format_exc()
                st.error(friendly_error_message(exc))
                with st.expander("Technical details"):
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
