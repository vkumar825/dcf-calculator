import os
import warnings
from dotenv import load_dotenv
from edgar import Company, set_identity
from edgar.entity import EntityFacts

load_dotenv()

set_identity(os.getenv("EDGAR_IDENTITY"))

FIELD_ALIASES = {
    # Cash Flow Statement
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
    ],
    "depr_amort": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ],
    # Income Statement
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
    ],
    "income_tax_expense": [
        "IncomeTaxExpenseBenefit",
        "CurrentIncomeTaxExpenseBenefit",
    ],
    "pre_tax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "OperatingIncomeLoss",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestAndDebtExpense",
        "InterestExpenseDebt",
    ],
    "shares_outstanding": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingDiluted",
        "EntityCommonStockSharesOutstanding",
    ],
    # Balance Sheet
    "cash_equiv": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalents",
    ],
    "short_term_investments": [
        "MarketableSecuritiesCurrent",
        "AvailableForSaleSecuritiesCurrent",
        "ShortTermInvestments",
    ],
    "long_term_investments": [
        "MarketableSecuritiesNoncurrent",
        "AvailableForSaleSecuritiesNoncurrent",
        "OtherLongTermInvestments",
    ],
    "short_term_debt": [
        "DebtCurrent",
        "ShortTermBorrowings",
        "CommercialPaper",
        "LongTermDebtCurrent",
    ],
    "long_term_debt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ],
    "preferred_stock": [
        "PreferredStockValue",
        "PreferredStockCarryingReportedAmount",
        "PreferredStockValueOutstanding",
    ],
    "minority_interest": [
        "MinoritiesReportedAmount",
        "NoncontrollingInterestInSubsidiaries",
        "NoncontrollingInterestInNetAssetsOfSubsidiaries",
    ],
}


def _extract_metric(
    facts, aliases: list[str], fiscal_year: int, default: float | None = None
) -> float:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        for tag in aliases:
            fact = facts.get_annual_fact(tag, fiscal_year=fiscal_year)

            if fact is not None and fact.numeric_value is not None:
                return float(fact.numeric_value)

    if default is not None:
        return default

    raise ValueError(
        f"Could not find any of tags {aliases} for fiscal year {fiscal_year}"
    )


def get_income_statement(facts: EntityFacts, fiscal_year: int) -> dict[str, float]:
    return {
        "revenue": _extract_metric(facts, FIELD_ALIASES["revenue"], fiscal_year),
        "operating_income": _extract_metric(
            facts, FIELD_ALIASES["operating_income"], fiscal_year
        ),
        "interest_expense": _extract_metric(
            facts, FIELD_ALIASES["interest_expense"], fiscal_year, default=0.0
        ),
        "income_tax_expense": _extract_metric(
            facts, FIELD_ALIASES["income_tax_expense"], fiscal_year
        ),
        "pre_tax_income": _extract_metric(
            facts, FIELD_ALIASES["pre_tax_income"], fiscal_year
        ),
        "shares_outstanding": _extract_metric(
            facts, FIELD_ALIASES["shares_outstanding"], fiscal_year
        ),
    }


def get_cash_flow_statement(facts: EntityFacts, fiscal_year: int) -> dict[str, float]:
    return {
        "operating_cash_flow": _extract_metric(
            facts, FIELD_ALIASES["operating_cash_flow"], fiscal_year
        ),
        "capex": _extract_metric(facts, FIELD_ALIASES["capex"], fiscal_year),
        "depr_amort": _extract_metric(
            facts, FIELD_ALIASES["depr_amort"], fiscal_year, default=0.0
        ),
    }


def get_balance_sheet(facts: EntityFacts, fiscal_year: int) -> dict[str, float]:
    return {
        "cash_equiv": _extract_metric(facts, FIELD_ALIASES["cash_equiv"], fiscal_year),
        "short_term_investments": _extract_metric(
            facts, FIELD_ALIASES["short_term_investments"], fiscal_year, default=0.0
        ),
        "long_term_investments": _extract_metric(
            facts, FIELD_ALIASES["long_term_investments"], fiscal_year, default=0.0
        ),
        "short_term_debt": _extract_metric(
            facts, FIELD_ALIASES["short_term_debt"], fiscal_year, default=0.0
        ),
        "long_term_debt": _extract_metric(
            facts, FIELD_ALIASES["long_term_debt"], fiscal_year, default=0.0
        ),
        "preferred_stock": _extract_metric(
            facts, FIELD_ALIASES["preferred_stock"], fiscal_year, default=0.0
        ),
        "minority_interest": _extract_metric(
            facts, FIELD_ALIASES["minority_interest"], fiscal_year, default=0.0
        ),
    }


def get_annual_financials(
    ticker: str, fiscal_year: int
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:

    try:
        company = Company(ticker)
        facts = company.get_facts()

        income_statement = get_income_statement(facts, fiscal_year)
        cash_flow_statement = get_cash_flow_statement(facts, fiscal_year)
        balance_sheet = get_balance_sheet(facts, fiscal_year)

        return income_statement, cash_flow_statement, balance_sheet

    except Exception:
        return None
