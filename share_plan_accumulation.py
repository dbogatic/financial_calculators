import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# App title
st.title("Share Plan Accumulation Calculator")

# User inputs
start_year = st.number_input("Start Year", value=2032, step=1)
end_year = st.number_input("End Year", value=2044, step=1)
shares_per_year = st.number_input("Shares Received Annually", value=1080)
share_price = st.number_input("Average Share Price ($)", value=32.0)
tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=28.0) / 100
growth_rate = st.number_input("Annual Growth Rate (%)", min_value=0.0, max_value=15.0, value=5.0) / 100

# Calculate years
years = list(range(int(start_year), int(end_year) + 1))

# Initialize DataFrame
df = pd.DataFrame({
    "Year": years,
    "Shares Received": shares_per_year,
    "Share Price": share_price
})

# Calculations
df["Gross Value"] = df["Shares Received"] * df["Share Price"]
df["Tax Rate"] = tax_rate
df["Net Value"] = df["Gross Value"] * (1 - df["Tax Rate"])

# Accumulate with compounding
accumulated = 0
accumulated_values = []
for net in df["Net Value"]:
    accumulated += net
    accumulated *= (1 + growth_rate)
    accumulated_values.append(accumulated)

df["Accumulated Value"] = accumulated_values

# Output results
st.subheader("Accumulation Table")
st.dataframe(df.style.format({"Gross Value": "${:,.2f}", "Net Value": "${:,.2f}", "Accumulated Value": "${:,.2f}"}))

# Show final value
st.metric("Final Accumulated Value", f"${accumulated:,.2f}")

# Plot
st.subheader("Accumulated Value Over Time")
fig, ax = plt.subplots()
ax.set_title("Accumulated Value Over Time")
ax.plot(df["Year"], df["Accumulated Value"], marker='o')
ax.set_xlabel("Year")
ax.set_ylabel("Cumulative Value ($)")
ax.grid(True)
st.pyplot(fig)