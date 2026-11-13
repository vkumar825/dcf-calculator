from datetime import datetime
from typing import Any
from edgar import CompanyNotFoundError
from pydantic import ValidationError
import streamlit as st
import pandas as pd
from dcf_calculator.dcf import DiscountedCashFlow
from dcf_calculator.dcf_schemas import AnnualFinancials, ValuationAssumptions
from dcf_calculator.fetch_edgar import get_annual_financials


def format_currency(val: float, projection: bool = False) -> str:
    if val is None:
        return "N/A"

    sign = "-" if val < 0 else ""
    dollar_prefix = "$"
    abs_val = abs(val)

    if projection:
        num_str = f"{abs_val / 1e6:,.1f}".removesuffix(".0")
        return f"{sign}{num_str}"

    if abs_val >= 1e12:
        return f"{sign}{dollar_prefix}{abs_val / 1e12:,.2f}T"
    elif abs_val >= 1e9:
        return f"{sign}{dollar_prefix}{abs_val / 1e9:,.1f}B"
    elif abs_val >= 1e6:
        return f"{sign}{dollar_prefix}{abs_val / 1e6:,.1f}M"
    else:
        return f"{sign}{dollar_prefix}{abs_val:,.0f}"


def display_company_overview(ticker: str, fiscal_year: int, financials: dict[str, Any]):
    income_statement = financials["income_statement"]
    cash_flow_statement = financials["cash_flow_statement"]
    balance_sheet = financials["balance_sheet"]

    fy_end = (
        f" · {financials['fiscal_year_end']}"
        if financials.get("fiscal_year_end")
        else ""
    )

    st.header(f"{financials['company_name']} ({ticker.upper()})", anchor=False)
    st.markdown(
        f"###### FY{fiscal_year} 10-K{fy_end} · CIK {financials['cik']}",
        anchors=False,
    )
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Revenue", format_currency(income_statement["revenue"]))
    col2.metric(
        "Operating Cash Flow",
        format_currency(cash_flow_statement["operating_cash_flow"]),
    )
    col3.metric("Cash & Cash Equivalents", format_currency(balance_sheet["cash_equiv"]))
    col4.metric("Long-Term Debt", format_currency(balance_sheet["long_term_debt"]))

    st.divider()


def display_cost_of_capital(
    valuations: dict[str, Any],
    assumptions: dict[str, Any],
    financials: dict[str, Any],
):
    income_statement = financials["income_statement"]
    balance_sheet = financials["balance_sheet"]
    total_debt = balance_sheet["short_term_debt"] + balance_sheet["long_term_debt"]

    pre_tax_cost_of_debt = valuations["pre_tax_cost_of_debt"]
    effective_tax_rate = valuations["effective_tax_rate"]

    current_stock_price = assumptions["current_stock_price"]
    outstanding_shares = income_statement["shares_outstanding"]
    market_capitalization = current_stock_price * outstanding_shares
    total_capitalization = market_capitalization + total_debt

    cost_of_equity = valuations["cost_of_equity"]

    st.subheader("Cost of Capital", anchor=False)

    col1, col2, col3 = st.columns(3)
    col1.metric("Market Cap", format_currency(market_capitalization), border=True)
    col2.metric("Total Debt", format_currency(total_debt), border=True)
    col3.metric("Total Capital", format_currency(total_capitalization), border=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Cost of Equity", f"{cost_of_equity * 100:,.1f}%", border=True)
    col2.metric(
        "Pre-Tax Cost of Debt", f"{pre_tax_cost_of_debt * 100:,.1f}%", border=True
    )
    col3.metric("Effective Tax Rate", f"{effective_tax_rate * 100:,.1f}%", border=True)

    st.info(f"Weighted Average Cost of Capital (WACC): **{valuations['wacc']:.1%}**")
    st.divider()


def display_projection_schedule(
    projection_schedules: list[dict[str, Any]], fiscal_year: int
):
    st.subheader(
        f"{len(projection_schedules) - 1}-Year Unlevered Free Cash Flow Projections",
        anchor=False,
    )

    schedule_list = []
    year_index = []

    for idx, schedule in enumerate(projection_schedules):
        year_index.append(idx + fiscal_year)
        schedule_list.append(
            {
                "Revenue": format_currency(schedule["revenue"], projection=True),
                "EBIT": format_currency(schedule["operating_income"], projection=True),
                "NOPAT": format_currency(schedule["nopat"], projection=True),
                "D&A": format_currency(schedule["depr_amort"], projection=True),
                "CapEx": format_currency(schedule["capex"], projection=True),
                "Free Cash Flow": format_currency(schedule["ufcf"], projection=True),
                "Discount Factor": f"{schedule['discount_factor']:.3f}",
                "Present Value": format_currency(
                    schedule["present_value"], projection=True
                ),
            }
        )

    projection_df = pd.DataFrame(schedule_list, index=year_index)
    st.dataframe(projection_df.T)
    st.markdown("*All figures in **USD Millions**, except Discount Factor*")
    st.divider()


def main():
    st.title("Discounted Cash Flow Calculator", anchor=False)
    st.markdown(
        "Pull SEC 10-K filings (**2009+**), model WACC and free cash flows, estimate instrinsic value, and implied share price.\n\n"
        "View source on [GitHub](https://github.com/vkumar825/dcf-calculator)."
    )
    with st.form("dcf_form", enter_to_submit=False):
        col1, col2 = st.columns(2)
        ticker = col1.text_input("Ticker Symbol", value="AAPL", required=True).upper()
        fiscal_year = col2.number_input(
            "Fiscal Year",
            min_value=2009,  # Covers SEC XBRL filings from 2009 onward
            max_value=datetime.now().year,
            value=datetime.now().year
            - 1,  # Setting to previous year to account for companies that haven't filed yet
            step=1,
            required=True,
        )

        col1, col2, col3 = st.columns(3)
        current_stock_price = col1.number_input(
            "Current Stock Price ($)", value=235.0, step=1.0, format="%g", required=True
        )
        risk_free_rate = col2.number_input(
            "Risk-free Rate (%)", value=4.0, step=0.25, format="%g", required=True
        )
        beta = col3.number_input(
            "Beta", value=1.07, step=0.25, format="%g", required=True
        )

        col1, col2, col3 = st.columns(3)
        market_risk_premium = col1.number_input(
            "Market Risk Premium (%)", value=5.10, step=0.25, format="%g", required=True
        )
        expected_growth_rate = col2.number_input(
            "Expected Growth Rate (%)",
            value=6.0,
            step=0.25,
            format="%g",
            required=True,
        )
        perpetual_growth_rate = col3.number_input(
            "Perpetual Growth Rate (%)",
            value=2.5,
            step=0.25,
            format="%g",
            required=True,
        )

        col1, col2 = st.columns([2, 1], vertical_alignment="bottom")
        fiscal_horizon = col1.selectbox("Fiscal Horizon (Years)", (5, 10))
        submitted = col2.form_submit_button(
            "Calculate", type="primary", use_container_width=True
        )

    if submitted:
        try:
            financials = get_annual_financials(ticker=ticker, fiscal_year=fiscal_year)

            income_statement = financials["income_statement"]
            cash_flow_statement = financials["cash_flow_statement"]
            balance_sheet = financials["balance_sheet"]

            assumptions_input = {
                "current_stock_price": current_stock_price,
                "risk_free_rate": risk_free_rate,
                "beta": beta,
                "market_risk_premium": market_risk_premium,
                "expected_growth_rate": expected_growth_rate,
                "perpetual_growth_rate": perpetual_growth_rate,
                "fiscal_horizon": fiscal_horizon,
            }

            dcf = DiscountedCashFlow(
                financials=[
                    AnnualFinancials(
                        ticker=ticker,
                        fiscal_year=fiscal_year,
                        income_statement=income_statement,
                        cash_flow_statement=cash_flow_statement,
                        balance_sheet=balance_sheet,
                    )
                ],
                assumptions=ValuationAssumptions(**assumptions_input),
            )

            valuations = dcf.run_valuation()

            display_company_overview(
                ticker=ticker, fiscal_year=fiscal_year, financials=financials
            )

            display_cost_of_capital(
                valuations=valuations,
                assumptions=assumptions_input,
                financials=financials,
            )

            display_projection_schedule(
                projection_schedules=valuations["projection_schedule"],
                fiscal_year=fiscal_year,
            )

        except CompanyNotFoundError:
            st.error("Could not find company matching that symbol.")
        except ValidationError:
            st.error(
                f"Financial statements for {ticker} in FY{fiscal_year} are incomplete. Please try another year or company."
            )
        except ValueError as e:
            st.error(f"{e}")
        except Exception:
            st.error("An unexpected error occurred. Please try again.")


if __name__ == "__main__":
    main()
