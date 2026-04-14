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
MIN_DAILY_VOL_FLOOR = 0.001

st.set_page_config(page_title="IMC Analytics Pro", layout="wide")

# --- DATA LOADING ---
LOG_DIR = Path(__file__).parent.parent / "backtests"

@st.cache_data(show_spinner=False)
def get_backtest_data(file_path, mtime):
    # Using the parse function from your environment
    act_df, trade_df, _ = parse(file_path)
    if act_df is not None and not act_df.empty:
        act_df = act_df.copy()
        if 'ask_price_1' in act_df.columns and 'bid_price_1' in act_df.columns:
            act_df['spread'] = act_df['ask_price_1'] - act_df['bid_price_1']
            act_df['spread_pct'] = act_df['spread'] / act_df['mid_price']
    return act_df, trade_df

# --- RISK METRICS FUNCTIONS ---
def calculate_day_adjusted_metrics(returns):
    if returns is None or len(returns) == 0: return 0, 0, 0
    var_95 = np.percentile(returns, 5) * 100
    vol_step = returns.std()
    vol_daily = vol_step * np.sqrt(STEPS_PER_DAY)
    mean_step = returns.mean()
    sharpe_daily = (mean_step * STEPS_PER_DAY) / vol_daily if vol_daily != 0 else 0
    return var_95, vol_daily * 100, sharpe_daily

def calculate_cvar(returns):
    if returns is None or len(returns) == 0: return 0
    var_threshold = np.percentile(returns, 5)
    return returns[returns <= var_threshold].mean() * 100

def calculate_drawdown(pnl):
    running_max = pnl.cummax()
    drawdown_abs = pnl - running_max
    return drawdown_abs, drawdown_abs.min()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Global Controls")
log_files = list(LOG_DIR.glob("*.log")) + list(LOG_DIR.glob("*.txt"))
if not log_files:
    st.error("No logs found.")
    st.stop()

selected_file = st.sidebar.selectbox("Log File", log_files, format_func=lambda x: x.name)
act_df, trade_df = get_backtest_data(selected_file, selected_file.stat().st_mtime)

products = act_df['product'].unique()
selected_product = st.sidebar.selectbox("Product", products)
filtered_df = act_df[act_df['product'] == selected_product].copy().sort_values('timestamp')

# Filter 0 mid prices
if st.sidebar.toggle("Filter 0 Mid Prices", value=True):
    filtered_df = filtered_df[filtered_df['mid_price'] != 0]

# --- APP LAYOUT ---
st.title(f"Analysis: {selected_product}")
tab1, tab2 = st.tabs(["📈 Performance & Charts", "🔬 Strategy Research"])

# --- TAB 1: ORIGINAL PERFORMANCE & CHARTS ---
with tab1:
    # Calculations
    filtered_df['returns_pct'] = filtered_df['profit_and_loss'].diff().fillna(0) / CAPITAL
    var_pct, vol_daily, sharpe_daily = calculate_day_adjusted_metrics(filtered_df['returns_pct'])
    cvar_pct = calculate_cvar(filtered_df['returns_pct'])
    drawdown_series, max_dd = calculate_drawdown(filtered_df['profit_and_loss'])

    # Metrics Row
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total PnL", f"{filtered_df['profit_and_loss'].iloc[-1]:,.0f}")
    m2.metric("Daily Sharpe", f"{sharpe_daily:.2f}")
    m3.metric("Daily Vol", f"{vol_daily:.2f}%")
    m4.metric("Max Drawdown", f"{max_dd:,.0f}")
    m5.metric("VaR (95%)", f"{var_pct:.4f}%")
    m6.metric("Avg Spread", f"{filtered_df['spread'].mean():.2f}" if 'spread' in filtered_df.columns else "N/A")

    # Standard Chart Selection
    exclude = ['day', 'timestamp', 'product']
    metrics_list = [c for c in filtered_df.columns if c not in exclude]
    
    col_chart, col_opt = st.columns([4, 1])
    chart_choice = col_opt.radio("Chart Type", ["Time Series", "Scatter", "Histogram", "Drawdown"])
    
    if chart_choice == "Time Series":
        y_val = col_opt.selectbox("Y-axis", metrics_list, index=metrics_list.index('mid_price'))
        fig = px.line(filtered_df, x='timestamp', y=y_val, template="plotly_dark")
    elif chart_choice == "Scatter":
        x_val = col_opt.selectbox("X-axis", metrics_list, index=metrics_list.index('bid_volume_1'))
        y_val = col_opt.selectbox("Y-axis", metrics_list, index=metrics_list.index('mid_price'))
        fig = px.scatter(filtered_df, x=x_val, y=y_val, opacity=0.4, template="plotly_dark", trendline="ols")
    elif chart_choice == "Histogram":
        h_val = col_opt.selectbox("Metric", metrics_list)
        fig = px.histogram(filtered_df, x=h_val, template="plotly_dark", nbins=50)
    elif chart_choice == "Drawdown":
        fig = px.area(x=filtered_df['timestamp'], y=drawdown_series, template="plotly_dark")
        fig.update_traces(fillcolor='rgba(255, 0, 0, 0.3)', line=dict(color='red'))

    col_chart.plotly_chart(fig, use_container_width=True)

    with st.expander("Detailed Trade History"):
        if trade_df is not None and not trade_df.empty:
            st.dataframe(trade_df, use_container_width=True)
        else:
            st.info("No trade data available.")

# --- TAB 2: ADVANCED ANALYTICS & FILTERS ---
with tab2:
    st.subheader("Statistical Signals & Entry Filters")
    
    # 1. Parameter Settings
    c1, c2, c3, c4 = st.columns(4)
    z_entry = c1.slider("Z-Entry (abs)", 0.0, 5.0, 2.0, 0.1)
    trend_limit = c2.slider("Trend Limit (Slope)", 0.0, 5.0, 1.0, 0.1)
    spread_max = c3.slider("Max Allowed Spread", 0.0, 20.0, 4.0, 0.5)
    ac_cutoff = c4.slider("Autocorr Cutoff", -1.0, 1.0, -0.1, 0.05)
    
    window = st.number_input("Analysis Window (Steps)", 10, 5000, 100)

    # 2. Signal Calculations
    roll_mean = filtered_df['mid_price'].rolling(window).mean()
    roll_std = filtered_df['mid_price'].rolling(window).std()
    filtered_df['zscore'] = (filtered_df['mid_price'] - roll_mean) / roll_std
    
    rets = filtered_df['mid_price'].diff()
    filtered_df['autocorr'] = rets.rolling(window).corr(rets.shift(1))
    
    def calc_slope(y):
        if len(y) < 2 or np.any(np.isnan(y)): return 0.0
        return np.polyfit(np.arange(len(y)), y, 1)[0]
    filtered_df['trend'] = filtered_df['mid_price'].rolling(window).apply(calc_slope, raw=True)

    # 3. Apply Filter Logic
    # We define "Signal Blocked" based on your provided criteria
    filtered_df['blocked'] = (
        (roll_std == 0) | 
        (filtered_df['trend'].abs() > trend_limit) | 
        (filtered_df['spread'] > spread_max) | 
        (filtered_df['zscore'].abs() < z_entry) | 
        (filtered_df['autocorr'] > ac_cutoff)
    )
    
    # 4. Visualization
    # Z-Score Plot
    fig_z = go.Figure()
    fig_z.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['zscore'], name="Z-Score", line=dict(color='#00d4ff')))
    fig_z.add_hline(y=z_entry, line_dash="dash", line_color="red", annotation_text="Entry Threshold")
    fig_z.add_hline(y=-z_entry, line_dash="dash", line_color="red")
    fig_z.update_layout(title="Rolling Z-Score & Entry Thresholds", template="plotly_dark", height=350)
    st.plotly_chart(fig_z, use_container_width=True)

    # Secondary Signals
    sc1, sc2 = st.columns(2)
    
    fig_ac = go.Figure()
    fig_ac.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['autocorr'], name="Autocorr", line=dict(color='orange')))
    fig_ac.add_hline(y=ac_cutoff, line_dash="dash", line_color="white", annotation_text="MR Threshold")
    fig_ac.update_layout(title="Rolling Autocorrelation", template="plotly_dark", height=300)
    sc1.plotly_chart(fig_ac, use_container_width=True)

    fig_tr = go.Figure()
    fig_tr.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['trend'], name="Trend", line=dict(color='magenta')))
    fig_tr.add_hline(y=trend_limit, line_dash="dash", line_color="yellow")
    fig_tr.add_hline(y=-trend_limit, line_dash="dash", line_color="yellow", annotation_text="Trend Limit")
    fig_tr.update_layout(title="Trend Slope (Velocity)", template="plotly_dark", height=300)
    sc2.plotly_chart(fig_tr, use_container_width=True)

    # Summary Analysis
    active_mask = ~filtered_df['blocked']
    active_pct = (active_mask.sum() / len(filtered_df)) * 100
    st.metric("Signal Market Connectivity", f"{active_pct:.1f}%", help="Percentage of time steps where all entry filters are satisfied.")