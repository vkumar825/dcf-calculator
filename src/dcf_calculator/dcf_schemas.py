from pydantic import BaseModel


class IncomeStatement(BaseModel):
    """Core financial metrics from the income statement.

    Attributes:
        revenue: Total revenue (top-line sales).
        ebit: Earnings before interest and taxes.
        income_tax_expense: Total income taxes.
        pre_tax_income: Earnings before taxes.
        shares_outstanding: Common shares outstanding.
    """

    revenue: float
    ebit: float
    income_tax_expense: float
    pre_tax_income: float
    shares_outstanding: float


class CashFlowStatement(BaseModel):
    """Cash flow statement metrics for free cash flow calculation.

    Attributes:
        depr_amort: Depreciation and amortization.
        capex: Capital expenditures.
        delta_nwc: Change in net working capital.
    """

    depr_amort: float
    capex: float
    delta_nwc: float


class BalanceSheet(BaseModel):
    """Balance sheet items for debt and cash adjustments.

    Attributes:
        cash_equiv: Cash and cash equivalents.
        short_term_investments: Short-term liquid marketable securities.
        short_term_debt: Short-term borrowings and current portion of debt.
        long_term_debt: Non-current debt obligations.
        total_debt: Computed property summing short-term and long-term debt.
    """

    cash_equiv: float
    short_term_investments: float
    short_term_debt: float
    long_term_debt: float

    @property
    def total_debt(self) -> float:
        return self.short_term_debt + self.long_term_debt


class AnnualFinancials(BaseModel):
    """Financial statements for a specific company and fiscal year.

    Attributes:
        ticker: Stock ticker symbol.
        fiscal_year: Reporting year.
        dollars_unit: Currency unit across statements (e.g., 'millions').
        shares_unit: Share count unit (e.g., 'shares', 'millions').
        income_statement: Income statement metrics.
        cash_flow_statement: Cash flow statement metrics.
        balance_sheet: Balance sheet metrics.
    """

    ticker: str
    fiscal_year: int
    dollars_unit: str
    shares_unit: str
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    balance_sheet: BalanceSheet


class ValuationAssumptions(BaseModel):
    """User-provided assumptions for DCF valuation and WACC.

    Attributes:
        risk_free_rate: Risk-free rate of return.
        beta: Stock beta (volatility relative to market).
        current_stock_price: Current share price.
        pre_tax_cost_debt: Effective interest rate on debt.
        expected_revenue_growth_rate: Forecasted annual revenue growth rate.
        perpetual_terminal_growth_rate: Long-term terminal growth rate.
        fiscal_horizon: Forecast horizon in years.
        market_risk_premium: Expected market return above risk-free rate.
    """

    risk_free_rate: float
    beta: float
    current_stock_price: float
    pre_tax_cost_debt: float
    expected_revenue_growth_rate: float
    perpetual_terminal_growth_rate: float
    fiscal_horizon: int
    market_risk_premium: float
