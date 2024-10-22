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

# Function to apply extra credits based on Rule of 55
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

# Forecast function
def forecast_contributions(dob, hire_date, years_of_service, eligible_pay, rate_of_return, pay_growth_rate, target_age):
    total_contributions = 0
    current_year = 2026
    reference_date = datetime(2026, 1, 1)
    reference_age = relativedelta(reference_date, dob).years
    years_until_target = target_age - reference_age

    salary_2026 = eligible_pay * (1 + pay_growth_rate)  # Apply growth only once for 2025 -> 2026

    # Calculate years of service from hire date
    if hire_date:
        years_of_service_on_2025 = relativedelta(datetime(2025, 12, 31), hire_date).years
    else:
        years_of_service_on_2025 = years_of_service

    # Calculate the employee's age on 12/31/2025
    age_on_2025 = relativedelta(datetime(2025, 12, 31), dob).years

    # Check if Rule of 55 applies on 12/31/2025
    rule_of_55_applies = age_on_2025 + years_of_service_on_2025 >= 55

    data = []
    years = []
    contributions = []

    for year in range(years_until_target):
        age = reference_age + year
        regular_contribution_rate = calculate_contribution_rate(years_of_service)
        
        # Apply extra service credits only if Rule of 55 applies and between 2026-2030
        if rule_of_55_applies and current_year >= 2026 and current_year <= 2030:
            service_credit_rate = 0.04  # Extra 4% service credit
        else:
            service_credit_rate = 0.0  # No extra credits

        annual_regular_contribution = salary_2026 * regular_contribution_rate
        annual_service_credits = salary_2026 * service_credit_rate
        annual_total_contribution = annual_regular_contribution + annual_service_credits

        total_contributions += annual_total_contribution
        total_contributions *= (1 + rate_of_return)
        salary_2026 *= (1 + pay_growth_rate)

        data.append({
            'Year': str(current_year),  # Convert Year to string to prevent commas
            'Age': age,
            'Years of Service': years_of_service,
            'Salary': salary_2026,
            'Regular Contribution Rate (%)': regular_contribution_rate * 100,
            'Service Credit Rate (%)': service_credit_rate * 100,
            'Annual Regular Contribution': annual_regular_contribution,
            'Annual Service Credits': annual_service_credits,
            'Total Accumulated Assets': total_contributions
        })

        years.append(current_year)
        contributions.append(total_contributions)

        # Increment years of service for each year
        years_of_service += 1
        current_year += 1

    df = pd.DataFrame(data)

    # Display DataFrame with better formatting
    df['Salary'] = df['Salary'].map('${:,.2f}'.format)
    df['Annual Regular Contribution'] = df['Annual Regular Contribution'].map('${:,.2f}'.format)
    df['Annual Service Credits'] = df['Annual Service Credits'].map('${:,.2f}'.format)
    df['Total Accumulated Assets'] = df['Total Accumulated Assets'].map('${:,.2f}'.format)

    # Display formatted DataFrame in Streamlit
    st.write("### Contribution Growth Forecast Table")
    st.dataframe(df)

    # Plotting the results
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
dob_input = st.text_input("Enter Date of Birth (MM/DD/YYYY):", placeholder="MM/DD/YYYY")
if dob_input:
    try:
        dob = datetime.strptime(dob_input, "%m/%d/%Y")
    except ValueError:
        st.error("Invalid Date Format. Please enter in MM/DD/YYYY format.")

# Input fields for Hire Date and Years of Service with validation
st.write("**Please enter either Hire Date or Years of Service (not both):**")
hire_date_input = st.text_input("Enter Hire Date (MM/DD/YYYY):", placeholder="MM/DD/YYYY or leave blank if entering Years of Service")
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
eligible_pay_input = st.text_input("Enter Eligible Pay (e.g., 100,000.00):", placeholder="100,000.00")
if eligible_pay_input:
    if not re.match(r'^\d{1,3}(,\d{3})*\.\d{2}$', eligible_pay_input):
        st.error("Invalid Eligible Pay Format. Please enter in the format 100,000.00")
    else:
        eligible_pay = float(eligible_pay_input.replace(',', '').replace('$', ''))

# Rate of Return input with validation
rate_of_return_input = st.text_input("Enter Rate of Return (e.g., 5.50):", placeholder="e.g., 5.50")
if rate_of_return_input:
    if not re.match(r'^\d+\.\d{2}$', rate_of_return_input):
        st.error("Invalid Rate of Return Format. Please enter in the format 5.50")
    else:
        rate_of_return = float(rate_of_return_input) / 100

# Pay Growth Rate input with validation
pay_growth_rate_input = st.text_input("Enter Pay Growth Rate (e.g., 3.00):", placeholder="e.g., 3.00")
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
                    years_of_service = relativedelta(hire_date, dob).years
                    forecast_contributions(dob, years_of_service, eligible_pay, rate_of_return, pay_growth_rate, target_age)
            elif years_of_service_input:
                years_of_service = int(years_of_service_input)
                forecast_contributions(dob, years_of_service, eligible_pay, rate_of_return, pay_growth_rate, target_age)
            else:
                st.error("Please provide either a Hire Date or Years of Service.")
        except ValueError as e:
            st.error(f"Error: {e}")
