import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------
# Helper functions
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
    # Annual depreciation
    annual_depreciation = CAPEX / depreciation_years
    
    # Debt details
    debt_amount = CAPEX * debt_ratio
    annual_principal_payment = debt_amount / debt_term if debt_term > 0 else 0
    outstanding_debt = debt_amount
    
    # Cashflow at time 0: Equity portion
    cashflows = [-CAPEX * (1 - debt_ratio)]
    op_cost = operating_cost
    
    # Yearly cashflows
    for t in range(1, years + 1):
        # Interest on remaining debt
        interest_expense = outstanding_debt * interest_rate if outstanding_debt > 0 else 0
        
        # Principal repayment (only in debt term)
        financing_cash = annual_principal_payment + interest_expense if t <= debt_term else interest_expense
        
        # Depreciation and interest give tax shields
        depreciation = annual_depreciation if t <= depreciation_years else 0
        tax_shield = (depreciation + interest_expense) * tax_rate
        
        # Net cash flow: operating cost and financing cost, offset by tax shield
        net_cash = -op_cost - financing_cash + tax_shield
        
        # Add salvage value in the final year
        if t == years:
            net_cash += salvage_value
        
        cashflows.append(net_cash)
        
        # Update debt balance
        if t <= debt_term:
            outstanding_debt -= annual_principal_payment
        
        # Grow operating cost
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
        # Tax shield reduces net cost
        net_cash = -lease_payment + (lease_payment * tax_rate)
        cashflows.append(net_cash)
        lease_payment *= (1 + lease_escalation)
    return cashflows

# ---------------------------
# Streamlit UI
# ---------------------------
st.title("Leasing vs Owning Cost Analysis")
st.markdown("This tool compares the financial impact of owning a facility versus leasing it. Adjust the parameters in the sidebar.")

st.sidebar.header("Ownership Parameters")
CAPEX = st.sidebar.number_input("New-build CAPEX ($M)", min_value=50.0, max_value=1000.0, value=300.0) * 1e6
debt_ratio = st.sidebar.slider("Debt Ratio", 0.0, 1.0, 0.6)
interest_rate = st.sidebar.slider("Interest Rate (%)", 0.0, 20.0, 4.0) / 100.0
debt_term = st.sidebar.slider("Debt Term (years)", 1, 30, 10)
salvage_value = st.sidebar.number_input("Salvage Value ($M)", min_value=0.0, max_value=500.0, value=40.0) * 1e6
operating_cost = st.sidebar.number_input("Initial Operating Cost ($M)", min_value=1.0, max_value=100.0, value=12.0) * 1e6
op_cost_growth = st.sidebar.slider("Operating Cost Growth (%)", 0.0, 10.0, 2.0) / 100.0
depreciation_years = st.sidebar.slider("Depreciation Years", 1, 30, 10)
tax_rate = st.sidebar.slider("Tax Rate (%)", 0.0, 50.0, 25.0) / 100.0

st.sidebar.header("Leasing Parameters")
initial_lease_payment = st.sidebar.number_input("Initial Lease Payment ($M)", min_value=1.0, max_value=100.0, value=18.0) * 1e6
lease_escalation = st.sidebar.slider("Lease Escalation (%)", 0.0, 10.0, 3.0) / 100.0

st.sidebar.header("Analysis Settings")
years = st.sidebar.slider("Analysis Period (years)", 5, 40, 20)
wacc = st.sidebar.slider("Discount Rate / WACC (%)", 0.0, 20.0, 6.0) / 100.0

# ---------------------------
# Compute Cashflows and NPVs
# ---------------------------
own_cf = ownership_cashflows(CAPEX, debt_ratio, interest_rate, debt_term, years, 
                             operating_cost, op_cost_growth, depreciation_years, 
                             tax_rate, salvage_value)
lease_cf = leasing_cashflows(initial_lease_payment, lease_escalation, years, tax_rate)

own_npv = npv(own_cf, wacc)
lease_npv = npv(lease_cf, wacc)

st.subheader("NPV Comparison")
st.write(f"**NPV Cost of Owning:** ${own_npv:,.0f}")
st.write(f"**NPV Cost of Leasing:** ${lease_npv:,.0f}")

# ---------------------------
# Prepare Data for Visuals
# ---------------------------
# Build a DataFrame of yearly cash flows
years_range = list(range(0, years + 1))
df = pd.DataFrame({
    "Year": years_range,
    "Owning Cash Flow": own_cf,
    "Leasing Cash Flow": lease_cf
})
df["Cumulative Owning"] = df["Owning Cash Flow"].cumsum()
df["Cumulative Leasing"] = df["Leasing Cash Flow"].cumsum()

# ---------------------------
# Visuals: Cumulative Cash Flows
# ---------------------------
st.subheader("Cumulative Cash Flow Over Time")
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(df["Year"], df["Cumulative Owning"] / 1e6, label="Owning")
ax.plot(df["Year"], df["Cumulative Leasing"] / 1e6, label="Leasing")
ax.set_xlabel("Year")
ax.set_ylabel("Cumulative Cash Flow (Millions $)")
ax.set_title("Cumulative Cash Flow: Owning vs Leasing")
ax.legend()
st.pyplot(fig)

# ---------------------------
# Visuals: Yearly Cash Flows
# ---------------------------
st.subheader("Yearly Cash Flows")
fig2, ax2 = plt.subplots(figsize=(8, 5))
ax2.bar(df["Year"] - 0.15, df["Owning Cash Flow"] / 1e6, width=0.3, label="Owning")
ax2.bar(df["Year"] + 0.15, df["Leasing Cash Flow"] / 1e6, width=0.3, label="Leasing")
ax2.set_xlabel("Year")
ax2.set_ylabel("Cash Flow (Millions $)")
ax2.set_title("Yearly Cash Flows: Owning vs Leasing")
ax2.legend()
st.pyplot(fig2)
