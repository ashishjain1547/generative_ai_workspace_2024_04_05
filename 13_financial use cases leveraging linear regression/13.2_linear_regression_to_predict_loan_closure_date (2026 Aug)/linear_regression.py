import os
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-Qt backend, avoids Wayland plugin warning
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

DATA_DIR = "./data"


def find_latest_csv(data_dir=DATA_DIR):
    """Return the path of the latest CSV file from the data directory."""
    csv_files = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.lower().endswith(".csv")
    ]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    # Sort by the 8-digit date (YYYYMMDD) in the filename, mtime as tiebreak
    def sort_key(path):
        m = re.search(r"\d{8}", os.path.basename(path))
        return (m.group(0) if m else "", os.path.getmtime(path))

    csv_files.sort(key=sort_key)
    latest_csv = csv_files[-1]

    m = re.search(r"\d{8}", os.path.basename(latest_csv))
    date_prefix = m.group(0) if m else ""

    return latest_csv, date_prefix


# ---- 1. Load data ----
csv_path, date_prefix = find_latest_csv()
print(f"Reading CSV: {csv_path}")
df = pd.read_csv(csv_path)

# Convert types
df["post_date"] = pd.to_datetime(df["post_date"], format="%d/%m/%Y")
df["balance"] = df["balance"].astype(float)

# Sort by date
df = df.sort_values("post_date")

# ---- 2. Convert dates to numeric (days since first date) ----
start_date = df["post_date"].min()
df["days"] = (df["post_date"] - start_date).dt.days

X = df[["days"]].values
y = df["balance"].values

# ---- 3. Fit Linear Regression ----
model = LinearRegression()
model.fit(X, y)

slope = model.coef_[0]
intercept = model.intercept_

print(f"Slope (balance change per day): {slope:.2f}")
print(f"Intercept: {intercept:.2f}")

# ---- 4. Predict regression line ----
df["predicted_balance"] = model.predict(X)

# ---- 5. Estimate loan completion (balance = 0) ----
# Solve: 0 = slope * days + intercept
if slope != 0:
    days_to_zero = -intercept / slope
    completion_date = start_date + timedelta(days=int(days_to_zero))
    completion_date_str = str(completion_date.date())
    print(f"\nEstimated Loan Completion Date: {completion_date_str}")
else:
    completion_date_str = "N/A"
    print("Slope is zero → cannot estimate completion")

# ---- 6. Append stats to run_stats.csv ----
run_date = datetime.strptime(date_prefix, "%Y%m%d")
date_label = run_date.strftime("%Y-%b-%d").upper()  # e.g., "2026-AUG-06"

stats_row = pd.DataFrame([{
    "Date": date_label,
    "Slope (balance change per day)": f"{slope:.2f}",
    "Intercept": f"{intercept:.2f}",
    "Estimated Loan Completion Date": completion_date_str,
}])
stats_path = "./run_stats.csv"
stats_row.to_csv(stats_path, mode="a", header=False, index=False)
print(f"Appended stats to {stats_path}")

# ---- 7. Plot ----
OUT_DIR = "./out"
os.makedirs(OUT_DIR, exist_ok=True)

plt.figure(figsize=(10, 5))
plt.scatter(df["post_date"], df["balance"], label="Actual Balance")
plt.plot(df["post_date"], df["predicted_balance"], linestyle="--", label="Regression Line")

plt.xlabel("Date")
plt.ylabel("Balance")
plt.title("Loan Balance Trend & Linear Regression")
plt.legend()
plt.grid()

plt.xticks(rotation=45)
plt.tight_layout()

out_path = os.path.join(OUT_DIR, f"{date_prefix}_trend_line.png")
plt.savefig(out_path)
print(f"Saved plot to {out_path}")
