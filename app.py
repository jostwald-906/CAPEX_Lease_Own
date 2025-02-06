import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------
# Helper function for dual inputs
# ---------------------------
def dual_input(label, min_value, max_value, default, step, key):
    """
    Displays a slider and a number input side by side and keeps them in sync.
    The value is stored in st.session_state[key+"_value"].
    """
    if key + "_value" not in st.session_state:
        st.session_state[key + "_value"] = default

    col1, col2 = st.columns(2)
    slider_val = col1.slider(f"{label} (slider)", min_value, max_value, st.session_state[key + "_value"], step=step, key=key+"_slider")
    number_val = col2.number_input(f"{label} (input)", min_value, max_value, st.session_state[key + "_value"], step=step, key=key+"_input")
    
    # Update session state if one control is changed
    if slider_val != st.session_state[key + "_value"]:
        st.session_state[key + "_value"] = slider_val
    if number_val != st.session_state[key + "_value"]:
        st.session_state[key + "_value"] = number_val
    return st.session_state[key + "_value"]

# ---------------------------
# Financial Model Functions
# ---------------------------
def npv(cashflows, discount_rate):
    """Calculate net present value (NPV) of cashflows."""
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cashflows))

def ownership_cashflows(CAPEX, debt_ratio, interest_rate, debt_term, years, 
                        operating_cost, op_cost_growth, depreciation_years, 
                        tax_rate, salvage_value):
    """
    Calculate yearly cash flows for owning a facility.
    Assumptions:
      - A portion of CAPEX is financed (debt).
      - Debt is repaid evenly over 'debt_term' years.
      - Interest is tax-deductible.
      - Straight-line depreciation over 'depreciation_years' gives a tax shield.
      - Operating cost grows annually.
      - Salvage value is received in the final year.
    """
    annual_depreciation = CAPEX / depreciation_years
    debt_amount = CAPEX * debt_ratio
    annual_principal_payment = debt_amount / debt_term if debt_term > 0 else 0
    outstanding_debt = debt_amount

    # Time 0: equity cash outflow
    cashflows = [-CAPEX * (1 - debt_ratio)]
    op_cost = operating_cost

    for t in range(1, years + 1):
        interest_expense = outstanding_debt * interest_rate if outstanding_debt > 0 else 0
        financing_cash = annual_principal_payment + interest_expense if t <= debt_term else interest_expense
        depreciation = annual_depreciation if t <= depreciation_years else 0
        tax_shield = (depreciation + interest_expense) * tax_rate

        net_cash = -op_cost - financing_cash + tax_shield
        if t == years:
            net_cash += salvage_value

        cashflows.append(net_cash)

        if t <= debt_term:
            outstanding_debt -= annual_principal_payment

        op_cost *= (1 + op_cost_growth)

    return cashflows

def leasing_cashflows(initial_lease_payment, lease_escalation, years, tax_rate):
    """
    Calculate yearly cash flows for leasing a facility.
    Assumptions:
      - Annual lease payment increases at a fixed escalation rate.
      - Lease payments are fully tax-deductible.
    """
    cashflows = [0]  # No upfront cost for leasing
    lease_payment = initial_lease_payment
    for t in range(1, years + 1):
        net_cash = -lease_payment + (lease_payment * tax_rate)
        cashflows.append(net_cash)
        lease_payment *= (1 + lease_escalation)
    return cashflows

# ---------------------------
# Streamlit UI
# ---------------------------
st.title("Leasing vs. Owning Cost Analysis")
st.markdown(
    "This tool compares the financial impact of owning a facility versus leasing it. "
    "For each parameter, you can adjust the value using the slider or by entering a number directly."
)

# Group inputs into a form for a cleaner user experience
with st.form("parameters_form"):
    st.header("Input Parameters")
    
    st.subheader("Ownership Parameters")
    capex_m = dual_input("New-build CAPEX ($M)", 50.0, 1000.0, 300.0, 1.0, key="CAPEX")
    salvage_m = dual_input("Salvage Value ($M)", 0.0, 500.0, 40.0, 1.0, key="salvage")
    op_cost_m = dual_input("Initial Operating Cost ($M)", 1.0, 100.0, 12.0, 1.0, key="op_cost")
    debt_ratio = dual_input("Debt Ratio", 0.0, 1.0, 0.6, 0.01, key="debt_ratio")
    interest_rate_pct = dual_input("Interest Rate (%)", 0.0, 20.0, 4.0, 0.1, key="interest_rate")
    debt_term = int(dual_input("Debt Term (years)", 1, 30, 10, 1, key="debt_term"))
    depreciation_years = int(dual_input("Depreciation Years", 1, 30, 10, 1, key="depr_years"))
    tax_rate_pct = dual_input("Tax Rate (%)", 0.0, 50.0, 25.0, 0.1, key="tax_rate")
    
    st.markdown("---")
    st.subheader("Leasing & Analysis Parameters")
    lease_payment_m = dual_input("Initial Lease Payment ($M)", 1.0, 100.0, 18.0, 1.0, key="lease_payment")
    lease_escalation_pct = dual_input("Lease Escalation (%)", 0.0, 10.0, 3.0, 0.1, key="lease_escalation")
    op_growth_pct = dual_input("Operating Cost Growth (%)", 0.0, 10.0, 2.0, 0.1, key="op_growth")
    analysis_years = int(dual_input("Analysis Period (years)", 5, 40, 20, 1, key="analysis_years"))
    wacc_pct = dual_input("Discount Rate / WACC (%)", 0.0, 20.0, 6.0, 0.1, key="wacc")
    
    submitted = st.form_submit_button("Run Analysis")

if submitted:
    # Convert inputs to proper units
    CAPEX = capex_m * 1e6
    salvage_value = salvage_m * 1e6
    operating_cost = op_cost_m * 1e6
    initial_lease_payment = lease_payment_m * 1e6

    interest_rate = interest_rate_pct / 100.0
    tax_rate = tax_rate_pct / 100.0
    op_cost_growth = op_growth_pct / 100.0
    lease_escalation = lease_escalation_pct / 100.0
    wacc = wacc_pct / 100.0

    # Compute cash flows
    own_cf = ownership_cashflows(CAPEX, debt_ratio, interest_rate, debt_term, analysis_years,
                                 operating_cost, op_cost_growth, depreciation_years,
                                 tax_rate, salvage_value)
    lease_cf = leasing_cashflows(initial_lease_payment, lease_escalation, analysis_years, tax_rate)

    own_npv = npv(own_cf, wacc)
    lease_npv = npv(lease_cf, wacc)

    # Prepare input parameter summary table
    param_data = {
        "Parameter": [
            "CAPEX ($M)", "Salvage Value ($M)", "Operating Cost ($M)", "Debt Ratio", 
            "Interest Rate (%)", "Debt Term (years)", "Depreciation Years", "Tax Rate (%)",
            "Initial Lease Payment ($M)", "Lease Escalation (%)", "Operating Cost Growth (%)",
            "Analysis Period (years)", "WACC (%)"
        ],
        "Value": [
            capex_m, salvage_m, op_cost_m, debt_ratio,
            interest_rate_pct, debt_term, depreciation_years, tax_rate_pct,
            lease_payment_m, lease_escalation_pct, op_growth_pct,
            analysis_years, wacc_pct
        ]
    }
    params_df = pd.DataFrame(param_data)

    # Prepare yearly cash flows table
    years_range = list(range(0, analysis_years + 1))
    df = pd.DataFrame({
        "Year": years_range,
        "Owning Cash Flow": own_cf,
        "Leasing Cash Flow": lease_cf
    })
    df["Cumulative Owning"] = df["Owning Cash Flow"].cumsum()
    df["Cumulative Leasing"] = df["Leasing Cash Flow"].cumsum()

    # Display outputs in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Parameter Summary", "NPV Comparison", "Yearly Cash Flows", "Cumulative Cash Flows"])

    with tab1:
        st.subheader("Input Parameters Summary")
        st.table(params_df)

    with tab2:
        st.subheader("NPV Comparison")
        npv_data = {
            "Option": ["Owning", "Leasing"],
            "NPV ($M)": [own_npv / 1e6, lease_npv / 1e6]
        }
        npv_df = pd.DataFrame(npv_data)
        st.table(npv_df)

    with tab3:
        st.subheader("Yearly Cash Flows")
        st.dataframe(df[["Year", "Owning Cash Flow", "Leasing Cash Flow"]].style.format({
            "Owning Cash Flow": "${:,.0f}",
            "Leasing Cash Flow": "${:,.0f}"
        }))
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(np.array(df["Year"]) - 0.15, df["Owning Cash Flow"] / 1e6, width=0.3, label="Owning")
        ax.bar(np.array(df["Year"]) + 0.15, df["Leasing Cash Flow"] / 1e6, width=0.3, label="Leasing")
        ax.set_xlabel("Year")
        ax.set_ylabel("Cash Flow (Millions $)")
        ax.set_title("Yearly Cash Flows: Owning vs. Leasing")
        ax.legend()
        st.pyplot(fig)

    with tab4:
        st.subheader("Cumulative Cash Flows")
        st.dataframe(df[["Year", "Cumulative Owning", "Cumulative Leasing"]].style.format({
            "Cumulative Owning": "${:,.0f}",
            "Cumulative Leasing": "${:,.0f}"
        }))
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        ax2.plot(df["Year"], df["Cumulative Owning"] / 1e6, label="Owning", marker="o")
        ax2.plot(df["Year"], df["Cumulative Leasing"] / 1e6, label="Leasing", marker="o")
        ax2.set_xlabel("Year")
        ax2.set_ylabel("Cumulative Cash Flow (Millions $)")
        ax2.set_title("Cumulative Cash Flows: Owning vs. Leasing")
        ax2.legend()
        st.pyplot(fig2)
