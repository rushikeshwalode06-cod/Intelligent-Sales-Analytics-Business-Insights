"""Regenerate the sample sales dataset with deterministic synthetic records."""
from pathlib import Path
import random
import pandas as pd

random.seed(42)
products = [
    ("Wireless Mouse", "Accessories", 24.99, 10.00),
    ("Mechanical Keyboard", "Accessories", 79.00, 38.00),
    ("USB-C Hub", "Accessories", 49.00, 22.00),
    ("Laptop Pro 14", "Computers", 1299.00, 900.00),
    ("Laptop Air 13", "Computers", 999.00, 690.00),
    ("Monitor 27-inch", "Displays", 329.00, 210.00),
    ("Monitor 24-inch", "Displays", 199.00, 120.00),
    ("Webcam HD", "Accessories", 59.00, 25.00),
    ("Office Chair", "Furniture", 249.00, 145.00),
    ("Standing Desk", "Furniture", 499.00, 320.00),
]
regions = ["North", "South", "East", "West"]
rows = []
dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
for _ in range(360):
    product, category, unit_price, unit_cost = random.choice(products)
    date = random.choice(dates)
    quantity = random.randint(1, 8)
    if date.month in (11, 12):
        quantity += random.randint(0, 4)
    rows.append({
        "order_date": date.strftime("%Y-%m-%d"),
        "product": product,
        "category": category,
        "region": random.choice(regions),
        "quantity": quantity,
        "unit_price": unit_price,
        "unit_cost": unit_cost,
    })
out = Path(__file__).parent / "data" / "sample_sales.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print(f"Wrote {len(rows)} rows to {out}")
