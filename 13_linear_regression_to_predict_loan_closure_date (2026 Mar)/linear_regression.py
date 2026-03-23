import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
from sklearn.linear_model import LinearRegression

# ---- 1. Load data ----
df = pd.read_csv("./post_date_balance.csv")

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
    print(f"\nEstimated Loan Completion Date: {completion_date.date()}")
else:
    print("Slope is zero → cannot estimate completion")

# ---- 6. Plot ----
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
plt.show()

plt.savefig("./loan_balance_trend.png")
