from pydantic import BaseModel, model_validator


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
        long_term_investments: Non-current marketable securities.
        short_term_debt: Short-term borrowings and current portion of debt.
        long_term_debt: Non-current debt obligations.
        total_debt: Computed property summing short-term and long-term debt.
    """

    cash_equiv: float
    short_term_investments: float
    long_term_investments: float
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

    @model_validator(mode="after")
    def normalize_to_base_units(self):
        dollar_multiplier = 1.0
        unit = self.dollars_unit.lower().strip()
        if unit in ("millions", "million"):
            dollar_multiplier = 1_000_000.0
        elif unit in ("thousands", "thousand"):
            dollar_multiplier = 1_000.0
        elif unit in ("billions", "billion"):
            dollar_multiplier = 1_000_000_000.0

        share_multiplier = 1.0
        s_unit = self.shares_unit.lower().strip()
        if s_unit in ("thousands", "thousand"):
            share_multiplier = 1_000.0
        elif s_unit in ("millions", "million"):
            share_multiplier = 1_000_000.0
        elif s_unit in ("billions", "billion"):
            share_multiplier = 1_000_000_000.0

        # Scale dollar fields across statements to raw dollars ($1.00)
        if dollar_multiplier != 1.0:
            # Income Statement
            self.income_statement.revenue *= dollar_multiplier
            self.income_statement.ebit *= dollar_multiplier
            self.income_statement.income_tax_expense *= dollar_multiplier
            self.income_statement.pre_tax_income *= dollar_multiplier

            # Cash Flow Statement
            self.cash_flow_statement.depr_amort *= dollar_multiplier
            self.cash_flow_statement.capex *= dollar_multiplier
            self.cash_flow_statement.delta_nwc *= dollar_multiplier

            # Balance Sheet
            self.balance_sheet.cash_equiv *= dollar_multiplier
            self.balance_sheet.short_term_investments *= dollar_multiplier
            self.balance_sheet.long_term_investments *= dollar_multiplier
            self.balance_sheet.short_term_debt *= dollar_multiplier
            self.balance_sheet.long_term_debt *= dollar_multiplier

            self.dollars_unit = "ones"

        # Scale share counts to raw shares (1.0)
        if share_multiplier != 1.0:
            self.income_statement.shares_outstanding *= share_multiplier
            self.shares_unit = "shares"

        return self


class ValuationAssumptions(BaseModel):
    """User-provided assumptions for DCF valuation and WACC.

    Attributes:
        risk_free_rate: Risk-free rate of return.
        beta: Stock beta (volatility relative to market).
        current_stock_price: Current share price.
        pre_tax_cost_debt: Effective interest rate on debt.
        expected_growth_rate: Forecasted annual revenue growth rate.
        perpetual_growth_rate: Long-term terminal growth rate.
        fiscal_horizon: Forecast horizon in years.
        market_risk_premium: Expected market return above risk-free rate.
    """

    risk_free_rate: float
    beta: float
    current_stock_price: float
    pre_tax_cost_debt: float
    expected_growth_rate: float
    perpetual_growth_rate: float
    fiscal_horizon: int
    market_risk_premium: float
