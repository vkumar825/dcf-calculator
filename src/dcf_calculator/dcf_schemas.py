from pydantic import BaseModel, field_validator


class IncomeStatement(BaseModel):
    """Core financial metrics from the income statement.

    Attributes:
        revenue: Top-line amount of money before expenses
        operating_income: Earnings before interest and taxes.
        interest_expense: Interest expense on debt obligations.
        income_tax_expense: Total income taxes.
        pre_tax_income: Earnings before taxes.
        shares_outstanding: Diluted shares outstanding.
    """

    revenue: float
    operating_income: float
    interest_expense: float = 0.0
    income_tax_expense: float
    pre_tax_income: float
    shares_outstanding: float


class CashFlowStatement(BaseModel):
    """Cash flow statement metrics for free cash flow calculation.

    Attributes:
        operating_cash_flow: Net cash provided by operating activities (CFO).
        capex: Capital expenditures.
        depr_amort: Depreciation and amortization expenses.
        delta_nwc: Change in net working capital.
    """

    operating_cash_flow: float
    capex: float
    depr_amort: float = 0.0
    delta_nwc: float = 0.0


class BalanceSheet(BaseModel):
    """Balance sheet items for debt and cash adjustments.

    Attributes:
        cash_equiv: Cash and cash equivalents.
        short_term_investments: Short-term liquid marketable securities.
        long_term_investments: Non-current marketable securities.
        short_term_debt: Short-term borrowings and current portion of debt.
        long_term_debt: Non-current debt obligations.
        preferred_stock: Value of preferred equity shares.
        minority_interest: Non-controlling interests in consolidated subsidiaries.
    """

    cash_equiv: float
    short_term_investments: float = 0.0
    long_term_investments: float = 0.0
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    preferred_stock: float = 0.0
    minority_interest: float = 0.0

    @property
    def total_debt(self) -> float:
        return self.short_term_debt + self.long_term_debt


class AnnualFinancials(BaseModel):
    """Financial statements for a specific company and fiscal year.

    Attributes:
        ticker: Stock ticker symbol.
        fiscal_year: Reporting year.
        income_statement: Income statement metrics.
        cash_flow_statement: Cash flow statement metrics.
        balance_sheet: Balance sheet metrics.
    """

    ticker: str
    fiscal_year: int
    income_statement: IncomeStatement
    cash_flow_statement: CashFlowStatement
    balance_sheet: BalanceSheet


class ValuationAssumptions(BaseModel):
    """User-provided assumptions for DCF valuation and WACC.

    Attributes:
        current_share_price: Current share price.
        risk_free_rate: Risk-free rate of return.
        beta: Stock beta (volatility relative to market).
        market_risk_premium: Expected market return above risk-free rate.
        expected_growth_rate: Forecasted annual revenue growth rate.
        perpetual_growth_rate: Long-term terminal growth rate.
        fiscal_horizon: Forecast horizon in years.
    """

    current_share_price: float
    risk_free_rate: float
    beta: float
    market_risk_premium: float
    expected_growth_rate: float
    perpetual_growth_rate: float
    fiscal_horizon: int = 5

    @field_validator(
        "risk_free_rate",
        "market_risk_premium",
        "expected_growth_rate",
        "perpetual_growth_rate",
    )
    @classmethod
    def normalize_percentages(cls, value: float) -> float:
        return value / 100 if value > 1.00 else value
