import pytest
from dcf_calculator.dcf_schemas import AnnualFinancials, ValuationAssumptions
from dcf_calculator.dcf import DiscountedCashFlow


@pytest.fixture
def financials():
    return [
        AnnualFinancials(
            ticker="AAPL",
            fiscal_year="2025",  # Verify Pydantic string -> int coercion
            income_statement={
                "interest_expense": 3_933_000_000,
                "income_tax_expense": 20_719_000_000,
                "pre_tax_income": 132_729_000_000,
                "shares_outstanding": 15_004_697_000,
            },
            cash_flow_statement={
                "operating_cash_flow": 111_482_000_000,
                "capex": 12_715_000_000,
            },
            balance_sheet={
                "cash_equiv": 35_934_000_000,
                "short_term_investments": 18_763_000_000,
                "long_term_investments": 77_723_000_000,
                "short_term_debt": 12_350_000_000,
                "long_term_debt": 78_328_000_000,
            },
        )
    ]


@pytest.fixture
def assumptions():

    return ValuationAssumptions(
        current_stock_price=235,
        risk_free_rate=4,
        beta=1.07,
        market_risk_premium=5.1,
        expected_growth_rate=6,
        perpetual_growth_rate=2.5,
        fiscal_horizon=10,
    )


@pytest.fixture
def dcf(financials, assumptions):
    return DiscountedCashFlow(financials=financials, assumptions=assumptions)


def test_percentage_normalization(assumptions):
    assert assumptions.risk_free_rate == pytest.approx(0.04)
    assert assumptions.market_risk_premium == pytest.approx(0.051)
    assert assumptions.expected_growth_rate == pytest.approx(0.06)
    assert assumptions.perpetual_growth_rate == pytest.approx(0.025)


def test_calculate_effective_tax_rate(dcf, financials, assumptions):
    # Standard effective tax rate (within 0% - 35% range)
    assert dcf.calculate_effective_tax_rate() == pytest.approx(0.1561, abs=1e-4)

    # Upper bound clamping: raw tax rate > 35% (60B / 100B = 60%) clamps to 35%
    financials[0].income_statement.income_tax_expense = 60_000_000_000
    financials[0].income_statement.pre_tax_income = 100_000_000_000
    assert dcf.calculate_effective_tax_rate() == pytest.approx(0.35)

    # Lower bound clamping: tax credit/refund (-10B / 100B = -10%) clamps to 0%
    financials[0].income_statement.income_tax_expense = -10_000_000_000
    assert dcf.calculate_effective_tax_rate() == pytest.approx(0.0)

    # Non-positive pre-tax income: defaults to 21% US statutory tax rate
    financials[0].income_statement.pre_tax_income = -1_000_000
    assert dcf.calculate_effective_tax_rate() == pytest.approx(0.21)


def test_calculate_cost_of_equity(dcf):
    assert dcf.calculate_cost_of_equity() == pytest.approx(0.0946, abs=1e-4)


def test_calculate_pre_tax_cost_debt(dcf, financials):
    assert dcf.calculate_pre_tax_cost_debt() == pytest.approx(0.0434, abs=1e-4)

    # Zero debt case returns 0.0
    financials[0].balance_sheet.short_term_debt = 0.0
    financials[0].balance_sheet.long_term_debt = 0.0
    assert dcf.calculate_pre_tax_cost_debt() == 0.0


def test_calculate_wacc(dcf):
    assert dcf.calculate_wacc() == pytest.approx(0.0931, abs=1e-4)


def test_calculate_base_ufcf(dcf):
    assert dcf.calculate_base_ufcf() == pytest.approx(102086058608.14, abs=1e-2)


def test_project_cash_flows(dcf):
    expected_fcf = [
        108211222124.63,
        114703895452.11,
        121586129179.23,
        128881296929.99,
        136614174745.79,
        144811025230.53,
        153499686744.37,
        162709667949.03,
        172472248025.97,
        182820582907.53,
    ]
    projected = dcf.project_cash_flows()
    assert len(projected) == 10
    assert projected == pytest.approx(expected_fcf, abs=1e-2)


def test_calculate_terminal_value(dcf):
    assert dcf.calculate_terminal_value() == pytest.approx(2751031194964.03, abs=1e-2)

    # Invalid perpetual growth rate (wacc <= g) raises ValueError
    dcf.assumptions.perpetual_growth_rate = 0.15
    wacc = dcf.calculate_wacc()
    g = dcf.assumptions.perpetual_growth_rate

    assert wacc == pytest.approx(0.0931, abs=1e-4)
    assert g == pytest.approx(0.15)
    assert not (wacc > g)

    with pytest.raises(
        ValueError, match=r"WACC must be greater than perpetual growth rate \(g\)\."
    ):
        dcf.calculate_terminal_value()


def test_calculate_enterprise_value(dcf):
    assert dcf.calculate_enterprise_value() == pytest.approx(1994675068697.00, abs=1e-2)


def test_calculate_equity_value(dcf):
    assert dcf.calculate_equity_value() == pytest.approx(2036417068697.00, abs=1e-2)


def test_calculate_implied_share_price(dcf):
    assert dcf.calculate_implied_share_price() == pytest.approx(135.72, abs=1e-2)


def test_run_valuation(dcf):
    result = dcf.run_valuation()

    assert result["effective_tax_rate"] == pytest.approx(0.1561, abs=1e-4)
    assert result["cost_of_equity"] == pytest.approx(0.0946, abs=1e-4)
    assert result["pre_tax_cost_of_debt"] == pytest.approx(0.0434, abs=1e-4)
    assert result["wacc"] == pytest.approx(0.0931, abs=1e-4)
    assert result["base_ufcf"] == pytest.approx(102086058608.14, abs=1e-2)
    assert len(result["projected_cash_flows"]) == 10
    assert result["projected_cash_flows"][0] == pytest.approx(108211222124.63, abs=1e-2)
    assert result["projected_cash_flows"][-1] == pytest.approx(
        182820582907.53, abs=1e-2
    )
    assert result["terminal_value"] == pytest.approx(2751031194964.03, abs=1e-2)
    assert result["enterprise_value"] == pytest.approx(1994675068697.00, abs=1e-2)
    assert result["equity_value"] == pytest.approx(2036417068697.00, abs=1e-2)
    assert result["implied_share_price"] == pytest.approx(135.72, abs=1e-2)
