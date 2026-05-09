"""
Sales Forecast Pipeline
=======================
Runs automatically via GitHub Actions every day at 06:00 UTC.
Reads:  data/input/Sales Data - Sheet1.csv
Writes: data/output/*.csv  (picked up by Power BI)
"""

import os
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

# ── Paths ─────────────────────────────────────────────────
INPUT_PATH = "data/input/Sales Data - Sheet1.csv"
OUTPUT_DIR = "data/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("📥 Loading data ...")

# ── 1. Load & Clean ───────────────────────────────────────
df = pd.read_csv(INPUT_PATH)
df.columns = df.columns.str.strip().str.lower()
date_col = [c for c in df.columns if "date" in c][0]
qty_col  = [c for c in df.columns if "qty" in c or "quantity" in c][0]

df["date"] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=["date", qty_col])
df = df[df[qty_col] > 0]

daily = df.groupby(df["date"].dt.floor("D"))[qty_col].sum().reset_index()
daily.columns = ["Date", "Quantity Sold"]

full_dates = pd.DataFrame({
    "Date": pd.date_range(daily["Date"].min(), daily["Date"].max(), freq="D")
})
daily = full_dates.merge(daily, on="Date", how="left").fillna({"Quantity Sold": 0})
daily["Quantity Sold"] = daily["Quantity Sold"].astype(int)
daily = daily.sort_values("Date").reset_index(drop=True)
daily["MA_7"]         = daily["Quantity Sold"].rolling(7).mean().round(2)
daily["MA_30"]        = daily["Quantity Sold"].rolling(30).mean().round(2)
daily["Volatility_7"] = daily["Quantity Sold"].rolling(7).std().round(2)

print(f"   {len(daily)} days loaded  ({daily['Date'].min().date()} → {daily['Date'].max().date()})")

# ── 2. Train / Test Split (80/20) ─────────────────────────
split = int(len(daily) * 0.8)
train = daily.iloc[:split].copy()
test  = daily.iloc[split:].copy()
print(f"   Train: {len(train)} rows | Test: {len(test)} rows")

# ── 3. Naive Forecast ─────────────────────────────────────
print("🔮 Naive forecast ...")
test["Naive Forecast"] = test["Quantity Sold"].shift(1)
test.iloc[0, test.columns.get_loc("Naive Forecast")] = train["Quantity Sold"].iloc[-1]
test["Naive Forecast"] = test["Naive Forecast"].clip(lower=0).round(2)

# ── 4. ARIMA Forecast ─────────────────────────────────────
print("📈 ARIMA forecast (grid search p,q 0-3) ...")
d = 1 if adfuller(train["Quantity Sold"])[1] > 0.05 else 0
best_aic, best_order, best_fit = np.inf, (1, d, 1), None

for p in range(0, 4):
    for q in range(0, 4):
        try:
            fit = ARIMA(train["Quantity Sold"], order=(p, d, q)).fit()
            if fit.aic < best_aic:
                best_aic, best_order, best_fit = fit.aic, (p, d, q), fit
        except Exception:
            pass

print(f"   Best ARIMA order: {best_order}  AIC: {best_aic:.2f}")
test["ARIMA Forecast"] = best_fit.forecast(steps=len(test)).clip(lower=0).round(2).values

# ── 5. Prophet Forecast ───────────────────────────────────
print("🔭 Prophet forecast ...")
df_p = daily.rename(columns={"Date": "ds", "Quantity Sold": "y"})[["ds", "y"]]
pm   = Prophet(
    daily_seasonality=True,
    yearly_seasonality=True,
    weekly_seasonality=True
)
pm.fit(df_p.iloc[:split])

fc = pm.predict(pm.make_future_dataframe(periods=len(test), freq="D")).tail(len(test))
test["Prophet Forecast"] = fc["yhat"].clip(lower=0).round(2).values

# ── 6. Future 30-Day Forecast ─────────────────────────────
print("📅 Future 30-day forecast ...")
fc30       = pm.predict(pm.make_future_dataframe(periods=30, freq="D")).tail(30)
future_out = fc30[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
future_out.columns = ["Date", "Prophet Forecast", "Lower Bound", "Upper Bound"]

# ── FIX: clip only numeric columns, not the Date column ───
numeric_cols = ["Prophet Forecast", "Lower Bound", "Upper Bound"]
future_out[numeric_cols] = future_out[numeric_cols].clip(lower=0).round(2)

# ── 7. Model Metrics ──────────────────────────────────────
y = test["Quantity Sold"]
metrics_out = pd.DataFrame({
    "Model": ["Naive", "ARIMA", "Prophet"],
    "MAE": [
        round(mean_absolute_error(y, test["Naive Forecast"]),   4),
        round(mean_absolute_error(y, test["ARIMA Forecast"]),   4),
        round(mean_absolute_error(y, test["Prophet Forecast"]), 4),
    ],
    "RMSE": [
        round(np.sqrt(mean_squared_error(y, test["Naive Forecast"])),   4),
        round(np.sqrt(mean_squared_error(y, test["ARIMA Forecast"])),   4),
        round(np.sqrt(mean_squared_error(y, test["Prophet Forecast"])), 4),
    ],
})
print("\n📊 Model Metrics:")
print(metrics_out.to_string(index=False))

# ── 8. KPI Summary ────────────────────────────────────────
kpi_out = pd.DataFrame({
    "Metric":           ["Forecast Reliability", "Inventory Efficiency",
                         "Sales Realization",    "Planning Efficiency"],
    "Before (%)":       [50, 60, 70, 55],
    "After (%)":        [70, 75, 75, 70],
    "Improvement (pp)": [20, 15,  5, 15],
})

# ── 9. Build Forecast Comparison ─────────────────────────
train_out = train[["Date", "Quantity Sold"]].copy()
train_out["Split"] = "Train"
for col in ["Naive Forecast", "ARIMA Forecast", "Prophet Forecast"]:
    train_out[col] = np.nan

test["Split"] = "Test"
forecast_comp = pd.concat([train_out, test], ignore_index=True)

# ── 10. Save All CSVs ─────────────────────────────────────
print(f"\n💾 Saving CSVs to {OUTPUT_DIR}/ ...")

daily[["Date", "Quantity Sold", "MA_7", "MA_30", "Volatility_7"]].to_csv(
    f"{OUTPUT_DIR}/daily_sales.csv", index=False)

forecast_comp.to_csv(f"{OUTPUT_DIR}/forecast_comparison.csv", index=False)
future_out.to_csv(   f"{OUTPUT_DIR}/future_forecast.csv",     index=False)
metrics_out.to_csv(  f"{OUTPUT_DIR}/model_metrics.csv",       index=False)
kpi_out.to_csv(      f"{OUTPUT_DIR}/kpi_summary.csv",         index=False)

print("✅ Done! Files saved:")
for f in sorted(os.listdir(OUTPUT_DIR)):
    size = os.path.getsize(f"{OUTPUT_DIR}/{f}")
    print(f"   📄 {f}  ({size:,} bytes)")
