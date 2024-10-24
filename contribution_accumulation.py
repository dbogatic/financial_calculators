import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

# Function to calculate contribution rate based on years of service
def calculate_contribution_rate(years_of_service):
    if years_of_service < 10:
        return 0.05
    elif years_of_service < 15:
        return 0.06
    elif years_of_service < 20:
        return 0.07
    elif years_of_service < 25:
        return 0.08
    elif years_of_service < 30:
        return 0.09
    else:
        return 0.10

# Function to check Rule of 55 eligibility as of December 31, 2025
def apply_rule_of_55(age_on_2025, yos_on_2025, current_year):
    if age_on_2025 + yos_on_2025 >= 55 and current_year >= 2026 and current_year <= 2030:
        return 0.04  # Extra 4% for 5 years (2026–2030)
    return 0.0  # No extra credits

# Validation function to check hire date and date of birth
def validate_hire_date(dob, hire_date):
    age_at_hire = relativedelta(hire_date, dob).years
    if age_at_hire < 16:
        return False, f"Error: Hire date shows the person started working at age {age_at_hire}. Minimum working age is 16."
    return True, ""

def forecast_contributions(dob, years_of_service, eligible_pay, rate_of_return, pay_growth_rate, target_age, hire_date=None):
    # Ensure dob and hire_date are datetime objects
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d")
    if hire_date and isinstance(hire_date, str):
        hire_date = datetime.strptime(hire_date, "%Y-%m-%d")

    # Validate hire date if provided
    if hire_date:
        valid_hire_date, error_message = validate_hire_date(dob, hire_date)
        if not valid_hire_date:
            st.error(error_message)
            return

    total_contributions = 0
    current_year = datetime.now().year  # Dynamically get the current year
    reference_age = relativedelta(datetime(current_year, 1, 1), dob).years
    years_until_target = target_age - reference_age

    if years_until_target <= 0:
        st.error(f"Target age {target_age} is less than or equal to your age in {current_year} ({reference_age}). Please choose a valid target age.")
        return

    # Initial salary is the eligible pay for the current year, no inflation yet
    salary = eligible_pay

    end_of_2025 = datetime(2025, 12, 31)
    age_on_2025 = relativedelta(end_of_2025, dob).years

    # Calculate years of service as of now (for Year Now)
    today = datetime.now()
    if hire_date:
        yos_now = relativedelta(today, hire_date).years
    else:
        yos_now = years_of_service

    data = []
    years = []
    contributions = []

    # Start the loop from Year Now and progress to the target year
    for year in range(current_year, current_year + years_until_target + 1):
        age = reference_age + (year - current_year)

        # Calculate contribution rate based on years of service
        regular_contribution_rate = calculate_contribution_rate(yos_now)
        service_credit_rate = apply_rule_of_55(age_on_2025, yos_now, year)

        # No contributions until 2026, only salary inflation before that
        if year >= 2026:
            annual_regular_contribution = salary * regular_contribution_rate
            annual_service_credits = salary * service_credit_rate
            annual_total_contribution = annual_regular_contribution + annual_service_credits
            total_contributions += annual_total_contribution
        else:
            annual_regular_contribution = 0
            annual_service_credits = 0
            annual_total_contribution = 0

        # Apply rate of return on accumulated assets
        total_contributions *= (1 + rate_of_return)

        # Append data for the current year
        data.append({
            'Year': str(year),
            'Age': age,
            'Years of Service': yos_now,
            'Salary': salary,
            'Regular Contribution Rate (%)': regular_contribution_rate * 100 if year >= 2026 else 0,
            'Service Credit Rate (%)': service_credit_rate * 100 if year >= 2026 else 0,
            'Annual Regular Contribution': annual_regular_contribution,
            'Annual Service Credits': annual_service_credits,
            'Total Accumulated Assets': total_contributions
        })

        # Inflate the salary for the next year (but not for the current year)
        if year >= current_year:
            salary *= (1 + pay_growth_rate)

        yos_now += 1  # Increment years of service for the next year
        years.append(year)
        contributions.append(total_contributions)

    # Convert data to a DataFrame
    df = pd.DataFrame(data)

    # Format numerical columns for display
    df['Salary'] = df['Salary'].map('${:,.2f}'.format)
    df['Annual Regular Contribution'] = df['Annual Regular Contribution'].map('${:,.2f}'.format)
    df['Annual Service Credits'] = df['Annual Service Credits'].map('${:,.2f}'.format)
    df['Total Accumulated Assets'] = df['Total Accumulated Assets'].map('${:,.2f}'.format)

    # Display DataFrame in Streamlit
    st.write("### Contribution Growth Forecast Table")
    st.dataframe(df)

    # Plot the results
    plt.figure(figsize=(10, 5))
    plt.plot(years, contributions, marker='o')
    plt.title("Projected Total Contribution Growth Over Time")
    plt.xlabel("Year")
    plt.ylabel("Total Contribution Growth (USD)")
    plt.grid(True)
    plt.xticks(years)
    st.pyplot(plt)

# Streamlit User Inputs
st.title("Retirement Contribution Growth Forecast")

# Date of Birth input with validation
dob_input = st.text_input("Enter Date of Birth:", placeholder="MM/DD/YYYY")
if dob_input:
    try:
        dob = datetime.strptime(dob_input, "%m/%d/%Y")
    except ValueError:
        st.error("Invalid Date Format. Please enter in MM/DD/YYYY format.")

# Input fields for Hire Date and Years of Service with validation
hire_date_input = st.text_input("Enter Hire Date:", placeholder="MM/DD/YYYY or leave blank if entering Years of Service")
if hire_date_input:
    try:
        hire_date = datetime.strptime(hire_date_input, "%m/%d/%Y")
    except ValueError:
        st.error("Invalid Hire Date Format. Please enter in MM/DD/YYYY format.")
        
years_of_service_input = st.text_input("Enter Years of Service:", placeholder="e.g., 10 or leave blank if entering Hire Date")

# Error handling for entering both Hire Date and Years of Service immediately
if hire_date_input and years_of_service_input:
    st.error("Please provide either a Hire Date or Years of Service, not both.")

# Eligible Pay input with validation
eligible_pay_input = st.text_input("Enter Eligible Pay:", placeholder="100,000.00")
if eligible_pay_input:
    if not re.match(r'^\d{1,3}(,\d{3})*\.\d{2}$', eligible_pay_input):
        st.error("Invalid Eligible Pay Format. Please enter in the format 100,000.00")
    else:
        eligible_pay = float(eligible_pay_input.replace(',', '').replace('$', ''))

# Rate of Return input with validation
rate_of_return_input = st.text_input("Enter Rate of Return:", placeholder="e.g., 5.50")
if rate_of_return_input:
    if not re.match(r'^\d+\.\d{2}$', rate_of_return_input):
        st.error("Invalid Rate of Return Format. Please enter in the format 5.50")
    else:
        rate_of_return = float(rate_of_return_input) / 100

# Pay Growth Rate input with validation
pay_growth_rate_input = st.text_input("Enter Pay Growth Rate:", placeholder="e.g., 3.00")
if pay_growth_rate_input:
    if not re.match(r'^\d+\.\d{2}$', pay_growth_rate_input):
        st.error("Invalid Pay Growth Rate Format. Please enter in the format 3.00")
    else:
        pay_growth_rate = float(pay_growth_rate_input) / 100

# Target Age input
target_age_input = st.text_input("Enter Target Age:", placeholder="e.g., 65")
if target_age_input:
    try:
        target_age = int(target_age_input)
    except ValueError:
        st.error("Invalid Target Age. Please enter a valid age.")

# Process inputs and run the forecast if valid inputs are provided
if st.button("Run Forecast"):
    if hire_date_input and years_of_service_input:
        st.error("Please provide either a Hire Date or Years of Service, not both.")
    else:
        try:
            if hire_date_input:
                hire_date = datetime.strptime(hire_date_input, "%m/%d/%Y")
                valid, message = validate_hire_date(dob, hire_date)
                if not valid:
                    st.error(message)
                else:
                    years_of_service = relativedelta(datetime(2026, 1, 1), hire_date).years  # Calculate years of service as of 2026
                    forecast_contributions(dob, years_of_service, eligible_pay, rate_of_return, pay_growth_rate, target_age, hire_date=hire_date)
            elif years_of_service_input:
                years_of_service = int(years_of_service_input)
                forecast_contributions(dob, years_of_service, eligible_pay, rate_of_return, pay_growth_rate, target_age)
            else:
                st.error("Please provide either a Hire Date or Years of Service.")
        except ValueError as e:
            st.error(f"Error: {e}")
