import datetime
from edgar.entity import EntityFacts
from edgar.entity.models import FinancialFact
from dcf_calculator.fetch_edgar import _derive_operating_income


def test_derive_operating_income():
    # 1. Exact match via OperatingProfitLoss
    op_profit_fact = FinancialFact(
        concept="OperatingProfitLoss",
        taxonomy="us-gaap",
        label="Operating Profit",
        value=5_000_000_000.0,
        numeric_value=5_000_000_000.0,
        unit="USD",
        fiscal_year=2024,
        fiscal_period="FY",
        period_end=datetime.date(2024, 12, 31),
        filing_date=datetime.date(2025, 2, 1),
        form_type="10-K",
    )
    entity_facts_op = EntityFacts(cik=123456, name="Exact Co", facts=[op_profit_fact])
    assert _derive_operating_income(entity_facts_op, 2024) == 5_000_000_000.0

    # 2. Fallback derivation via Gross Profit - SG&A
    gp_fact = FinancialFact(
        concept="GrossProfit",
        taxonomy="us-gaap",
        label="Gross Profit",
        value=22_887_000_000.0,
        numeric_value=22_887_000_000.0,
        unit="USD",
        fiscal_year=2024,
        fiscal_period="FY",
        period_end=datetime.date(2024, 5, 31),
        filing_date=datetime.date(2024, 7, 23),
        form_type="10-K",
    )
    sga_fact = FinancialFact(
        concept="SellingGeneralAndAdministrativeExpense",
        taxonomy="us-gaap",
        label="Selling and Administrative Expense",
        value=16_576_000_000.0,
        numeric_value=16_576_000_000.0,
        unit="USD",
        fiscal_year=2024,
        fiscal_period="FY",
        period_end=datetime.date(2024, 5, 31),
        filing_date=datetime.date(2024, 7, 23),
        form_type="10-K",
    )
    entity_facts_gp_sga = EntityFacts(
        cik=320187, name="NIKE, Inc.", facts=[gp_fact, sga_fact]
    )
    assert _derive_operating_income(entity_facts_gp_sga, 2024) == 6_311_000_000.0
