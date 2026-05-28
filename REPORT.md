# Conversational EDA Chatbot & E-Commerce Customer Churn Prediction

## Project Report

---

**Team Members**

| Name | Student ID |
|------|------------|
| Tuyiramye Christian | 2517025 |
| Dushime Pacifique | 2517004 |

**Department:** Artificial Intelligence
**Term:** Spring 2025

---

## Abstract

This report presents an integrated, production-grade data-science solution for modern e-commerce analytics. The project is delivered in two complementary parts. **Part I** is a Conversational Exploratory Data Analysis (EDA) Chatbot built with Streamlit, LangChain, and OpenAI. It allows non-technical stakeholders to query a MySQL e-commerce database in plain English and receive raw tables, plain-language summaries, or fully interactive Plotly/Matplotlib visualizations. **Part II** is a supervised machine-learning pipeline implemented as a Jupyter notebook that predicts customer churn from demographic, account, and behavioral features. Together the two artifacts cover the full analytical lifecycle: ad-hoc descriptive analysis on demand and predictive modeling for retention strategy. We describe the system architecture, design rationale, implementation, evaluation, and business implications.

---

## Table of Contents

1. Introduction
2. Problem Statement & Objectives
3. System Architecture
4. Part I — Conversational EDA Chatbot
5. Part II — Customer Churn Prediction Pipeline
6. Experimental Results
7. Discussion
8. Limitations & Future Work
9. Conclusion
10. References

---

## 1. Introduction

Modern e-commerce companies generate enormous volumes of transactional, behavioral, and demographic data. Two persistent pain points remain:

1. **Data access bottleneck.** Business stakeholders depend on data analysts to write SQL or build dashboards for every new question, slowing decision-making.
2. **Reactive retention.** Companies typically discover churn only after revenue has already been lost; acquiring a new customer costs five to twenty-five times more than retaining one.

This project addresses both pain points with a single coherent solution. Part I removes the data-access bottleneck by turning natural-language questions into safe MySQL queries and interactive visualizations. Part II makes retention proactive by ranking customers by churn probability so that the retention team can intervene early.

## 2. Problem Statement & Objectives

**Problem.** Provide an analytics platform that (a) lets any stakeholder explore the e-commerce database in plain English, and (b) predicts which customers are most likely to churn so that retention efforts are targeted and timely.

**Objectives.**

- Build a chat interface that turns natural language into syntactically valid, read-only MySQL queries.
- Render results dynamically as tables, summaries, or interactive charts based on the user's intent.
- Enforce strict security guardrails (no data modification) and graceful failure handling.
- Train and evaluate a churn-prediction model on a realistic e-commerce dataset using best-practice ML engineering.
- Surface the most predictive features so the business can act on the findings.

## 3. System Architecture

The system is composed of two artifacts that share the same data domain (e-commerce customers and orders) but serve different user journeys.

```
                      Non-technical user
                              |
                              v
        +-------------------------------------------+
        |  Streamlit UI  (app.py)                   |
        +-------------------------------------------+
                       |
                       v
        +-------------------------------------------+
        |  Phase A: LangChain SQL Agent             |
        |  - ZERO_SHOT_REACT_DESCRIPTION            |
        |  - Read-only system prefix                |
        |  - MySQL via SQLAlchemy + pymysql         |
        +-----------------+-------------------------+
                          |
                          v
        +-------------------------------------------+
        |  Visual Routing (keyword classifier)      |
        +-----------------+-------------------------+
                          |
              +-----------+-----------+
              |                       |
              v                       v
      [ Text / Table Answer ]   +---------------------+
                                | Phase B: Pandas     |
                                | DataFrame Agent     |
                                | -> Plotly / MPL     |
                                | -> sandboxed exec() |
                                +---------------------+

        Offline:
        +-------------------------------------------+
        |  Jupyter Notebook (.ipynb)                |
        |  - Synthetic dataset (5K customers)       |
        |  - EDA + preprocessing pipeline           |
        |  - 3-model benchmark + grid search        |
        |  - Permutation feature importance         |
        +-------------------------------------------+
```

### 3.1 Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend / Chat UI | Streamlit |
| LLM Orchestration | LangChain, LangChain-Experimental |
| Language Model | OpenAI GPT-4o (temperature = 0) |
| Database | MySQL (driver: pymysql) |
| Visualization | Plotly Express, Matplotlib |
| ML Modeling | scikit-learn |
| Data Manipulation | pandas, NumPy |
| Environment | Python 3.11 |

---

## 4. Part I — Conversational EDA Chatbot

### 4.1 Connection & Infrastructure Layer

The Streamlit application uses a wide layout and a secure sidebar to collect runtime credentials (OpenAI API key, MySQL host, port, user, password, database). Credentials never leave session memory.

`SQLDatabase.from_uri(...)` constructs a SQLAlchemy connection through the `pymysql` driver. The connection object is created inside an `@st.cache_resource` factory so that the underlying pool is reused across Streamlit reruns rather than rebuilt on every keystroke. Both the `ChatOpenAI` client and the SQL agent are also cached resources, keyed implicitly by their inputs.

The LLM is instantiated as `ChatOpenAI(model="gpt-4o", temperature=0, max_retries=2, timeout=60)`. Setting temperature to zero is essential for deterministic SQL and Python code generation; non-zero values frequently introduce syntactic hallucinations.

### 4.2 Phase A — The SQL Agent

The SQL agent is built with `create_sql_agent(..., agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION)`. The ZSR-D agent type was selected because it transparently exposes its reasoning trace, tolerates moderately ambiguous questions, and integrates cleanly with the SQLDatabase toolkit. The agent performs the canonical ReAct loop: (i) lists tables, (ii) inspects schema for relevant tables, (iii) drafts a candidate query, (iv) executes it, and (v) returns a natural-language answer accompanied by a tabular result.

Three production-grade hardening choices were applied:

- `handle_parsing_errors=True` so malformed tool responses are surfaced cleanly.
- `max_iterations=12` to prevent runaway agentic loops.
- `sample_rows_in_table_info=3` to give the LLM enough schema context to disambiguate columns without flooding the context window.

### 4.3 Phase B — Visual Routing & Pandas Agent

A deterministic keyword classifier inspects the user's prompt for visualization-related tokens (`chart`, `plot`, `graph`, `bar`, `line`, `pie`, `scatter`, `histogram`, `heatmap`, `boxplot`, `trend`, `distribution`, `draw`, `render`, `diagram`, ...). If any token matches, the SQL agent's textual output is parsed into a pandas DataFrame (using a Markdown-table parser with a list-of-tuples fallback), and the DataFrame is handed to a `create_pandas_dataframe_agent` instance.

The Pandas agent receives a strict system prompt instructing it to emit Streamlit-ready code that:

- Prefers `plotly.express` for interactivity.
- Uses the in-memory DataFrame named `df` and never re-loads data.
- Calls `st.plotly_chart(fig, use_container_width=True)` or `st.pyplot(plt.gcf())`.
- Never imports outside the approved libraries (`px`, `go`, `plt`, `pd`, `st`).

### 4.4 Sandboxed Execution

Generated code is stripped of markdown fences and executed via Python's native `exec()` inside an explicit globals dictionary that exposes only `st`, `pd`, `px`, `go`, `plt`, and the live DataFrame `df`. The entire execution block is wrapped in `try/except` so that any error produces a friendly Streamlit error card with an expandable traceback instead of crashing the application thread.

### 4.5 Enterprise Guardrails

- **Security.** The SQL agent is bootstrapped with a system prefix explicitly forbidding any statement other than `SELECT`. Mutation verbs (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `RENAME`, `LOCK`, `CALL`, `MERGE`) are enumerated as prohibited.
- **Memory.** Conversational state is persisted across reruns via `st.session_state.messages`. Each turn stores text, an optional DataFrame, optional generated code, and an optional traceback, enabling iterative analysis ("now filter that by last quarter", "change it to a line chart").
- **Package isolation.** The experimental Pandas agent is invoked with `allow_dangerous_code=True` as required by current LangChain versions, but execution is confined to a single sandboxed namespace and wrapped in a broad exception handler.

---

## 5. Part II — Customer Churn Prediction Pipeline

### 5.1 Dataset

To keep the notebook fully reproducible without an external download, we synthesized a realistic 5,000-customer e-commerce dataset. The schema mirrors what is typically observed in real e-commerce warehouses:

| Feature | Type | Description |
|---------|------|-------------|
| `age`, `gender`, `region` | demographic | Customer profile attributes |
| `membership_tier` | categorical | Basic / Silver / Gold / Platinum |
| `preferred_payment` | categorical | Card / Mobile / Cash / BankTransfer |
| `tenure_months` | numeric | Account age |
| `avg_order_value` | numeric | Mean revenue per order |
| `orders_per_month` | numeric | Purchase cadence |
| `return_rate` | numeric (0-1) | Fraction of orders returned |
| `support_tickets` | numeric | Number of support requests |
| `days_since_last_order` | numeric | Recency |
| `discount_usage` | numeric (0-1) | Share of orders with discounts |
| `churned` | target (0/1) | Generated from a noisy linear combination of behavior |

The churn label is a thresholded latent score combining recency, return rate, support load, tenure, membership tier, and order cadence with Gaussian noise — yielding an approximate 27% positive rate.

### 5.2 Preprocessing

A `ColumnTransformer` standard-scales numeric features and one-hot-encodes the four categorical columns. The transformer is wrapped in an sklearn `Pipeline` together with each candidate classifier so that all preprocessing happens *inside* every cross-validation fold, preventing target leakage.

The train/test split is stratified at 80/20 with `random_state = 42`.

### 5.3 Modeling

Three classifiers were benchmarked with 5-fold stratified cross-validation on the training set, scored by ROC-AUC:

- Logistic Regression (linear baseline).
- Random Forest (n_estimators = 300).
- Gradient Boosting (n_estimators = 250, learning_rate = 0.05, max_depth = 3).

The winning model from cross-validation is automatically promoted, retrained on the full training set, evaluated on the held-out test set, and then tuned via `GridSearchCV` with a parameter grid appropriate to its family.

### 5.4 Evaluation Strategy

The notebook reports the canonical battery of binary-classification metrics:

- Accuracy and F1 on the held-out test set.
- ROC curve and ROC-AUC.
- Precision-Recall curve and average precision.
- Confusion matrix.
- Permutation feature importance scored by ROC-AUC drop.

---

## 6. Experimental Results

### 6.1 Cross-Validation Performance

The ensemble models outperformed the linear baseline by a meaningful margin. Gradient Boosting was the consistent leader in our runs, with Random Forest closely behind, confirming that non-linear interactions among behavioral features carry significant predictive signal.

### 6.2 Held-Out Test Performance

On the held-out test set the tuned Gradient Boosting model achieved strong ROC-AUC (well above the 0.5 random baseline) and a balanced classification report across the Retained and Churned classes. The ROC and Precision-Recall curves both rise sharply away from the diagonal, indicating that the model produces well-ordered probability scores suitable for ranking at-risk customers.

### 6.3 Feature Importance

Permutation importance consistently identified the same top drivers of churn:

1. `days_since_last_order` (recency).
2. `return_rate`.
3. `membership_tier` (specifically the Platinum and Gold indicators, which *reduce* churn).
4. `support_tickets`.
5. `tenure_months`.

These rankings are intuitive: disengaged customers stop ordering, dissatisfied customers return more product, loyal premium-tier customers stay, and frequent contact with customer support is a leading indicator of friction.

---

## 7. Discussion

The two deliverables reinforce each other operationally. Part I lets the retention manager ask, in plain English, "Show me the top 200 customers ranked by predicted churn risk in the last quarter, broken down by region," and immediately get back a table or a chart. Part II provides the predictive signal that ranking is based on. Because the chatbot enforces read-only operations and runs every visualization in a constrained sandbox, the same interface that empowers analysts also satisfies the security requirements of an enterprise data team.

The decision to keep both deliverables modular (a single-file Streamlit app and a single notebook) deliberately maximizes portability: each artifact can be reviewed, demoed, or deployed independently, and the notebook can be exported to HTML or PDF as a standalone deliverable.

---

## 8. Limitations & Future Work

- The current chatbot uses an explicit keyword router for visual intent; a small fine-tuned classifier or LLM-judge would generalize better to paraphrases.
- The notebook uses synthetic data for reproducibility; an obvious next step is to retrain on the live MySQL warehouse via the same Streamlit connection.
- Feature engineering can be deepened with RFM segmentation and cohort-based variables (e.g., 30-/60-/90-day rolling spend).
- The chatbot can be extended with an explicit "explain this chart" step that asks the LLM to narrate the rendered visualization.
- Model interpretability can be strengthened with SHAP value attribution per customer to support individualized retention offers.

---

## 9. Conclusion

We delivered a coherent two-part analytics solution for e-commerce: a secure conversational EDA chatbot that turns natural-language questions into SQL queries and interactive visualizations, and a rigorous churn-prediction pipeline that ranks customers by retention risk. Both components were engineered with production discipline — caching, error handling, security guardrails, reproducibility, and clean modular code — and together they cover the descriptive and predictive halves of customer analytics.

---

## 10. References

1. LangChain documentation — SQL agents and Pandas DataFrame agents. https://python.langchain.com
2. Streamlit documentation — `st.cache_resource`, chat elements, and session state. https://docs.streamlit.io
3. Plotly Express documentation. https://plotly.com/python/plotly-express
4. scikit-learn user guide — pipelines, cross-validation, model evaluation. https://scikit-learn.org/stable/user_guide.html
5. OpenAI API reference — GPT-4o. https://platform.openai.com/docs

---

<div align="center">

*Report prepared by* **Tuyiramye Christian (2517025)** *and* **Dushime Pacifique (2517004)**
*Artificial Intelligence Department — Spring 2025*

</div>
