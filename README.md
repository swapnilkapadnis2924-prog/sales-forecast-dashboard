# Sales Forecast Dashboard — GitHub + Power BI

Fully automated, 100% free, 100% online pipeline.
Runs daily via GitHub Actions → outputs CSVs → Power BI auto-refreshes.

---

## Folder Structure

```
sales-forecast-dashboard/
├── .github/
│   └── workflows/
│       └── daily_forecast.yml   ← GitHub Actions schedule
├── data/
│   ├── input/
│   │   └── Sales Data - Sheet1.csv   ← YOU upload this
│   └── output/                       ← auto-generated daily
│       ├── daily_sales.csv
│       ├── forecast_comparison.csv
│       ├── future_forecast.csv
│       ├── model_metrics.csv
│       └── kpi_summary.csv
├── forecast_pipeline.py
├── requirements.txt
└── README.md
```

---

## Setup (One Time)

### 1. Create GitHub Repo
1. Go to github.com → New Repository
2. Name: `sales-forecast-dashboard`
3. Set to **Public**
4. Upload all files from this zip maintaining the folder structure

### 2. Upload Your CSV
1. Go to `data/input/` in your repo
2. Click **Add file → Upload files**
3. Upload your `Sales Data - Sheet1.csv`

### 3. Enable GitHub Actions
1. Go to your repo → **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. To test immediately: **Actions → Daily Sales Forecast → Run workflow**

### 4. Get Raw CSV URLs for Power BI
Replace `YOUR_USERNAME` with your GitHub username:

```
https://raw.githubusercontent.com/YOUR_USERNAME/sales-forecast-dashboard/main/data/output/daily_sales.csv
https://raw.githubusercontent.com/YOUR_USERNAME/sales-forecast-dashboard/main/data/output/forecast_comparison.csv
https://raw.githubusercontent.com/YOUR_USERNAME/sales-forecast-dashboard/main/data/output/future_forecast.csv
https://raw.githubusercontent.com/YOUR_USERNAME/sales-forecast-dashboard/main/data/output/model_metrics.csv
https://raw.githubusercontent.com/YOUR_USERNAME/sales-forecast-dashboard/main/data/output/kpi_summary.csv
```

### 5. Connect Power BI
1. Open Power BI Desktop
2. **Get Data → Web**
3. Paste each raw URL above — one per table
4. Set `Date` columns to **Date** type in Power Query
5. **Close & Apply**
6. Build your dashboard visuals
7. **Publish** to Power BI Service

### 6. Set Up Auto-Refresh in Power BI Service
1. Go to your dataset → **Settings → Scheduled Refresh**
2. Turn on scheduled refresh
3. Set time to **07:00 UTC** (1 hour after GitHub Action runs)
4. ✅ Dashboard refreshes automatically every day

---

## Daily Automated Flow

```
06:00 UTC  GitHub Actions triggers
           ↓
           Installs Python deps
           ↓
           Runs forecast_pipeline.py
           ↓
           Saves 5 CSVs to data/output/
           ↓
           Commits & pushes to GitHub
           ↓
07:00 UTC  Power BI scheduled refresh
           ↓
           Reads raw CSV URLs from GitHub
           ↓
           Dashboard updated ✅
```

---

## Updating Your Sales Data

When you have new sales data:
1. Go to `data/input/` in your repo
2. Upload the new `Sales Data - Sheet1.csv` (overwrite the old one)
3. GitHub Actions will pick it up at the next 06:00 UTC run
4. Or trigger manually: **Actions → Daily Sales Forecast → Run workflow**

---

## Power BI Visuals Guide

| Visual | Table | X-axis | Y-axis |
|---|---|---|---|
| Line Chart (trend) | `daily_sales` | Date | Quantity Sold, MA_7, MA_30 |
| Line Chart (forecast) | `forecast_comparison` | Date | Quantity Sold + 3 forecasts |
| Area Chart (future) | `future_forecast` | Date | Prophet Forecast + bounds |
| Clustered Bar | `model_metrics` | Model | MAE, RMSE |
| Clustered Bar | `kpi_summary` | Metric | Before(%), After(%) |
