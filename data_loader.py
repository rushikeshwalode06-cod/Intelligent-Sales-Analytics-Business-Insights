from pathlib import Path
import pandas as pd
from analytics import REQUIRED_COLUMNS

DATA_PATH = Path(__file__).parent / "data" / "sample_sales.csv"


def load_sample_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Sample dataset not found: {DATA_PATH}")
    return pd.read_csv(DATA_PATH)


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = getattr(uploaded_file, "name", "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Unsupported file type. Upload a CSV or Excel file.")


def validate_sales_data(df: pd.DataFrame) -> list[str]:
    normalized = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    errors = []
    missing = [col for col in REQUIRED_COLUMNS if col not in normalized]
    if missing:
        errors.append("Missing required columns: " + ", ".join(missing))
    if df.empty:
        errors.append("The uploaded dataset contains no rows.")
    return errors
