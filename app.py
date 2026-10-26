import os
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
from dotenv import load_dotenv

from analytics import (
    prepare_sales_data,
    calculate_kpis,
    build_business_summary,
)
from data_loader import (
    load_sample_data,
    read_uploaded_file,
    validate_sales_data,
)
from agent import (
    ask_sales_analyst,
    GeminiQuotaError,
    GeminiUnavailableError,
)

# =========================================================
# 1. CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Sales Intelligence AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv("GOOGLE_API_KEY", "").strip()
default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# =========================================================
# 2. RGB NEON UI
# =========================================================

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(ellipse at 5% 0%, rgba(124,58,237,.23), transparent 35%),
        radial-gradient(ellipse at 95% 5%, rgba(6,182,212,.15), transparent 30%),
        linear-gradient(135deg,#080411,#130824,#09051a);
    color: #f5edff;
}
[data-testid="stHeader"] {
    background: rgba(8,4,17,.8);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#1b0b32,#0b0618);
    border-right: 1px solid #a855f7;
}
[data-testid="stSidebar"] * {
    color: #f3e8ff;
}
h1,h2,h3 {
    color: #f5eaff !important;
    text-shadow: 0 0 12px rgba(168,85,247,.4);
}
h1 {
    border-bottom: 1px solid #22d3ee;
    padding-bottom: 12px;
}
[data-testid="stMetric"] {
    background: linear-gradient(145deg,#24113e,#100921);
    border: 1px solid #9855f7;
    border-radius: 16px;
    padding: 17px;
    box-shadow: 0 0 15px rgba(168,85,247,.17);
    transition: all .2s ease;
}
[data-testid="stMetric"]:hover {
    border-color: #22d3ee;
    box-shadow: 0 0 22px rgba(34,211,238,.3);
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    color: #c4b5fd !important;
}
[data-testid="stMetricValue"] {
    color: #67e8f9 !important;
}
.stButton > button,.stDownloadButton > button {
    background: linear-gradient(100deg,#7c3aed,#c026d3,#0891b2);
    color: white !important;
    border: 1px solid #67e8f9;
    border-radius: 11px;
    font-weight: 700;
    box-shadow: 0 0 12px rgba(168,85,247,.22);
    transition: all .2s ease;
}
.stButton > button:hover,.stDownloadButton > button:hover {
    border-color: white;
    box-shadow: 0 0 22px rgba(34,211,238,.45);
    transform: translateY(-2px);
}
.stTextInput input,.stTextArea textarea,
[data-baseweb="select"] > div,
[data-testid="stDateInput"] input {
    background: #110923 !important;
    color: white !important;
    border: 1px solid #8b5cf6 !important;
    border-radius: 10px !important;
}
.stTextInput input:focus,.stTextArea textarea:focus {
    border-color: #22d3ee !important;
    box-shadow: 0 0 10px rgba(34,211,238,.3) !important;
}
[data-testid="stFileUploader"] {
    background: rgba(28,13,50,.75);
    border: 1px dashed #22d3ee;
    border-radius: 14px;
    padding: 12px;
}
[data-testid="stPlotlyChart"],
[data-testid="stExpander"],
[data-testid="stDataFrame"] {
    background: rgba(19,9,37,.7);
    border: 1px solid rgba(168,85,247,.45);
    border-radius: 14px;
    overflow: hidden;
}
[data-testid="stAlert"] {
    border-radius: 12px;
}
hr {
    border-color: rgba(168,85,247,.5) !important;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)

pio.templates["rgb_neon"] = pio.templates["plotly_dark"]
pio.templates["rgb_neon"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(12,6,27,0.25)",
    font=dict(color="#eee7ff"),
    title=dict(font=dict(color="#67e8f9")),
    colorway=[
        "#22d3ee", "#c084fc", "#f472b6",
        "#a3e635", "#facc15"
    ],
)
pio.templates.default = "rgb_neon"


def style_chart(fig):
    fig.update_layout(
        template="rgb_neon",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,6,27,0.25)",
        font_color="#eee7ff",
        title_font_color="#67e8f9",
        margin=dict(l=20, r=20, t=60, b=30),
        legend_title_font_color="#c4b5fd",
    )
    return fig


# =========================================================
# 3. HEADER AND SIDEBAR
# =========================================================

st.title("📊 Intelligent Sales Analytics")
st.markdown(
    "### ✨ AI-powered sales intelligence and business insights"
)
st.caption(
    "Analyze revenue, profitability, products, categories and regions."
)

with st.sidebar:
    st.markdown("# 💜 Sales AI")
    st.caption("RGB NEON ANALYTICS DASHBOARD")
    st.divider()

    st.subheader("⚙️ AI Settings")
    model_name = st.text_input(
        "Gemini model",
        value=default_model,
        help="Enter a Gemini model ID supported by your API key.",
    ).strip()

    st.caption(
        "Gemini API usage depends on your project's model access, "
        "rate limits and quota."
    )

    st.divider()
    st.subheader("📋 Expected columns")
    st.code(
        "order_date, product, category, region,\n"
        "quantity, unit_price, unit_cost",
        language="text",
    )
    st.caption("Upload CSV, XLSX or XLS files.")

    if api_key:
        st.success("API key detected")
    else:
        st.warning("Gemini API key not detected")

if not api_key:
    st.info(
        "Dashboard analytics work without an API key. "
        "Add GOOGLE_API_KEY to your .env file to enable AI insights."
    )

# =========================================================
# 4. DATA UPLOAD AND VALIDATION
# =========================================================

st.subheader("📂 Upload your sales dataset")

uploaded_file = st.file_uploader(
    "Choose a sales CSV or Excel file",
    type=["csv", "xlsx", "xls"],
)

try:
    if uploaded_file is not None:
        raw_df = read_uploaded_file(uploaded_file)
        data_source = uploaded_file.name
    else:
        raw_df = load_sample_data()
        data_source = "Included sample dataset"

    validation = validate_sales_data(raw_df)

    if validation:
        st.error(
            "Please fix these dataset issues:\n\n"
            + "\n".join(f"- {error}" for error in validation)
        )
        st.stop()

    df = prepare_sales_data(raw_df)

    if df.empty:
        st.error(
            "No valid rows remain after processing. "
            "Check the date and numeric columns."
        )
        st.stop()

except Exception as exc:
    st.error(f"Could not load dataset: {exc}")
    st.info("Try a valid CSV or Excel sales file.")
    st.stop()

info_col1, info_col2 = st.columns([3, 1])
with info_col1:
    st.success(f"Dataset loaded: {data_source}")
with info_col2:
    st.metric("Total data rows", f"{len(df):,}")

with st.expander("👀 Preview dataset"):
    st.dataframe(df.head(100), use_container_width=True)

# =========================================================
# 5. DASHBOARD FILTERS
# =========================================================

st.divider()
st.subheader("🎛️ Dashboard filters")

filter_cols = st.columns(3)

with filter_cols[0]:
    regions = sorted(
        df["region"].dropna().astype(str).unique().tolist()
    )
    selected_regions = st.multiselect(
        "🌍 Region",
        regions,
        default=regions,
    )

with filter_cols[1]:
    categories = sorted(
        df["category"].dropna().astype(str).unique().tolist()
    )
    selected_categories = st.multiselect(
        "📦 Category",
        categories,
        default=categories,
    )

with filter_cols[2]:
    min_date = df["order_date"].min().date()
    max_date = df["order_date"].max().date()

    date_range = st.date_input(
        "📅 Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    df["region"].astype(str).isin(selected_regions)
    & df["category"].astype(str).isin(selected_categories)
    & df["order_date"].dt.date.between(start_date, end_date)
].copy()

if filtered.empty:
    st.warning(
        "No rows match the selected filters. "
        "Choose at least one region and category."
    )
    st.stop()

# =========================================================
# 6. KPI CARDS
# =========================================================

kpis = calculate_kpis(filtered)

st.divider()
st.subheader("⚡ Business performance overview")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("💰 Revenue", f"${kpis['revenue']:,.2f}")
k2.metric("📈 Profit", f"${kpis['profit']:,.2f}")
k3.metric("📊 Profit margin", f"{kpis['profit_margin']:.1f}%")
k4.metric("🧾 Orders / rows", f"{kpis['orders']:,}")
k5.metric("📦 Units sold", f"{kpis['units_sold']:,}")

# =========================================================
# 7. SALES CHARTS
# =========================================================

st.divider()
st.subheader("📈 Sales analytics")

left, right = st.columns(2)

with left:
    monthly = (
        filtered.assign(
            month=filtered["order_date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        .groupby("month", as_index=False)[["revenue", "profit"]]
        .sum()
    )

    fig = px.line(
        monthly,
        x="month",
        y=["revenue", "profit"],
        markers=True,
        title="Monthly revenue and profit",
        labels={"value": "Amount ($)", "month": "Month"},
    )
    st.plotly_chart(style_chart(fig), use_container_width=True)

with right:
    by_category = (
        filtered.groupby("category", as_index=False)[
            ["revenue", "profit"]
        ]
        .sum()
        .sort_values("revenue", ascending=False)
    )

    fig = px.bar(
        by_category,
        x="category",
        y=["revenue", "profit"],
        barmode="group",
        title="Performance by category",
        labels={"value": "Amount ($)", "category": "Category"},
    )
    st.plotly_chart(style_chart(fig), use_container_width=True)

left, right = st.columns(2)

with left:
    by_region = (
        filtered.groupby("region", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )

    fig = px.bar(
        by_region,
        x="region",
        y="revenue",
        title="Revenue by region",
        labels={"revenue": "Revenue ($)", "region": "Region"},
        color="revenue",
        color_continuous_scale=["#7c3aed", "#22d3ee", "#f472b6"],
    )
    st.plotly_chart(style_chart(fig), use_container_width=True)

with right:
    by_product = (
        filtered.groupby("product", as_index=False)[
            ["profit", "revenue", "quantity"]
        ]
        .sum()
        .sort_values("profit", ascending=False)
        .head(10)
    )

    fig = px.bar(
        by_product,
        x="product",
        y="profit",
        title="Top 10 products by profit",
        labels={"profit": "Profit ($)", "product": "Product"},
        color="profit",
        color_continuous_scale=["#7c3aed", "#c084fc", "#22d3ee"],
    )
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(style_chart(fig), use_container_width=True)

with st.expander("📋 Detailed filtered data"):
    st.dataframe(filtered, use_container_width=True)

# =========================================================
# 8. GEMINI AI SALES ANALYST
# =========================================================

st.divider()
st.subheader("💬 Ask your AI Sales Analyst")
st.write(
    "Ask questions about the currently filtered data. "
    "For example: Which region is most profitable? "
    "How can we improve low profit margins?"
)

question = st.text_area(
    "Your question",
    placeholder=(
        "Summarize sales performance and give "
        "3 actionable recommendations."
    ),
    height=120,
    key="sales_question",
)

if st.button("✨ Generate AI Insights", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Please enter a question first.")

    elif not api_key:
        st.error(
            "Gemini API key is missing. Add GOOGLE_API_KEY "
            "to your .env file and restart Streamlit."
        )

    elif not model_name:
        st.error("Enter a valid Gemini model ID in the sidebar.")

    else:
        summary = build_business_summary(filtered)

        try:
            answer = None

            with st.spinner(
                f"🤖 Consulting Gemini model: {model_name}..."
            ):
                # One retry only for temporary service unavailability.
                for attempt in range(2):
                    try:
                        answer = ask_sales_analyst(
                            question.strip(),
                            summary,
                            model_name=model_name,
                            api_key=api_key,
                        )
                        break

                    except GeminiUnavailableError:
                        if attempt == 1:
                            raise
                        time.sleep(2)

            st.markdown("### 🧠 AI-generated business analysis")
            st.markdown(answer)

        except GeminiQuotaError as exc:
            st.error("Gemini API quota or rate limit reached.")
            st.warning(str(exc))
            st.markdown(
                "Check your [Google AI Studio rate limits]"
                "(https://ai.dev/rate-limit). "
                "Wait for the quota window to reset or review "
                "your project limits. Retrying will not restore "
                "an exhausted quota."
            )

        except GeminiUnavailableError as exc:
            st.error("Gemini is temporarily unavailable.")
            st.warning(str(exc))
            st.info(
                "The app already retried once. Wait a few minutes "
                "and try again. Check model availability if the "
                "problem continues."
            )

        except Exception as exc:
            st.error(f"AI request failed: {exc}")
            st.info(
                "Check your API key, model ID, network connection "
                "and Google AI Studio project."
            )

# =========================================================
# 9. EXPORT
# =========================================================

st.divider()
st.subheader("📥 Export filtered sales data")

csv_bytes = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download filtered data as CSV",
    data=csv_bytes,
    file_name="filtered_sales_data.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption(
    "AI insights use summary statistics and should be verified "
    "against the source data before making important business decisions."
)
