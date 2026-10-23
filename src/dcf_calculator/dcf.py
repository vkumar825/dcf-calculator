from pydantic import BaseModel

from dcf_calculator.dcf_schemas import AnnualFinancials, ValuationAssumptions


class DiscountedCashFlow(BaseModel):
    financials: list[AnnualFinancials]
    assumptions: ValuationAssumptions

    def get_latest_financials(self) -> AnnualFinancials:
        return self.financials[-1]

    def calculate_effective_tax_rate(self) -> float:
        income_statement = self.get_latest_financials().income_statement
        total_tax_expense = income_statement.income_tax_expense
        pre_tax_income = income_statement.pre_tax_income

        US_FEDERAL_RATE = 0.21
        MAX_TAX_RATE = 0.35

        if pre_tax_income > 0:
            raw_tax_rate = total_tax_expense / pre_tax_income

            # Clamping between 0% and the maximum tax rate of 35%
            return max(0.0, min(raw_tax_rate, MAX_TAX_RATE))

        else:
            # Default to federal statutory rate of 21%
            return US_FEDERAL_RATE

    def calculate_cost_of_equity(self) -> float:
        assumptions = self.assumptions
        risk_free_rate = assumptions.risk_free_rate
        beta = assumptions.beta
        market_risk_premium = assumptions.market_risk_premium

        # Using Capital Asset Pricing Model (CAPM) formula to calculate cost of equity
        cost_of_equity = risk_free_rate + (beta * market_risk_premium)

        return cost_of_equity

    def calculate_pre_tax_cost_debt(self) -> float:
        balance_sheet = self.get_latest_financials().balance_sheet
        income_statement = self.get_latest_financials().income_statement

        if balance_sheet.total_debt > 0:
            return income_statement.interest_expense / balance_sheet.total_debt

        return 0.0

    def calculate_wacc(self) -> float:
        assumptions = self.assumptions
        income_statement = self.get_latest_financials().income_statement
        balance_sheet = self.get_latest_financials().balance_sheet

        current_stock_price = assumptions.current_stock_price
        cost_of_debt = self.calculate_pre_tax_cost_debt()
        outstanding_shares = income_statement.shares_outstanding
        total_debt = balance_sheet.total_debt

        effective_tax_rate = self.calculate_effective_tax_rate()
        cost_of_equity = self.calculate_cost_of_equity()

        market_capitalization = current_stock_price * outstanding_shares
        total_value_of_capital = market_capitalization + total_debt
        equity_weight = market_capitalization / total_value_of_capital
        debt_weight = total_debt / total_value_of_capital

        # Using Weighted Average Cost of Capital formula to calculate discount rate
        wacc = (equity_weight * cost_of_equity) + (
            debt_weight * cost_of_debt * (1 - effective_tax_rate)
        )

        return wacc

    def calculate_base_ufcf(self) -> float:
        income_statement = self.get_latest_financials().income_statement
        cash_flow_statement = self.get_latest_financials().cash_flow_statement

        cfo = cash_flow_statement.operating_cash_flow
        capex = abs(cash_flow_statement.capex)
        effective_tax_rate = self.calculate_effective_tax_rate()
        interest_expense = income_statement.interest_expense

        # Deriving Unlevered Free Cash Flow from Cash Flow from Operations
        ufcf = cfo - capex + (interest_expense * (1 - effective_tax_rate))

        return ufcf

    def project_cash_flows(self) -> list[float]:
        assumptions = self.assumptions

        base_ufcf = self.calculate_base_ufcf()
        revenue_growth_rate = assumptions.expected_growth_rate
        fiscal_horizon = assumptions.fiscal_horizon

        projected_cash_flows = []

        for t in range(1, fiscal_horizon + 1):
            projected_ufcf = base_ufcf * (1 + revenue_growth_rate) ** t
            projected_cash_flows.append(projected_ufcf)

        return projected_cash_flows

    def calculate_terminal_value(self) -> float:
        assumptions = self.assumptions

        final_fcf = self.project_cash_flows()[-1]
        g = assumptions.perpetual_growth_rate
        wacc = self.calculate_wacc()

        if wacc <= g:
            raise ValueError("WACC must be greater than perpetual growth rate (g).")

        terminal_value = (final_fcf * (1 + g)) / (wacc - g)

        return terminal_value

    def calculate_enterprise_value(self) -> float:
        projected_cash_flows = self.project_cash_flows()
        wacc = self.calculate_wacc()
        terminal_value = self.calculate_terminal_value()
        n = len(projected_cash_flows)  # represents the final year

        present_values = []

        for t, ufcf in enumerate(projected_cash_flows, start=1):
            pv = ufcf / ((1 + wacc) ** t)
            present_values.append(pv)

        sum_of_present_values = sum(present_values)

        pv_of_terminal_value = terminal_value / ((1 + wacc) ** n)

        enterprise_value = sum_of_present_values + pv_of_terminal_value

        return enterprise_value

    def calculate_equity_value(self) -> float:
        balance_sheet = self.get_latest_financials().balance_sheet

        enterprise_value = self.calculate_enterprise_value()

        total_liquid_cash = (
            balance_sheet.cash_equiv
            + balance_sheet.long_term_investments
            + balance_sheet.short_term_investments
        )

        equity_value = (
            enterprise_value
            + total_liquid_cash
            - balance_sheet.total_debt
            - balance_sheet.preferred_stock
            - balance_sheet.minority_interest
        )

        return equity_value

    def calculate_implied_share_price(self) -> float:
        income_statement = self.get_latest_financials().income_statement
        equity_value = self.calculate_equity_value()

        implied_share_price = equity_value / income_statement.shares_outstanding

        return implied_share_price

    def run_valuation(self) -> dict[str, float | list[float]]:
        return {
            "effective_tax_rate": self.calculate_effective_tax_rate(),
            "cost_of_equity": self.calculate_cost_of_equity(),
            "pre_tax_cost_of_debt": self.calculate_pre_tax_cost_debt(),
            "wacc": self.calculate_wacc(),
            "base_ufcf": self.calculate_base_ufcf(),
            "projected_cash_flows": self.project_cash_flows(),
            "terminal_value": self.calculate_terminal_value(),
            "enterprise_value": self.calculate_enterprise_value(),
            "equity_value": self.calculate_equity_value(),
            "implied_share_price": self.calculate_implied_share_price(),
        }
