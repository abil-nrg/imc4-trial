import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from parse import parse
from pathlib import Path

# --- CONSTANTS ---
STEPS_PER_DAY = 10000 
CAPITAL = 100000
MIN_DAILY_VOL_FLOOR = 0.001  # 0.1% minimum daily volatility to avoid Sharpe blow-up

st.set_page_config(page_title="Quant Analytics", layout="wide")

# --- DATA LOADING ---
LOG_DIR = Path(__file__).parent.parent / "backtests"

@st.cache_data(show_spinner=False)
def get_backtest_data(file_path, mtime):
    act_df, trade_df, _ = parse(file_path)
    if act_df is not None and not act_df.empty:
        act_df = act_df.copy()
        if 'ask_price_1' in act_df.columns and 'bid_price_1' in act_df.columns:
            act_df['spread'] = act_df['ask_price_1'] - act_df['bid_price_1']
            act_df['spread_pct'] = act_df['spread'] / act_df['mid_price']
    return act_df, trade_df

# --- RISK METRICS ---
def calculate_day_adjusted_metrics(returns):
    if returns is None or len(returns) == 0:
        return 0, 0, 0
    var_95 = np.percentile(returns, 5) * 100
    vol_step = returns.std()
    vol_daily = vol_step * np.sqrt(STEPS_PER_DAY)
    mean_step = returns.mean()
    sharpe_daily = (mean_step * STEPS_PER_DAY) / vol_daily if vol_daily != 0 else 0
    return var_95, vol_daily * 100, sharpe_daily

def calculate_cvar(returns):
    if returns is None or len(returns) == 0:
        return 0
    var_threshold = np.percentile(returns, 5)
    cvar = returns[returns <= var_threshold].mean()
    return cvar * 100

def calculate_drawdown(pnl):
    running_max = pnl.cummax()
    drawdown_abs = pnl - running_max
    max_dd_abs = drawdown_abs.min()
    return drawdown_abs, max_dd_abs

# --- SIDEBAR ---
st.sidebar.header("Control Panel")
log_files = list(LOG_DIR.glob("*.log")) + list(LOG_DIR.glob("*.txt"))
if not log_files:
    st.error("No logs found in the backtests directory.")
    st.stop()

selected_file = st.sidebar.selectbox("Log File", log_files, format_func=lambda x: x.name)
act_df, trade_df = get_backtest_data(selected_file, selected_file.stat().st_mtime)

products = act_df['product'].unique()
selected_product = st.sidebar.selectbox("Product", products)

filtered_df = act_df[act_df['product'] == selected_product].copy()
if filtered_df.empty:
    st.warning("No data for selected product.")
    st.stop()
filtered_df = filtered_df.sort_values('timestamp')

# --- FEATURE SELECTION ---
exclude = ['day', 'timestamp', 'product']
metrics = [c for c in filtered_df.columns if c not in exclude]
selected_metric = st.sidebar.selectbox(
    "Primary Metric (Y-axis)",
    metrics,
    index=metrics.index('mid_price') if 'mid_price' in metrics else 0
)
chart_type = st.sidebar.radio(
    "Chart Type",
    ["Time Series", "Scatter", "Histogram", "Box", "Drawdown", "Rolling"]
)
if chart_type == "Scatter":
    second_metric = st.sidebar.selectbox(
        "Secondary Metric (X-axis)",
        metrics,
        index=metrics.index('bid_volume_1') if 'bid_volume_1' in metrics else 0
    )

# --- RETURNS ---
filtered_df['returns'] = filtered_df['profit_and_loss'].diff().fillna(0)
filtered_df['returns_pct'] = filtered_df['returns'] / CAPITAL
returns = filtered_df['returns_pct']

# --- METRICS ---
var_pct, vol_daily, sharpe_daily = calculate_day_adjusted_metrics(returns)
cvar_pct = calculate_cvar(returns)
drawdown_series, max_dd = calculate_drawdown(filtered_df['profit_and_loss'])

# --- ROLLING METRICS (with optional volatility floor) ---
window = st.sidebar.slider("Rolling Window (Steps)", 50, 5000, 1000)
use_vol_floor = st.sidebar.checkbox("Apply volatility floor to rolling Sharpe", value=True)

rolling_mean = returns.rolling(window).mean()
rolling_std = returns.rolling(window).std()
rolling_vol_daily = rolling_std * np.sqrt(STEPS_PER_DAY) * 100   # in percent for plotting

# Compute rolling Sharpe (daily)
if use_vol_floor:
    # Use the maximum of actual daily volatility and the floor (in absolute, not percent)
    vol_abs_floor = MIN_DAILY_VOL_FLOOR
    vol_for_sharpe = np.maximum(rolling_std * np.sqrt(STEPS_PER_DAY), vol_abs_floor)
    rolling_sharpe = (rolling_mean * STEPS_PER_DAY) / vol_for_sharpe
else:
    # Original formula (can spike when volatility is near zero)
    min_std = 1e-8
    rolling_std_safe = rolling_std.clip(lower=min_std)
    rolling_sharpe = (rolling_mean / rolling_std_safe) * np.sqrt(STEPS_PER_DAY)

filtered_df['rolling_vol_daily'] = rolling_vol_daily
filtered_df['rolling_sharpe_daily'] = rolling_sharpe

# --- UI ---
st.title(f"Analysis: {selected_product}")
m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Total PnL", f"{filtered_df['profit_and_loss'].iloc[-1]:,.0f}")
m2.metric("Daily Sharpe", f"{sharpe_daily:.2f}")
m3.metric("VaR (95%)", f"{var_pct:.4f}%")
m4.metric("CVaR (95%)", f"{cvar_pct:.4f}%")
m5.metric("Daily Vol", f"{vol_daily:.2f}%")
m6.metric("Max Drawdown", f"{max_dd:,.0f}")
m7.metric("Avg Spread", f"{filtered_df['spread'].mean():.2f}" if 'spread' in filtered_df.columns else "N/A")

# --- CHARTS ---
if chart_type == "Time Series":
    fig = px.line(filtered_df, x='timestamp', y=selected_metric, template="plotly_dark")
elif chart_type == "Scatter":
    df_plot = filtered_df[[second_metric, selected_metric]].dropna()
    fig = px.scatter(df_plot, x=second_metric, y=selected_metric, opacity=0.4, template="plotly_dark", trendline="ols")
elif chart_type == "Histogram":
    fig = px.histogram(filtered_df, x=selected_metric, template="plotly_dark", nbins=50)
elif chart_type == "Box":
    fig = px.box(filtered_df, y=selected_metric, template="plotly_dark")
elif chart_type == "Drawdown":
    fig = px.area(x=filtered_df['timestamp'], y=drawdown_series, template="plotly_dark", title="Underwater Drawdown (Absolute PnL)")
    fig.update_traces(fillcolor='rgba(255, 0, 0, 0.3)', line=dict(color='red'))
elif chart_type == "Rolling":
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['rolling_vol_daily'],
                             name='Daily Volatility (%)', line=dict(color='cyan', width=2)))
    fig.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['rolling_sharpe_daily'],
                             name='Daily Sharpe Ratio', line=dict(color='orange', width=2), yaxis='y2'))
    title_suffix = " (with volatility floor)" if use_vol_floor else " (no floor - may spike)"
    fig.update_layout(
        template="plotly_dark",
        title=f"Rolling Daily Metrics (Window: {window} steps){title_suffix}",
        xaxis=dict(title="Timestamp"),
        yaxis=dict(title="Daily Volatility (%)", title_font=dict(color='cyan'), tickfont=dict(color='cyan')),
        yaxis2=dict(title="Daily Sharpe Ratio", title_font=dict(color='orange'), tickfont=dict(color='orange'),
                    overlaying='y', side='right'),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)')
    )

st.plotly_chart(fig, use_container_width=True)

# --- TRADE LOG ---
with st.expander("Detailed Trade History"):
    if trade_df is not None and not trade_df.empty:
        st.dataframe(trade_df, use_container_width=True)
    else:
        st.info("No trade data available.")