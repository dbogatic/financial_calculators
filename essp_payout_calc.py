import streamlit as st
import pandas as pd

def run_calculation(
    cola,
    retirement_age,
    current_age,
    current_year,
    current_salary,
    bucket_df,
    contrib_type
):
    """
    Calculate year-by-year balances and final payouts for each bucket.

    Each bucket uses its own specific return rate from the `return_rate` column.
    """
    buckets = bucket_df.to_dict(orient="records")
    max_payout_year = max(b["payout_year"] for b in buckets)
    years = list(range(current_year, max_payout_year))  # simulate until the year before payout

    results = []
    for yr in years:
        row = {
            "Year": yr,
            "Age": current_age + (yr - current_year),
        }
        for b in buckets:
            balance = b["starting_balance"]
            sim_year = current_year
            age = current_age
            return_rate = b["return_rate"]  # Use the specific return rate for this bucket

            if contrib_type == "Amount":
                contrib = b["starting_contribution"]
            else:
                local_salary = current_salary

            while sim_year <= yr and sim_year < b["payout_year"]:
                if age < retirement_age:
                    if contrib_type == "Amount":
                        balance = (balance + contrib) * (1 + return_rate)
                        contrib *= (1 + cola)
                    else:
                        contribution_this_year = local_salary * b["starting_contribution"]
                        balance = (balance + contribution_this_year) * (1 + return_rate)
                        local_salary *= (1 + cola)
                else:
                    balance *= (1 + return_rate)  # Use the same return rate after retirement
                sim_year += 1
                age += 1

            row[b["name"]] = round(balance, 2) if yr < b["payout_year"] else None
        results.append(row)

    balances_df = pd.DataFrame(results)
    balances_df["Year"] = balances_df["Year"].astype(int)
    return balances_df, create_payout_df(
        buckets, cola, retirement_age, current_age, current_year, current_salary, contrib_type
    )

def create_payout_df(buckets, cola, retirement_age, current_age, current_year, current_salary, contrib_type):
    """
    Compute the final payout for each bucket using the specific return rate for each bucket.
    """
    payouts = []
    for b in buckets:
        balance = b["starting_balance"]
        sim_year = current_year
        age = current_age
        return_rate = b["return_rate"]  # Use the specific return rate for this bucket

        if contrib_type == "Amount":
            contrib = b["starting_contribution"]
        else:
            local_salary = current_salary

        while sim_year < b["payout_year"]:
            if age < retirement_age:
                if contrib_type == "Amount":
                    balance = (balance + contrib) * (1 + return_rate)
                    contrib *= (1 + cola)
                else:
                    contribution_this_year = local_salary * b["starting_contribution"]
                    balance = (balance + contribution_this_year) * (1 + return_rate)
                    local_salary *= (1 + cola)
            else:
                balance *= (1 + return_rate)  # Use the same return rate after retirement
            sim_year += 1
            age += 1

        payouts.append({
            "Bucket": b["name"],
            "Payout Year": b["payout_year"],
            "Payout Amount": round(balance, 2)
        })

    return pd.DataFrame(payouts)

def main():
    st.title("Bucket Growth Calculator")

    # === Global Inputs (raw numeric entry) ===
    st.header("Global Inputs")
    current_salary = st.number_input("Current Salary", value=100000.0, min_value=0.0)
    cola = st.number_input("COLA (annual growth rate)", value=0.03, min_value=0.0, max_value=1.0, step=0.01)
    retirement_age = st.number_input("Retirement Age", value=62, min_value=0, max_value=120, step=1)
    current_age = st.number_input("Current Age", value=58, min_value=0, max_value=120, step=1)
    current_year = st.number_input("Current Year", value=2025, min_value=1900, max_value=2100, step=1)

    # === Contribution Type ===
    st.header("Contribution Type")
    contrib_type = st.radio("Select how you want to input contributions:", options=["Amount", "Percent"])

    # === Bucket Data Inputs with Explanation ===
    st.header("Bucket Inputs")
    st.write(
    "Please enter the raw numeric values—do not include comma separators. Decimals are allowed.\n\n"
    "For 'Starting Balance' and 'Starting Contribution Amount' (if using Amount mode), "
    "enter the full monetary value (e.g., 1000000.56 should be entered as 1000000.56).\n"
    "For 'Return Rate' (in both modes), enter the rate as a decimal fraction (e.g., 0.07 for 7%).\n"
    "For 'Starting Contribution (Decimal Rate)' (if using Percent mode), enter the rate as a decimal fraction (e.g., 0.03 for 3%)."
)
    if contrib_type == "Amount":
        # Use float defaults with two decimals
        default_contributions = [5000.00, 3000.00, 7500.00, 1000.00, 5000.00, 2000.00]
        contrib_label = "Starting Contribution Amount"
    else:
        default_contributions = [0.05, 0.03, 0.08, 0.01, 0.05, 0.02]
        contrib_label = "Starting Contribution (Decimal Rate)"

    default_data = {
        "name": ["Bucket 1", "Bucket 2", "Bucket 3", "Bucket 4", "Bucket 5", "Retirement Bucket"],
        "starting_balance": [30000.00, 20000.00, 40000.00, 8000.00, 25000.00, 15000.00],
        "starting_contribution": default_contributions,
        "payout_year": [2032, 2033, 2034, 2035, 2036, 2030],
        "return_rate": [0.07, 0.06, 0.08, 0.05, 0.07, 0.04]  # Example return rates for each bucket
    }
    default_bucket_df = pd.DataFrame(default_data)

    # Do not set a forced format in the data editor so that full precision can be entered.
    bucket_df = st.data_editor(
        default_bucket_df,
        key="bucket_data_editor",
        column_config={
            "payout_year": st.column_config.NumberColumn("Payout Year", format="%d"),
            "starting_balance": st.column_config.NumberColumn("Starting Balance"),
            "starting_contribution": st.column_config.NumberColumn(contrib_label),
            "return_rate": st.column_config.NumberColumn("Return Rate (Decimal)", format="%.2f"),
        }
    )
    st.markdown("Ensure that all numeric cells contain valid numbers; no text or blank cells are allowed.")

    # === Run Calculation ===
    if st.button("Run Calculation"):
        # Convert specific columns to numeric
        for col in ["starting_balance", "starting_contribution", "payout_year", "return_rate"]:
            bucket_df[col] = pd.to_numeric(bucket_df[col], errors="coerce")
        invalid_df = bucket_df[bucket_df[["starting_balance", "starting_contribution", "payout_year", "return_rate"]].isna().any(axis=1)]
        if not invalid_df.empty:
            st.error(f"Some rows contain invalid numeric values:\n{invalid_df}")
            st.stop()
        invalid_values = bucket_df.query("starting_balance < 0 or starting_contribution < 0 or payout_year <= 0 or return_rate < 0")
        if not invalid_values.empty:
            st.error(
                "One or more rows have invalid values.\n"
                " - Starting balance, contribution, and return rate must be >= 0.\n"
                " - Payout year must be > 0.\n\n" + str(invalid_values)
            )
            st.stop()

        df_balances, df_payouts = run_calculation(
            cola=cola,
            retirement_age=retirement_age,
            current_age=current_age,
            current_year=current_year,
            current_salary=current_salary,
            bucket_df=bucket_df,
            contrib_type=contrib_type
        )

        # ---- FORCE FORMATTING ON OUTPUT (Using Pandas' Styler) ----
        # Format year-by-year balances: Year and Age as integers; other columns as monetary values with commas and two decimals.
        format_dict_bal = {"Year": "{:.0f}", "Age": "{:.0f}"}
        for col in df_balances.columns:
            if col not in ["Year", "Age"]:
                format_dict_bal[col] = "{:,.2f}"
        df_balances_styled = df_balances.style.format(format_dict_bal)
        st.subheader("Year-by-Year Balances")
        st.dataframe(df_balances_styled, use_container_width=True)

        # Format final payouts: Payout Year as integer; Payout Amount as monetary value.
        df_payouts_styled = df_payouts.style.format({
            "Payout Year": "{:.0f}",
            "Payout Amount": "{:,.2f}"
        })
        st.subheader("ESSP Final Payouts")
        st.dataframe(df_payouts_styled, use_container_width=True)

        st.download_button(
            label="Download Year-by-Year as CSV",
            data=df_balances.to_csv(index=False).encode("utf-8"),
            file_name="yearly_balances.csv",
            mime="text/csv"
        )
        st.download_button(
            label="Download Final Payouts as CSV",
            data=df_payouts.to_csv(index=False).encode("utf-8"),
            file_name="bucket_payouts.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()