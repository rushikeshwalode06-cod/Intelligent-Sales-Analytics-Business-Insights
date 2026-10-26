import pandas as pd

NUMERIC_COLUMNS = ["quantity", "unit_price", "unit_cost"]
REQUIRED_COLUMNS = ["order_date", "product", "category", "region", *NUMERIC_COLUMNS]


def prepare_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [str(c).strip().lower().replace(" ", "_") for c in result.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in result.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    result["order_date"] = pd.to_datetime(result["order_date"], errors="coerce")
    for col in NUMERIC_COLUMNS:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result = result.dropna(subset=REQUIRED_COLUMNS).copy()
    result = result[(result["quantity"] >= 0) & (result["unit_price"] >= 0) & (result["unit_cost"] >= 0)]
    result["revenue"] = result["quantity"] * result["unit_price"]
    result["cost"] = result["quantity"] * result["unit_cost"]
    result["profit"] = result["revenue"] - result["cost"]
    result["profit_margin"] = result.apply(
        lambda row: (row["profit"] / row["revenue"] * 100) if row["revenue"] else 0.0, axis=1
    )
    return result.sort_values("order_date").reset_index(drop=True)


def calculate_kpis(df: pd.DataFrame) -> dict:
    revenue = float(df["revenue"].sum())
    profit = float(df["profit"].sum())
    return {
        "revenue": revenue,
        "cost": float(df["cost"].sum()),
        "profit": profit,
        "profit_margin": (profit / revenue * 100) if revenue else 0.0,
        "orders": int(len(df)),
        "units_sold": int(df["quantity"].sum()),
    }


def _records(grouped: pd.DataFrame, metric: str, n: int = 10) -> list[dict]:
    if grouped.empty:
        return []
    return grouped.sort_values(metric, ascending=False).head(n).round(2).to_dict(orient="records")


def build_business_summary(df: pd.DataFrame) -> dict:
    kpis = calculate_kpis(df)
    monthly = df.assign(month=df["order_date"].dt.to_period("M").astype(str)).groupby("month", as_index=False)[["revenue", "profit"]].sum()
    category = df.groupby("category", as_index=False)[["revenue", "profit", "quantity"]].sum()
    region = df.groupby("region", as_index=False)[["revenue", "profit", "quantity"]].sum()
    product = df.groupby("product", as_index=False)[["revenue", "profit", "quantity"]].sum()
    return {
        "row_count": int(len(df)),
        "date_range": [str(df["order_date"].min().date()), str(df["order_date"].max().date())],
        "kpis": {k: round(v, 2) if isinstance(v, float) else v for k, v in kpis.items()},
        "monthly_performance": monthly.round(2).to_dict(orient="records"),
        "category_performance": _records(category, "revenue", 20),
        "region_performance": _records(region, "revenue", 20),
        "top_products_by_profit": _records(product, "profit", 10),
        "lowest_products_by_profit": product.sort_values("profit").head(10).round(2).to_dict(orient="records"),
    }
