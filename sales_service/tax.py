"""
Simple tax calculation for US (sales tax) and GB (VAT).
Extend with a proper tax engine (e.g., TaxJar) in production.
"""
from decimal import Decimal

# US state tax rates (sample — add all 50 states for production)
US_STATE_TAX = {
    "CA": Decimal("0.0725"),
    "NY": Decimal("0.08"),
    "TX": Decimal("0.0625"),
    "WA": Decimal("0.065"),
    "FL": Decimal("0.06"),
}

GB_VAT_RATE = Decimal("0.20")
DEFAULT_RATE = Decimal("0.08")


def calculate_tax(subtotal: Decimal, country_code: str, state_code: str | None = None) -> Decimal:
    if country_code == "GB":
        return (subtotal * GB_VAT_RATE).quantize(Decimal("0.01"))
    if country_code == "US" and state_code:
        rate = US_STATE_TAX.get(state_code.upper(), DEFAULT_RATE)
        return (subtotal * rate).quantize(Decimal("0.01"))
    return (subtotal * DEFAULT_RATE).quantize(Decimal("0.01"))
