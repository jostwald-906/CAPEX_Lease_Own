import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------
# Set default values for all parameters
# ---------------------------
default_values = {
    "CAPEX": 300.0,
    "salvage": 40.0,
    "op_cost": 12.0,
    "debt_ratio": 0.6,
    "interest_rate": 4.0,
    "debt_term": 10,
    "depr_years": 10,
    "tax_rate": 25.0,
    "lease_payment": 18.0,
    "lease_escalation": 3.0,
    "op_growth": 2.0,
    "analysis_years": 20,
    "wacc": 6.0,
}

# Initialize st.session_state with default values if not present
for key, val in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------------------------
# Helper function for dual inputs with on_change callbacks
# ---------------------------
def dual_input(label, min_value, max_value, default, step, key, help_text=""):
    """
    Displays a slider and a number input side by side.
    When either widget changes, its callback updates st.session_state[key].
    Both widgets use st.session_state[key] so they remain in sync.
    """
    def update_from_slider():
        st.session_state[key] = st.session_state[key + "_slider"]

    def update_from_input():
        st.session_state[key] = st.session_state[key + "_input"]

    col1, col2 = st.columns(2)
    col1.slider(
        f"{label} (slider)",
        min_value, max_value,
        value=st.session_state[key],
        step=step,
        help=help_text,
        key=key + "_slider",
        on_change=update_from_slider
    )
    col2.number_input(
        f"{label} (input)",
        min_value, max_value,
        value=st.session_state[key],
        step=step,
        help=help_text,
        key=key + "_input",
        on_change=update_from_input
    )
    return st.session_state[key]

# ---------------------------
# Financial Model Functions
# ---------------------------
def npv(cashflows, discount_rate):
    """Calculate net present value (NPV) of cashflows."""
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cashflows))

def ownership_cashflows(CAPEX, debt_ratio, interest_rate, debt_term, n_years, 
                        operating_cost, op_cost_growth, depreciation_years, 
                        tax_rate, salvage_value):
    """
    Calculate yearly cash flows for owning a facility.
    
    Assumptions:
      - A portion of CAPEX is financed by debt (repaid evenly over debt_term years).
      - Interest on the financed portion is tax-deductible.
      - Straight-line depreciation over depreciation_years creates a tax shield.
      - Operating cost grows annually at a constant rate.
      - Salvage value is received in the final year.
    """
    annual_depreciation = CAPEX / depreciation_years
    debt_amount = CAPEX * debt_ratio
    annual_principal_payment = debt_amount / debt_term if debt_term > 0 else 0
    outstanding_debt = debt_amount

    # Time 0: equity cash outflow
    cashflows = [-CAPEX * (1 - debt_ratio)]
    op_cost = operating_cost

    for t in range(1, n_years + 1):
        interest_expense = outstanding_debt * interest_rate if outstanding_debt > 0 else 0
        financing_cash = annual_principal_payment + interest_expense if t <= debt_term else interest_expense
        depreciation = annual_depreciation if t <= depreciation_years else 0
        tax_shield = (depreciation + interest_expense) * tax_rate

        net_cash = -op_cost - financing_cash + tax_shield
        if t == n_years:
            net_cash += salvage_value

        cashflows.append(net_cash)

        if t <= debt_term:
            outstanding_debt -= annual_principal_payment

        op_cost *= (1 + op_cost_growth)

    return cashflows

def leasing_cashflows(initial_lease_payment, lease_escalation, n_years, tax_rate):
    """
    Calculate yearly cash flows for leasing a facility.
    
    Assumptions:
      - Lease payments escalate annually at a fixed rate.
      - Lease payments are fully tax-deductible.
    """
    cashflows = [0]  # No upfront cost for leasing
    lease_payment = initial_lease_payment
    for t in range(1, n_years + 1):
        net_cash = -lease_payment + (lease_payment * tax_rate)
        cashflows.append(net_cash)
        lease_payment *= (1 + lease_escalation)
    return cashflows

# ---------------------------
# Convert session_state values to working units
# ---------------------------
capex_m = st.session_state["CAPEX"]
salvage_m = st.session_state["salvage"]
op_cost_m = st.session_state["op_cost"]
debt_ratio = st.session_state["debt_ratio"]
interest_rate_pct = st.session_state["interest_rate"]
debt_term = st.session_state["debt_term"]
depreciation_years = st.session_state["depr_years"]
tax_rate_pct = st.session_state["tax_rate"]
lease_payment_m = st.session_state["lease_payment"]
lease_escalation_pct = st.session_state["lease_escalation"]
op_growth_pct = st.session_state["op_growth"]
analysis_years = st.session_state["analysis_years"]
wacc_pct = st.session_state["wacc"]

CAPEX = capex_m * 1e6
salvage_value = salvage_m * 1e6
operating_cost = op_cost_m * 1e6
initial_lease_payment = lease_payment_m * 1e6
interest_rate = interest_rate_pct / 100.0
tax_rate = tax_rate_pct / 100.0
op_cost_growth = op_growth_pct / 100.0
lease_escalation = lease_escalation_pct / 100.0
wacc = wacc_pct / 100.0

# ---------------------------
# Compute outputs
# ---------------------------
own_cf = ownership_cashflows(CAPEX, debt_ratio, interest_rate, debt_term, analysis_years,
                             operating_cost, op_cost_growth, depreciation_years,
                             tax_rate, salvage_value)
lease_cf = leasing_cashflows(initial_lease_payment, lease_escalation, analysis_years, tax_rate)
own_npv = npv(own_cf, wacc)
lease_npv = npv(lease_cf, wacc)

# Prepare a summary table for parameters and yearly cash flows data frame
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

years_range = list(range(0, analysis_years + 1))
df = pd.DataFrame({
    "Year": years_range,
    "Owning Cash Flow": own_cf,
    "Leasing Cash Flow": lease_cf
})
df["Cumulative Owning"] = df["Owning Cash Flow"].cumsum()
df["Cumulative Leasing"] = df["Leasing Cash Flow"].cumsum()

# ---------------------------
# Display Outputs (Tabs) at the Top
# ---------------------------
st.title("Leasing vs. Owning Cost Analysis")
st.markdown(
    "This tool compares the financial impact of owning a facility versus leasing it. "
    "For each parameter, you can adjust the value using the slider or by entering a number directly."
)
st.header("Output Results")
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "Approach & Assumptions", 
    "Parameter Summary", 
    "NPV Comparison", 
    "Yearly Cash Flows", 
    "Cumulative Cash Flows"
])

with tab0:
    st.subheader("Approach & Assumptions")
    st.markdown(
        """
        **Approach:**
        - The model calculates Net Present Value (NPV) by discounting projected cash flows using a constant discount rate (WACC).
        - For ownership, a portion of CAPEX is financed with debt (repaid evenly), with tax shields from interest and straight‑line depreciation.
        - For leasing, the model uses fixed annual lease payments (with escalation) and applies a tax benefit to those payments.
        
        **Assumptions:**
        - Operating costs grow at a constant rate.
        - Debt is repaid evenly and depreciation is linear.
        - This is a high‑level analysis; more detailed evaluations might separate operating and financing cash flows.
        """
    )

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
    st.dataframe(
        df[["Year", "Owning Cash Flow", "Leasing Cash Flow"]].style.format({
            "Owning Cash Flow": "${:,.0f}",
            "Leasing Cash Flow": "${:,.0f}"
        }),
        width=1200
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(np.array(df["Year"]) - 0.15, df["Owning Cash Flow"] / 1e6, width=0.3, label="Owning")
    ax.bar(np.array(df["Year"]) + 0.15, df["Leasing Cash Flow"] / 1e6, width=0.3, label="Leasing")
    ax.set_xlabel("Year")
    ax.set_ylabel("Cash Flow (Millions $)")
    ax.set_title("Yearly Cash Flows: Owning vs. Leasing")
    ax.legend()
    st.pyplot(fig)

with tab4:
    st.subheader("Cumulative Cash Flows")
    st.dataframe(
        df[["Year", "Cumulative Owning", "Cumulative Leasing"]].style.format({
            "Cumulative Owning": "${:,.0f}",
            "Cumulative Leasing": "${:,.0f}"
        }),
        width=1200
    )
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.plot(df["Year"], df["Cumulative Owning"] / 1e6, label="Owning", marker="o")
    ax2.plot(df["Year"], df["Cumulative Leasing"] / 1e6, label="Leasing", marker="o")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Cumulative Cash Flow (Millions $)")
    ax2.set_title("Cumulative Cash Flows: Owning vs. Leasing")
    ax2.legend()
    st.pyplot(fig2)

# ---------------------------
# Display Input Controls in an Expander Below
# ---------------------------

st.header("Input Parameters")
with st.expander("Show/Modify Inputs", expanded=True):
    capex_m = dual_input(
        "New-build CAPEX ($M)", 50.0, 3000.0, default_values["CAPEX"], 1.0, key="CAPEX",
        help_text="The total cost (in millions) to build the facility. This is the upfront capital expenditure for ownership."
    )
    salvage_m = dual_input(
        "Salvage Value ($M)", 0.0, 500.0, default_values["salvage"], 1.0, key="salvage",
        help_text="The estimated residual value (in millions) recoverable at the end of the analysis period."
    )
    op_cost_m = dual_input(
        "Initial Operating Cost ($M)", 1.0, 100.0, default_values["op_cost"], 1.0, key="op_cost",
        help_text="The first-year operating cost (in millions) covering maintenance, utilities, etc."
    )
    debt_ratio = dual_input(
        "Debt Ratio", 0.0, 1.0, default_values["debt_ratio"], 0.01, key="debt_ratio",
        help_text="The fraction of CAPEX financed by debt (e.g., 0.6 means 60% debt, 40% equity)."
    )
    interest_rate_pct = dual_input(
        "Interest Rate (%)", 0.0, 20.0, default_values["interest_rate"], 0.1, key="interest_rate",
        help_text="The annual interest rate (in percent) on the financed portion."
    )
    debt_term = int(dual_input(
        "Debt Term (years)", 1, 30, default_values["debt_term"], 1, key="debt_term",
        help_text="The number of years over which the debt is repaid."
    ))
    depreciation_years = int(dual_input(
        "Depreciation Years", 1, 30, default_values["depr_years"], 1, key="depr_years",
        help_text="The period over which the facility is depreciated (straight-line)."
    ))
    tax_rate_pct = dual_input(
        "Tax Rate (%)", 0.0, 50.0, default_values["tax_rate"], 0.1, key="tax_rate",
        help_text="The corporate tax rate (in percent) used to calculate tax shields."
    )
    lease_payment_m = dual_input(
        "Initial Lease Payment ($M)", 1.0, 100.0, default_values["lease_payment"], 1.0, key="lease_payment",
        help_text="The annual lease payment (in millions) if the facility is leased."
    )
    lease_escalation_pct = dual_input(
        "Lease Escalation (%)", 0.0, 10.0, default_values["lease_escalation"], 0.1, key="lease_escalation",
        help_text="The annual percentage increase in the lease payment."
    )
    op_growth_pct = dual_input(
        "Operating Cost Growth (%)", 0.0, 10.0, default_values["op_growth"], 0.1, key="op_growth",
        help_text="The expected annual growth rate (in percent) in operating costs."
    )
    analysis_years = int(dual_input(
        "Analysis Period (years)", 5, 40, default_values["analysis_years"], 1, key="analysis_years",
        help_text="The time horizon (in years) for the cash flow and NPV analysis."
    ))
    wacc_pct = dual_input(
        "Discount Rate / WACC (%)", 0.0, 20.0, default_values["wacc"], 0.1, key="wacc",
        help_text="The discount rate (in percent) used to discount future cash flows."
    )
