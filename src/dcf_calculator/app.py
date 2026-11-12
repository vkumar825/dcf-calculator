from edgar import CompanyNotFoundError
import streamlit as st
import pandas as pd
from dcf_calculator.fetch_edgar import get_annual_financials


def display_company_overview(ticker: str, fiscal_year: int):
    financials = get_annual_financials(ticker=ticker, fiscal_year=fiscal_year)

    income_statement = financials["income_statement"]
    cash_flow_statement = financials["cash_flow_statement"]
    balance_sheet = financials["balance_sheet"]

    st.header(f"{financials['company_name']} ({ticker.upper()})", anchor=False)
    st.markdown(f"###### FY{fiscal_year} 10-K • CIK {financials['cik']}", anchors=False)
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Revenue", f"${income_statement['revenue'] / 1e9:,.1f}B")
    col2.metric(
        "Operating Cash Flow",
        f"${cash_flow_statement['operating_cash_flow'] / 1e9:,.1f}B",
    )
    col3.metric(
        "Cash & Cash Equivalents", f"${balance_sheet['cash_equiv'] / 1e9:,.1f}B"
    )
    col4.metric("Long-Term Debt", f"${balance_sheet['long_term_debt'] / 1e9:,.1f}B")

    return income_statement, cash_flow_statement, balance_sheet


def main():
    st.title("Discounted Cash Flow Calculator", anchor=False)

    with st.form("dcf_form", enter_to_submit=False):
        col1, col2 = st.columns(2)
        ticker = col1.text_input("Ticker Symbol", required=True).upper()
        fiscal_year = col2.number_input(
            "Fiscal Year", value=2025, step=1, required=True
        )

        col1, col2, col3 = st.columns(3)
        current_stock_price = col1.number_input(
            "Current Stock Price", value=None, required=True
        )
        risk_free_rate = col2.number_input("Risk-free Rate", value=None, required=True)
        beta = col3.number_input("Beta", value=None, required=True)

        col1, col2, col3 = st.columns(3)
        market_risk_premium = col1.number_input(
            "Market Risk Premium", value=None, required=True
        )
        expected_growth_rate = col2.number_input(
            "Expected Growth Rate", value=None, required=True
        )
        perpetual_growth_rate = col3.number_input(
            "Perpetual Growth Rate", value=None, required=True
        )

        fiscal_horizon = st.selectbox("Fiscal Horizon", (5, 10))

        submitted = st.form_submit_button("Calculate")

    if submitted:
        try:
            income_statement, cash_flow_statement, balance_sheet = (
                display_company_overview(ticker=ticker, fiscal_year=fiscal_year)
            )

        except CompanyNotFoundError:
            st.error("Could not find company matching that symbol.")
        except ValueError as e:
            st.error(f"{e}")
        except Exception as e:
            st.error(f"An unexpected error occurred. Please try again.")


if __name__ == "__main__":
    main()
