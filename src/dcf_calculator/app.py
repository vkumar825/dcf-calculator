import streamlit as st

def main():
    # streamlit run src/dcf_calculator/app.py

    st.title("Discounted Cash Flow Calculator", anchor=False)

    with st.form("dcf_form", enter_to_submit=False):
        col1, col2 = st.columns(2)
        ticker = col1.text_input("Ticker Symbol", required=True).upper()
        fiscal_year = col2.number_input("Fiscal Year", value=2025, step=1, required=True)

        col1, col2, col3 = st.columns(3)
        current_stock_price = col1.number_input("Current Stock Price", value=None, required=True)
        risk_free_rate = col2.number_input("Risk-free Rate", value=None, required=True)
        beta = col3.number_input("Beta", value=None, required=True)

        col1, col2, col3 = st.columns(3)
        market_risk_premium = col1.number_input("Market Risk Premium", value=None, required=True)
        expected_growth_rate = col2.number_input("Expected Growth Rate", value=None, required=True)
        perpetual_growth_rate = col3.number_input("Perpetual Growth Rate", value=None, required=True)

        fiscal_horizon = st.selectbox(
            "Fiscal Horizon",
            (5, 10))

        submitted = st.form_submit_button("Calculate")
        if submitted:
            st.write(f'Ticker Symbol: {ticker}')
            st.write(f'Fiscal Year: {fiscal_year}')
            st.write(f'Current Stock Price: {current_stock_price}')
            st.write(f'Risk-free Rate: {risk_free_rate}')
            st.write(f'Beta: {beta}')
            st.write(f'Market Risk Premium: {market_risk_premium}')
            st.write(f'Expected Growth Rate: {expected_growth_rate}')
            st.write(f'Perpetual Growth Rate: {perpetual_growth_rate}')
            st.write(f'Fiscal Horizon: {fiscal_horizon}')


if __name__ == "__main__":
    main()
