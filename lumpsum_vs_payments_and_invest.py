import streamlit as st
import pandas as pd

st.title("Lump Sum vs Annual Payment Investment Calculator")
st.write("This tool helps you compare the future value of a lump sum payment against the future value of an annual payment. "
         "You can adjust the parameters to see how they affect the final balance and present value.")

# --- INPUTS ---
lump_sum_amount = st.number_input("Lump Sum Payment Amount (Present Value):", value=121637.0)
starting_balance = st.number_input("Starting Balance (after first payment deducted):", value=106837.0)
annual_payment = st.number_input("Annual Payment:", value=14800.0)
return_rate = st.number_input("Annual Return Rate (as decimal):", value=0.06, format="%.4f")
tax_rate = st.number_input("Tax Rate on Gains (as decimal):", value=0.15, format="%.4f")
discount_rate = st.number_input("Discount Rate for Present Value (as decimal):", value=0.025, format="%.4f")
years = st.number_input("Number of Years:", value=10, min_value=1, step=1)

# --- CALCULATION ---
balance = starting_balance
results = []

for year in range(1, int(years) + 1):
    if year > 1:
        balance -= annual_payment
    gross_gain = balance * return_rate
    tax = gross_gain * tax_rate
    net_gain = gross_gain - tax
    balance += net_gain
    # Present Value of balance at end of this year
    pv_balance = balance / ((1 + discount_rate) ** year)
    results.append({
        "Year": year,
        "Start Balance": round(balance - net_gain, 2),
        "Gross Gain": round(gross_gain, 2),
        "Tax": round(tax, 2),
        "Net Gain": round(net_gain, 2),
        "End Balance": round(balance, 2),
        "Present Value (End Balance)": round(pv_balance, 2)
    })

df = pd.DataFrame(results)

# --- FINAL BALANCE + PRESENT VALUE ---
final_balance = balance
present_value = final_balance / ((1 + discount_rate) ** years)

# --- DISPLAY AUDIT TABLE ---
st.subheader("Year-by-Year Audit Spreadsheet")
st.dataframe(df)  # interactive table

# --- FINAL RESULTS ---
st.subheader("Final Results")
st.write(f"Final Balance (future dollars): **${final_balance:,.2f}**")
st.write(f"Present Value of Final Balance (discounted at {discount_rate*100:.2f}% for {int(years)} years): **${present_value:,.2f}**")

# --- LUMP SUM INFO ---
st.subheader("Lump Sum Payment")
st.write(f"Lump Sum Payment Amount (Present Value): **${lump_sum_amount:,.2f}**")

# --- CONCLUSION ---
st.subheader("Conclusion")

if present_value > 0:
    st.success(
        # note the double backslash before each $ to escape it in Markdown
        f"✅ Paying annually and investing the difference results in a present value of **\\${present_value:,.2f}**, "
        f"compared to a lump sum payment of **\\${lump_sum_amount:,.2f}**.\n\n"
        f"**Conclusion:** This approach leaves you with a financial surplus of **\\${present_value:,.2f}** after {years} years."
    )
else:
    st.warning(
        f"⚠️ Paying a lump sum of **\\${lump_sum_amount:,.2f}** is financially better than annual payments.\n\n"
        f"**Conclusion:** Annual payments + investing would leave you with a present value of **\\${present_value:,.2f}** after {years} years."
    )

# --- DOWNLOAD BUTTON ---
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Download Audit Spreadsheet (CSV)", data=csv, file_name="audit_table.csv", mime="text/csv")
