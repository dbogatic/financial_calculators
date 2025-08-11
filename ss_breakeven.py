# app.py — Social Security Breakeven (DOB-accurate)
# - Inputs: DOB, "today" date, claim ages + monthly benefits (today's $)
# - Toggle: apply COLA from today (pre-claim + post-claim), timing (Jan/B-day), SSA lag
# - Outputs: totals to horizon, year-by-year cumulative table, breakeven table, chart

import math
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ==========================
# Core calculation helpers
# ==========================

def first_of_next_month(d: date) -> date:
    return date(d.year + (1 if d.month == 12 else 0), 1 if d.month == 12 else d.month + 1, 1)

def age_years_fraction(dob: date, d: date) -> float:
    return (d.year - dob.year) + (d.month - dob.month) / 12.0

def claim_month(dob: date, claim_age: int) -> date:
    return date(dob.year + claim_age, dob.month, 1)

def first_payment_month(dob: date, claim_age: int, use_payment_lag: bool) -> date:
    start = claim_month(dob, claim_age)
    return first_of_next_month(start) if use_payment_lag else start

def end_boundary_month(dob: date, end_age: int) -> date:
    # exclusive boundary (month of the birthday)
    return date(dob.year + end_age, dob.month, 1)

def count_preclaim_steps_january(current_date: date, first_pay_month: date) -> int:
    # January steps strictly after "today" and strictly before first payment
    first_jan = date(current_date.year + (1 if current_date >= date(current_date.year,1,1) else 0), 1, 1)
    if first_jan <= current_date:
        first_jan = date(current_date.year+1, 1, 1)
    steps, d = 0, first_jan
    while d < first_pay_month:
        steps += 1
        d = date(d.year+1, 1, 1)
    return steps

def count_preclaim_steps_birthday(dob: date, current_date: date, claim_age: int) -> int:
    # birthdays strictly after "today" and strictly before the claim birthday
    next_bd_year = current_date.year if (current_date.month, current_date.day) < (dob.month, dob.day) else current_date.year + 1
    d = date(next_bd_year, dob.month, 1)
    steps = 0
    while d < claim_month(dob, claim_age):
        steps += 1
        d = date(d.year+1, dob.month, 1)
    return steps

def years_since_claim_birthday(dob: date, d: date, claim_age: int) -> int:
    cm = claim_month(dob, claim_age)
    if d < cm:
        return 0
    years = d.year - cm.year
    if (d.month, d.day) < (cm.month, cm.day):
        years -= 1
    return max(0, years)

def build_monthly_series(
    dob: date,
    current_date: date,
    claim_age: int,
    monthly_at_claim_today: float,
    horizon_age: int,
    cola_rate: float,
    apply_cola_from_today: bool,
    cola_timing: str,           # 'january' | 'birthday'
    use_payment_lag: bool
) -> List[Tuple[date, float]]:
    """Return [(month_date, cumulative_future_$)] from first payment through horizon."""
    # starting amount at claim after optional pre-claim COLA
    start_m = first_payment_month(dob, claim_age, use_payment_lag)
    if apply_cola_from_today and cola_rate > 0:
        if cola_timing == "january":
            steps = count_preclaim_steps_january(current_date, start_m)
        else:
            steps = count_preclaim_steps_birthday(dob, current_date, claim_age)
        start_amt = monthly_at_claim_today * (1.0 + cola_rate) ** steps
    else:
        start_amt = monthly_at_claim_today

    # iterate months
    end_ex = end_boundary_month(dob, horizon_age)
    months = []
    d = start_m
    while d < end_ex:
        months.append(d)
        d = first_of_next_month(d)

    series, cum, amt = [], 0.0, start_amt
    for d in months:
        # post-claim COLA
        if apply_cola_from_today and cola_rate > 0:
            if cola_timing == "birthday":
                k = years_since_claim_birthday(dob, d, claim_age)
                amt = start_amt * (1.0 + cola_rate) ** k
            # 'january' bumps after writing this month, for next month

        cum += amt
        series.append((d, cum))

        if apply_cola_from_today and cola_rate > 0 and cola_timing == "january":
            nxt = first_of_next_month(d)
            if nxt.month == 1:
                amt *= (1.0 + cola_rate)
    return series

def align_series(sa: List[Tuple[date, float]], sb: List[Tuple[date, float]]):
    months = sorted(set([d for d,_ in sa]) | set([d for d,_ in sb]))
    la, lb = {d:v for d,v in sa}, {d:v for d,v in sb}
    out_a, out_b = [], []
    pa = pb = 0.0
    for d in months:
        if d in la: pa = la[d]
        if d in lb: pb = lb[d]
        out_a.append((d, pa)); out_b.append((d, pb))
    return out_a, out_b

def find_breakeven_month(sa, sb) -> Optional[date]:
    if not sa or not sb:
        return None
    a, b = align_series(sa, sb)
    for i in range(1, len(a)):
        d0, y0 = a[i-1][0], a[i-1][1] - b[i-1][1]
        d1, y1 = a[i][0],   a[i][1]   - b[i][1]
        if y0 == 0:
            return d0
        if y0 * y1 < 0:
            return d1  # month granularity is fine
    return None

def fmt_age(dob: date, d: Optional[date]) -> str:
    if d is None:
        return "—"
    y = d.year - dob.year
    m = d.month - dob.month
    if m < 0:
        y -= 1; m += 12
    return f"{y}y {m}m"

def cumulative_at_age(series: List[Tuple[date, float]], dob: date, end_age: int) -> float:
    """Cumulative through the month before end_age birthday."""
    if not series: return 0.0
    boundary = end_boundary_month(dob, end_age)
    last = 0.0
    for d, v in series:
        if d < boundary: last = v
        else: break
    return last

# ==========================
# Streamlit UI
# ==========================
st.set_page_config(page_title="Social Security Breakeven", layout="wide")
st.title("Social Security Breakeven")

with st.sidebar:
    st.header("Inputs")
    dob = st.date_input("Date of birth", value=date(1965, 5, 15))
    current_date = st.date_input("Today's date (for COLA anchor)", value=date.today())
    cola_rate = st.number_input("Annual COLA (%)", value=3.0, min_value=0.0, max_value=10.0, step=0.1) / 100.0
    apply_cola_from_today = st.checkbox("Apply COLA from 'today' (pre- & post-claim)", value=False)
    cola_timing = st.selectbox("COLA timing", options=["january", "birthday"], index=0)
    use_payment_lag = st.checkbox("SSA 1-month payment lag", value=False)
    horizon_age = st.slider("Projection horizon (age)", min_value=70, max_value=100, value=92, step=1)

    st.markdown("---")
    st.subheader("Claim ages & monthly benefits (today's $)")
    default_df = pd.DataFrame(
        {"Claim Age": [62, 67, 70], "Monthly Benefit": [1800.0, 2500.0, 3100.0]}
    )
    claim_df = st.data_editor(default_df, num_rows="dynamic", key="claims")
    # sanitize
    claim_df = claim_df.dropna()
    claim_df["Claim Age"] = claim_df["Claim Age"].astype(int)
    claim_df["Monthly Benefit"] = claim_df["Monthly Benefit"].astype(float)

# Build series for each claim age
claim_amounts = {int(row["Claim Age"]): float(row["Monthly Benefit"]) for _, row in claim_df.iterrows()}

series_map: Dict[int, List[Tuple[date, float]]] = {}
for age, amt in sorted(claim_amounts.items()):
    series_map[age] = build_monthly_series(
        dob=dob,
        current_date=current_date,
        claim_age=age,
        monthly_at_claim_today=amt,
        horizon_age=horizon_age,
        cola_rate=cola_rate,
        apply_cola_from_today=apply_cola_from_today,
        cola_timing=cola_timing,
        use_payment_lag=use_payment_lag
    )

# Totals table
totals = {age: (ser[-1][1] if ser else 0.0) for age, ser in series_map.items()}
totals_df = pd.DataFrame({
    "Claim Age": list(totals.keys()),
    f"Total to age {horizon_age} (Future $)": [totals[a] for a in totals.keys()]
}).sort_values("Claim Age")

# Year-by-year cumulative table
age_grid = list(range(min(claim_amounts), horizon_age + 1))
rows = []
for cut in age_grid:
    row = {"Age": cut}
    for age in sorted(claim_amounts):
        row[f"Claim {age}"] = cumulative_at_age(series_map[age], dob, cut)
    rows.append(row)
yearly_df = pd.DataFrame(rows)

# Breakeven table
pairs = []
ages_sorted = sorted(claim_amounts)
for i in range(len(ages_sorted)):
    for j in range(i+1, len(ages_sorted)):
        a1, a2 = ages_sorted[i], ages_sorted[j]
        bm = find_breakeven_month(series_map[a1], series_map[a2])
        pairs.append({"Pair": f"{a1} vs {a2}", "Breakeven (YYy MMm)": fmt_age(dob, bm)})
breakeven_df = pd.DataFrame(pairs)

# Layout
col1, col2 = st.columns([1.1, 1])
with col1:
    st.subheader("Totals to Horizon (Future $)")
    st.dataframe(totals_df.reset_index(drop=True).style.format({totals_df.columns[1]: "{:,.2f}"}), use_container_width=True)

    st.subheader("Year-by-Year Cumulative (Future $)")
    st.dataframe(yearly_df.style.format({c: "{:,.2f}" for c in yearly_df.columns if c != "Age"}), use_container_width=True)

with col2:
    st.subheader("Breakeven (Future $)")
    st.dataframe(breakeven_df, use_container_width=True)

    # Chart: pick pair to plot
    st.markdown("---")
    st.subheader("Breakeven Chart")
    pair = st.selectbox("Compare pair", options=[f"{a} vs {b}" for i,a in enumerate(ages_sorted) for b in ages_sorted[i+1:]])
    a_str, b_str = pair.split(" vs ")
    pa, pb = int(a_str), int(b_str)
    sa, sb = series_map[pa], series_map[pb]

    # Prepare plot arrays
    x_a = [age_years_fraction(dob, d) for d,_ in sa]; y_a = [v for _,v in sa]
    x_b = [age_years_fraction(dob, d) for d,_ in sb]; y_b = [v for _,v in sb]
    bm = find_breakeven_month(sa, sb)

    fig = plt.figure(figsize=(5.5, 3.6))
    plt.plot(x_a, y_a, label=f"Claim {pa}")
    plt.plot(x_b, y_b, label=f"Claim {pb}")
    if bm is not None:
        bx = age_years_fraction(dob, bm)
        # get y at breakeven month from aligned series
        a_al, _ = align_series(sa, sb)
        y_be = next(v for d,v in a_al if d == bm)
        plt.axvline(bx, linestyle="--", label=f"Breakeven {fmt_age(dob, bm)}")
        plt.scatter([bx], [y_be])
    plt.xlabel("Age (years)")
    plt.ylabel("Cumulative benefits (future $)")
    plt.title(f"Cumulative Benefits: Claim {pa} vs {pb}")
    plt.legend()
    plt.tight_layout()
    st.pyplot(fig)

# Footer note
st.caption(
    "Notes: (1) Benefits entered are monthly in today's dollars at each claim age. "
    "(2) When 'Apply COLA from today' is on, benefits are stepped annually by the selected timing "
    "both before and after claiming. (3) Breakeven is calculated in future (inflated) dollars on a monthly grid."
)
