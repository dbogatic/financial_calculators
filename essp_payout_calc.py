import streamlit as st
import pandas as pd

def run_calculation(cola, pre_return, post_return, retirement_age, current_age, current_year, bucket_df):
    """
    Calculate year-by-year balances and final payouts.
    Returns two DataFrames:
      1) Yearly balances up to each bucket's payout year
      2) Final payouts for each bucket
    """
    bucket_data = bucket_df.to_dict(orient="records")

    # === Determine max year for iteration
    max_year = max(b["payout_year"] for b in bucket_data) - 1
    years = list(range(current_year, max_year + 1))

    # === Year-by-Year Balances
    results = []
    for year in years:
        row = {
            "Year": year,
            "Age": current_age + (year - current_year)
        }
        for bucket in bucket_data:
            balance = bucket["starting_balance"]
            contrib = bucket["starting_contribution"]
            age = current_age
            sim_year = current_year

            while sim_year <= year and sim_year < bucket["payout_year"]:
                if age < retirement_age:
                    balance = (balance + contrib) * (1 + pre_return)
                    contrib *= (1 + cola)
                else:
                    balance *= (1 + post_return)
                sim_year += 1
                age += 1

            # Only show balance if before payout
            if year < bucket["payout_year"]:
                row[bucket["name"]] = round(balance, 2)
            else:
                row[bucket["name"]] = None

        results.append(row)

    df = pd.DataFrame(results)
    df["Year"] = df["Year"].astype(int)  # Make Year column integer

    # === Final Payouts
    payouts = []
    for bucket in bucket_data:
        balance = bucket["starting_balance"]
        contrib = bucket["starting_contribution"]
        age = current_age
        sim_year = current_year
        payout_year = bucket["payout_year"]

        while sim_year < payout_year:
            if age < retirement_age:
                balance = (balance + contrib) * (1 + pre_return)
                contrib *= (1 + cola)
            else:
                balance *= (1 + post_return)
            sim_year += 1
            age += 1

        payouts.append({
            "Bucket": bucket["name"],
            "Payout Year": payout_year,
            "Payout Amount": round(balance, 2)
        })

    payout_df = pd.DataFrame(payouts)
    return df, payout_df

def main():
    st.title("ESSP Bucket Growth Calculator")

    # == Global Inputs ==
    st.header("Global Inputs")
    cola = st.number_input("COLA", value=0.03, min_value=0.0, max_value=1.0, step=0.01, format="%.3f")
    pre_return = st.number_input("Pre-Retirement Return", value=0.07, min_value=0.0, max_value=1.0, step=0.01, format="%.3f")
    post_return = st.number_input("Post-Retirement Return", value=0.05, min_value=0.0, max_value=1.0, step=0.01, format="%.3f")
    retirement_age = st.number_input("Retirement Age", value=62, min_value=0, max_value=120, step=1)
    current_age = st.number_input("Current Age", value=58, min_value=0, max_value=120, step=1)
    current_year = st.number_input("Current Year", value=2025, min_value=1900, max_value=2100, step=1)

    # == Bucket Data ==
    st.header("ESSP Bucket Inputs")
    st.write("Enter or edit data for each bucket below.")

    default_data = {
        "name": [
            "Bucket 1", 
            "Bucket 2", 
            "Bucket 3", 
            "Bucket 4", 
            "Bucket 5", 
            "Retirement Bucket"
        ],
        "starting_balance": [37367, 31726, 58548, 57609, 93648, 55732],
        "starting_contribution": [9925, 13720, 10217, 4087, 9925, 7210],
        "payout_year": [2032, 2033, 2034, 2035, 2036, 2030]
    }

    default_bucket_df = pd.DataFrame(default_data)

    # Fixed rows; no num_rows="dynamic"
    bucket_df = st.data_editor(
        default_bucket_df,
        key="bucket_data_editor",
    )

    st.markdown(
        "All numeric columns must be valid numbers; no text or blank cells."
    )

    # == Calculate Button ==
    if st.button("Run Calculation"):
        # Attempt numeric conversions
        for col in ["starting_balance", "starting_contribution", "payout_year"]:
            bucket_df[col] = pd.to_numeric(bucket_df[col], errors="coerce")

        # Identify invalid rows
        invalid_rows = bucket_df[bucket_df[["starting_balance",
                                            "starting_contribution",
                                            "payout_year"]].isna().any(axis=1)]
        if not invalid_rows.empty:
            st.error(
                f"The following rows have invalid numeric values (NaN). "
                "Please correct them before running the calculation:\n\n"
                f"{invalid_rows}"
            )
            st.stop()

        # Additional checks
        invalid_rows_2 = bucket_df.query("starting_balance < 0 or starting_contribution < 0 or payout_year <= 0")
        if len(invalid_rows_2) > 0:
            st.error(
                "One or more buckets have invalid values:\n"
                " - Starting balance/contribution cannot be negative.\n"
                " - Payout year must be greater than 0.\n\n"
                f"{invalid_rows_2}"
            )
            st.stop()

        # If everything is valid, proceed
        df, payout_df = run_calculation(
            cola=cola, 
            pre_return=pre_return, 
            post_return=post_return, 
            retirement_age=retirement_age, 
            current_age=current_age, 
            current_year=current_year, 
            bucket_df=bucket_df
        )

        st.subheader("Year-by-Year Balances")
        st.dataframe(df, use_container_width=True)

        st.subheader("Final Payouts")
        st.dataframe(payout_df, use_container_width=True)

        # Download links
        st.download_button(
            label="Download Year-by-Year as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="yearly_balances.csv",
            mime="text/csv"
        )

        st.download_button(
            label="Download Final Payouts as CSV",
            data=payout_df.to_csv(index=False).encode("utf-8"),
            file_name="bucket_payouts.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()


