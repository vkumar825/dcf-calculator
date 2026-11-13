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
                "revenue": 416_161_000_000,
                "operating_income": 133_050_000_000,
                "interest_expense": 0.0,
                "income_tax_expense": 20_719_000_000,
                "pre_tax_income": 132_729_000_000,
                "shares_outstanding": 15_004_697_000,
            },
            cash_flow_statement={
                "operating_cash_flow": 111_482_000_000,
                "capex": 12_715_000_000,
                "depr_amort": 11_698_000_000,
                "delta_nwc": 0.0,
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


def test_calculate_pre_tax_cost_of_debt(dcf, financials):
    # Fallback case: interest_expense == 0.0 estimates borrowing cost at risk_free_rate + 1.5% (4% + 1.5% = 5.5%)
    assert dcf.calculate_pre_tax_cost_of_debt() == pytest.approx(0.055)

    # Standard case: when interest_expense > 0, calculates interest_expense / total_debt
    financials[0].income_statement.interest_expense = 3_933_000_000
    assert dcf.calculate_pre_tax_cost_of_debt() == pytest.approx(0.0434, abs=1e-4)

    # Zero debt case returns 0.0
    financials[0].balance_sheet.short_term_debt = 0.0
    financials[0].balance_sheet.long_term_debt = 0.0
    assert dcf.calculate_pre_tax_cost_of_debt() == 0.0

    # Reset for other tests
    financials[0].income_statement.interest_expense = 0.0
    financials[0].balance_sheet.short_term_debt = 12_350_000_000
    financials[0].balance_sheet.long_term_debt = 78_328_000_000


def test_calculate_wacc(dcf):
    assert dcf.calculate_wacc() == pytest.approx(0.0934, abs=1e-4)


def test_calculate_base_ufcf(dcf, financials):
    # Baseline with D&A added back and delta_nwc = 0.0
    assert dcf.calculate_base_ufcf() == pytest.approx(111263891892.50, abs=1e-2)

    # Edge-case: Non-zero positive delta_nwc reduces free cash flow
    financials[0].cash_flow_statement.delta_nwc = 2_000_000_000
    assert dcf.calculate_base_ufcf() == pytest.approx(109263891892.50, abs=1e-2)

    # Edge-case: Zero D&A fallback (when EDGAR cannot find D&A)
    financials[0].cash_flow_statement.delta_nwc = 0.0
    financials[0].cash_flow_statement.depr_amort = 0.0
    assert dcf.calculate_base_ufcf() == pytest.approx(99565891892.50, abs=1e-2)


def test_generate_projection_schedule(dcf):
    schedule = dcf.generate_projection_schedule()

    # Total entries should be fiscal_horizon + 1 (Year 0 + Years 1-10)
    assert len(schedule) == 11

    # Verify Year 0 (Historical Base)
    y0 = schedule[0]
    assert y0["year"] == 0
    assert y0["revenue"] == 416_161_000_000
    assert y0["operating_income"] == 133_050_000_000
    assert y0["ufcf"] == pytest.approx(111263891892.50, abs=1e-2)
    assert y0["discount_factor"] == 1.0
    assert y0["present_value"] == pytest.approx(111263891892.50, abs=1e-2)

    # Verify Year 1 (First Projected Year at 6% growth)
    y1 = schedule[1]
    assert y1["year"] == 1
    assert y1["revenue"] == pytest.approx(441130660000.0, abs=1e-2)
    assert y1["operating_income"] == pytest.approx(141033000000.0, abs=1e-2)
    assert y1["ufcf"] == pytest.approx(117939725406.05, abs=1e-2)
    assert y1["discount_factor"] == pytest.approx(0.9146, abs=1e-4)
    assert y1["present_value"] == pytest.approx(107868805570.52, abs=1e-2)

    # Verify Year 10 (Final Projected Year)
    y10 = schedule[10]
    assert y10["year"] == 10
    assert y10["revenue"] == pytest.approx(745280968240.97, abs=1e-2)
    assert y10["operating_income"] == pytest.approx(238272286025.03, abs=1e-2)
    assert y10["ufcf"] == pytest.approx(199256684504.08, abs=1e-2)
    assert y10["discount_factor"] == pytest.approx(0.4096, abs=1e-4)
    assert y10["present_value"] == pytest.approx(81615092086.03, abs=1e-2)

    # Verify all expected column keys exist in each row
    expected_keys = {
        "year",
        "revenue",
        "operating_income",
        "nopat",
        "depr_amort",
        "capex",
        "ufcf",
        "discount_factor",
        "present_value",
    }
    for row in schedule:
        assert set(row.keys()) == expected_keys


def test_project_cash_flows(dcf):
    expected_fcf = [
        117939725406.05,
        125016108930.42,
        132517075466.24,
        140468099994.22,
        148896185993.87,
        157829957153.50,
        167299754582.71,
        177337739857.67,
        187978004249.13,
        199256684504.08,
    ]
    projected = dcf.project_cash_flows()
    assert len(projected) == 10
    assert projected == pytest.approx(expected_fcf, abs=1e-2)


def test_calculate_terminal_value(dcf):
    assert dcf.calculate_terminal_value() == pytest.approx(2987567597947.72, abs=1e-2)

    # Invalid perpetual growth rate (wacc <= g) raises ValueError
    dcf.assumptions.perpetual_growth_rate = 0.15
    wacc = dcf.calculate_wacc()
    g = dcf.assumptions.perpetual_growth_rate

    assert wacc == pytest.approx(0.0934, abs=1e-4)
    assert g == pytest.approx(0.15)
    assert not (wacc > g)

    with pytest.raises(
        ValueError, match=r"WACC must be greater than perpetual growth rate \(g\)\."
    ):
        dcf.calculate_terminal_value()


def test_calculate_enterprise_value(dcf):
    assert dcf.calculate_enterprise_value() == pytest.approx(2165703743828.87, abs=1e-2)


def test_calculate_equity_value(dcf):
    assert dcf.calculate_equity_value() == pytest.approx(2207445743828.87, abs=1e-2)


def test_calculate_implied_share_price(dcf):
    assert dcf.calculate_implied_share_price() == pytest.approx(147.12, abs=1e-2)


def test_run_valuation(dcf):
    result = dcf.run_valuation()

    assert result["effective_tax_rate"] == pytest.approx(0.1561, abs=1e-4)
    assert result["cost_of_equity"] == pytest.approx(0.0946, abs=1e-4)
    assert result["pre_tax_cost_of_debt"] == pytest.approx(0.055, abs=1e-4)
    assert result["wacc"] == pytest.approx(0.0934, abs=1e-4)
    assert result["base_ufcf"] == pytest.approx(111263891892.50, abs=1e-2)
    assert len(result["projection_schedule"]) == 11
    assert result["projection_schedule"][0]["year"] == 0
    assert result["projection_schedule"][-1]["year"] == 10
    assert result["terminal_value"] == pytest.approx(2987567597947.72, abs=1e-2)
    assert result["enterprise_value"] == pytest.approx(2165703743828.87, abs=1e-2)
    assert result["equity_value"] == pytest.approx(2207445743828.87, abs=1e-2)
    assert result["implied_share_price"] == pytest.approx(147.12, abs=1e-2)
