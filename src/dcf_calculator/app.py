from datetime import datetime
from typing import Any
from edgar import CompanyNotFoundError
from pydantic import ValidationError
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dcf_calculator.dcf import DiscountedCashFlow
from dcf_calculator.dcf_schemas import AnnualFinancials, ValuationAssumptions
from dcf_calculator.fetch_edgar import get_annual_financials


def format_currency(val: float, projection: bool = False, currency: bool = True) -> str:
    if val is None:
        return "N/A"

    sign = "-" if val < 0 else ""
    dollar_prefix = "$" if currency else ""
    abs_val = abs(val)

    if projection:
        num_str = f"{abs_val / 1e6:,.1f}".removesuffix(".0")
        return f"{sign}{num_str}"

    if abs_val >= 1e12:
        val_str = f"{abs_val / 1e12:,.2f}"
        if "." in val_str:
            val_str = val_str.rstrip("0").rstrip(".")
        return f"{sign}{dollar_prefix}{val_str}T"
    elif abs_val >= 1e9:
        val_str = f"{abs_val / 1e9:,.1f}".removesuffix(".0")
        return f"{sign}{dollar_prefix}{val_str}B"
    elif abs_val >= 1e6:
        val_str = f"{abs_val / 1e6:,.1f}".removesuffix(".0")
        return f"{sign}{dollar_prefix}{val_str}M"
    elif abs_val == 0:
        return f"{dollar_prefix}0"
    else:
        return f"{sign}{dollar_prefix}{abs_val:,.2f}"


def display_company_overview(ticker: str, fiscal_year: int, financials: dict[str, Any]):
    income_statement = financials["income_statement"]
    cash_flow_statement = financials["cash_flow_statement"]
    balance_sheet = financials["balance_sheet"]

    fy_end = (
        f" (Ended {financials['fiscal_year_end']})"
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

    current_share_price = assumptions["current_share_price"]
    outstanding_shares = income_statement["shares_outstanding"]
    market_capitalization = current_share_price * outstanding_shares
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


def display_valuation_summary(
    valuations: dict[str, Any],
    financials: dict[str, Any],
    current_share_price: float,
):
    st.subheader("Valuation Summary", anchor=False)

    income_statement = financials["income_statement"]
    shares_outstanding = income_statement.get("shares_outstanding")
    n = len(valuations["present_values"])

    col1, col2, col3 = st.columns(3)
    col1.metric(
        f"PV of {n}-Year Free Cash Flow",
        format_currency(valuations["pv_of_fcf"]),
        border=True,
    )
    col2.metric(
        "Terminal Value", format_currency(valuations["terminal_value"]), border=True
    )
    col3.metric(
        "PV of Terminal Value",
        format_currency(valuations["pv_of_terminal_value"]),
        border=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Enterprise Value", format_currency(valuations["enterprise_value"]), border=True
    )
    col2.metric(
        "Equity Value", format_currency(valuations["equity_value"]), border=True
    )
    col3.metric(
        "Diluted Shares Outstanding",
        format_currency(shares_outstanding, currency=False),
        border=True,
    )

    upside = (
        valuations["implied_share_price"] - current_share_price
    ) / current_share_price

    _, col1, col2, _ = st.columns([0.5, 1, 1, 0.5])

    col1.metric(
        "Current Share Price",
        format_currency(current_share_price),
        delta="Market Price",
        delta_color="violet",
        delta_arrow="off",
        border=True,
    )

    arrow_str = "off"

    # Margin of Safety thresholds:
    # Buy:  >= +20% (undervalued with buffer)
    # Sell: < -10%  (overvalued)
    # Hold: -10% to +20% (fair value range)
    if upside >= 0.20:
        signal = "Buy"
        delta_color = "normal"
        arrow_str = "up"
    elif upside < -0.10:
        signal = "Sell"
        delta_color = "normal"
        arrow_str = "down"
    else:
        signal = "Hold"
        delta_color = "yellow"

    col2.metric(
        "Implied Share Price",
        format_currency(valuations["implied_share_price"]),
        delta=f"{upside:+.1%} ({signal})",
        delta_color=delta_color,
        delta_arrow=arrow_str,
        border=True,
    )

    st.divider()


def display_valuation_bridge_chart(
    valuations: dict[str, Any],
    financials: dict[str, Any],
):
    st.subheader(
        "Valuation Bridge: PV of Cash Flows to Equity Value",
        anchor=False,
    )

    balance_sheet = financials["balance_sheet"]
    total_debt = balance_sheet["short_term_debt"] + balance_sheet["long_term_debt"]
    total_cash_and_securities = (
        balance_sheet["cash_equiv"]
        + balance_sheet["short_term_investments"]
        + balance_sheet["long_term_investments"]
    )

    # Normalize the units to USD billions
    pv_of_fcf_b = valuations["pv_of_fcf"] / 1e9
    pv_of_terminal_value_b = valuations["pv_of_terminal_value"] / 1e9
    total_cash_b = total_cash_and_securities / 1e9
    total_debt_b = -total_debt / 1e9
    equity_value_b = valuations["equity_value"] / 1e9

    x_labels = [
        "PV of Cash Flows",
        "PV of Terminal Value",
        "Cash & Marketable Securities",
        "Total Debt",
        "Equity Value",
    ]
    measures = ["relative", "relative", "relative", "relative", "total"]
    y_values = [
        pv_of_fcf_b,
        pv_of_terminal_value_b,
        total_cash_b,
        total_debt_b,
        equity_value_b,
    ]
    text_labels = [
        f"${pv_of_fcf_b:,.1f}B",
        f"${pv_of_terminal_value_b:,.1f}B",
        f"+${total_cash_b:,.1f}B",
        f"-${abs(total_debt_b):,.1f}B",
        f"${equity_value_b:,.1f}B",
    ]

    fig = go.Figure(
        go.Waterfall(
            name="Valuation Bridge",
            orientation="v",
            measure=measures,
            x=x_labels,
            textposition="outside",
            text=text_labels,
            y=y_values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        )
    )

    fig.update_layout(
        yaxis_title="USD (Billions)",
        showlegend=False,
        waterfallgap=0.25,
        margin=dict(l=20, r=20, t=30, b=20),
    )

    st.plotly_chart(fig, width="stretch")


@st.cache_data(show_spinner="Fetching financial statements from SEC EDGAR...")
def load_financials(ticker: str, fiscal_year: int) -> dict[str, Any]:
    return get_annual_financials(ticker=ticker, fiscal_year=fiscal_year)


def main():
    st.title("Discounted Cash Flow Calculator", anchor=False)
    st.markdown(
        "Pulls SEC 10-K filings **(2009+)** to calculate WACC, "
        "project free cash flows, and estimate implied share price. "
        "[View source on GitHub](https://github.com/vkumar825/dcf-calculator)."
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
        current_share_price = col1.number_input(
            "Current Share Price ($)",
            min_value=1.0,
            value=230.0,
            step=1.0,
            format="%g",
            required=True,
        )
        risk_free_rate = col2.number_input(
            "Risk-free Rate (%)", value=4.25, step=0.25, format="%g", required=True
        )
        beta = col3.number_input(
            "Beta", value=1.25, step=0.25, format="%g", required=True
        )

        col1, col2, col3 = st.columns(3)
        market_risk_premium = col1.number_input(
            "Market Risk Premium (%)", value=5.0, step=0.25, format="%g", required=True
        )
        expected_growth_rate = col2.number_input(
            "Expected Growth Rate (%)",
            value=8.0,
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
            financials = load_financials(ticker=ticker, fiscal_year=fiscal_year)

            income_statement = financials["income_statement"]
            cash_flow_statement = financials["cash_flow_statement"]
            balance_sheet = financials["balance_sheet"]

            assumptions_input = {
                "current_share_price": current_share_price,
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

            display_valuation_summary(
                valuations=valuations,
                financials=financials,
                current_share_price=assumptions_input["current_share_price"],
            )

            display_valuation_bridge_chart(
                valuations=valuations,
                financials=financials,
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
