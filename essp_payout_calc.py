import streamlit as st
import pandas as pd

def run_calculation(
    cola,
    pre_return,
    post_return,
    retirement_age,
    current_age,
    current_year,
    current_salary,
    bucket_df,
    contrib_type
):
    """
    Calculate year-by-year balances and final payouts for each bucket.
    
    For Amount mode:
      - 'starting_contribution' is interpreted as a dollar amount for the current year,
        which grows by COLA each year.
    
    For Percent mode:
      - 'starting_contribution' is interpreted as a decimal fraction (e.g. 0.03 for 3%)
        of current_salary. Each year's contribution is:
            current_salary * starting_contribution
        and current_salary grows by COLA each year.
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

            if contrib_type == "Amount":
                contrib = b["starting_contribution"]
            else:
                local_salary = current_salary

            while sim_year <= yr and sim_year < b["payout_year"]:
                if age < retirement_age:
                    if contrib_type == "Amount":
                        balance = (balance + contrib) * (1 + pre_return)
                        contrib *= (1 + cola)
                    else:
                        contribution_this_year = local_salary * b["starting_contribution"]
                        balance = (balance + contribution_this_year) * (1 + pre_return)
                        local_salary *= (1 + cola)
                else:
                    balance *= (1 + post_return)
                sim_year += 1
                age += 1

            row[b["name"]] = round(balance, 2) if yr < b["payout_year"] else None

        results.append(row)

    balances_df = pd.DataFrame(results)
    balances_df["Year"] = balances_df["Year"].astype(int)
    return balances_df, create_payout_df(
        buckets, cola, pre_return, post_return, retirement_age,
        current_age, current_year, current_salary, contrib_type
    )

def create_payout_df(buckets, cola, pre_return, post_return, retirement_age,
                     current_age, current_year, current_salary, contrib_type):
    """
    Compute the final payout for each bucket using the same simulation logic.
    """
    payouts = []
    for b in buckets:
        balance = b["starting_balance"]
        sim_year = current_year
        age = current_age

        if contrib_type == "Amount":
            contrib = b["starting_contribution"]
        else:
            local_salary = current_salary

        while sim_year < b["payout_year"]:
            if age < retirement_age:
                if contrib_type == "Amount":
                    balance = (balance + contrib) * (1 + pre_return)
                    contrib *= (1 + cola)
                else:
                    contribution_this_year = local_salary * b["starting_contribution"]
                    balance = (balance + contribution_this_year) * (1 + pre_return)
                    local_salary *= (1 + cola)
            else:
                balance *= (1 + post_return)
            sim_year += 1
            age += 1

        payouts.append({
            "Bucket": b["name"],
            "Payout Year": b["payout_year"],
            "Payout Amount": round(balance, 2)
        })

    return pd.DataFrame(payouts)

def main():
    st.title("ESSP Bucket Growth Calculator")

    # === Global Inputs (for user entry; no output formatting applied in the input phase) ===
    st.header("Global Inputs")
    cola = st.number_input("COLA (annual growth rate)", value=0.03,
                           min_value=0.0, max_value=1.0,
                           step=0.01, format="%.3f")
    pre_return = st.number_input("Pre-Retirement Return", value=0.07,
                                 min_value=0.0, max_value=1.0,
                                 step=0.01, format="%.3f")
    post_return = st.number_input("Post-Retirement Return", value=0.05,
                                  min_value=0.0, max_value=1.0,
                                  step=0.01, format="%.3f")
    retirement_age = st.number_input("Retirement Age", value=62, min_value=0, max_value=120, step=1)
    current_age = st.number_input("Current Age", value=58, min_value=0, max_value=120, step=1)
    current_year = st.number_input("Current Year", value=2025, min_value=1900, max_value=2100, step=1)
    current_salary = st.number_input("Current Salary", value=100000.0,
                                     min_value=0.0, format="%.2f")

    # === Contribution Type ===
    st.header("Contribution Type")
    contrib_type = st.radio("Select how you want to input contributions:",
                            options=["Amount", "Percent"])

    # === Bucket Data Inputs ===
    st.header("ESSP Bucket Inputs")
    st.write(
        f"Below, 'starting_contribution' is interpreted as a "
        f"{'dollar amount' if contrib_type == 'Amount' else 'decimal fraction for the rate (e.g. 0.03 for 3%)'}."
    )
    if contrib_type == "Amount":
        default_contributions = [5000, 3000, 7500, 1000, 5000, 2000]
        contrib_label = "Starting Contribution Amount"
    else:
        # Updated defaults (rounded to two decimals) for Percent mode
        default_contributions = [0.05, 0.03, 0.08, 0.01, 0.05, 0.02]
        contrib_label = "Starting Contribution (Decimal Rate)"
    
    default_data = {
        "name": ["Bucket 1", "Bucket 2", "Bucket 3", "Bucket 4", "Bucket 5", "Retirement Bucket"],
        "starting_balance": [30000.00, 20000.00, 40000.00, 8000.00, 25000.00, 15000.00],
        "starting_contribution": default_contributions,
        "payout_year": [2032, 2033, 2034, 2035, 2036, 2030]
    }
    default_bucket_df = pd.DataFrame(default_data)

    # In the data editor, we now do not force any display format so that input remains flexible.
    bucket_df = st.data_editor(
        default_bucket_df,
        key="bucket_data_editor",
        column_config={
            "payout_year": st.column_config.NumberColumn("Payout Year", format="%d"),
            "starting_balance": st.column_config.NumberColumn("Starting Balance"),
            "starting_contribution": st.column_config.NumberColumn(contrib_label),
        }
    )
    st.markdown("All numeric columns must be valid numbers; no text or blank cells.")

    # === Run Calculation ===
    if st.button("Run Calculation"):
        # Convert columns to numeric
        for col in ["starting_balance", "starting_contribution", "payout_year"]:
            bucket_df[col] = pd.to_numeric(bucket_df[col], errors="coerce")
        invalid_df = bucket_df[bucket_df[["starting_balance", "starting_contribution", "payout_year"]].isna().any(axis=1)]
        if not invalid_df.empty:
            st.error(f"Some rows have invalid numeric values:\n{invalid_df}")
            st.stop()
        invalid_values = bucket_df.query("starting_balance < 0 or starting_contribution < 0 or payout_year <= 0")
        if not invalid_values.empty:
            st.error("One or more rows have invalid values. "
                     " - Starting balance and contribution must be >= 0.\n"
                     " - Payout year must be > 0.\n\n" + str(invalid_values))
            st.stop()

        df_balances, df_payouts = run_calculation(
            cola=cola,
            pre_return=pre_return,
            post_return=post_return,
            retirement_age=retirement_age,
            current_age=current_age,
            current_year=current_year,
            current_salary=current_salary,
            bucket_df=bucket_df,
            contrib_type=contrib_type
        )

        # ---- FORCE FORMATTING ON OUTPUT ----
        # Format year-by-year balances: Year and Age as integers; monetary columns with commas and two decimals.
        format_dict_bal = {"Year": "{:.0f}", "Age": "{:.0f}"}
        for col in df_balances.columns:
            if col not in ["Year", "Age"]:
                format_dict_bal[col] = "{:,.2f}"
        df_balances_styled = df_balances.style.format(format_dict_bal)
        st.subheader("ESSP Year-by-Year Balances")
        st.dataframe(df_balances_styled, use_container_width=True)

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


