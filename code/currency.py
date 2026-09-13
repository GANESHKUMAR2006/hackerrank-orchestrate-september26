"""
Currency conversion module using strictly dataset/exchange_rates.csv.
"""

import csv
import os
from typing import Dict, Tuple, Optional

class CurrencyConverter:
    def __init__(self, exchange_rates_path: Optional[str] = None):
        if exchange_rates_path is None:
            exchange_rates_path = os.path.join(
                os.path.dirname(__file__), "..", "dataset", "exchange_rates.csv"
            )
        self.exchange_rates_path = exchange_rates_path
        self.rates: Dict[Tuple[str, str, str], float] = {}
        self._load_rates()

    def _load_rates(self):
        if not os.path.exists(self.exchange_rates_path):
            raise FileNotFoundError(f"Exchange rates file not found at: {self.exchange_rates_path}")
        with open(self.exchange_rates_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["rate_date"].strip()
                from_curr = row["from_currency"].strip().upper()
                to_curr = row["to_currency"].strip().upper()
                rate = float(row["rate"].strip())
                self.rates[(date, from_curr, to_curr)] = rate

    def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        rate_date: str
    ) -> float:
        """
        Convert an amount from from_currency to to_currency using dated exchange rates.
        Fails loudly if the required conversion rate cannot be resolved.
        """
        from_curr = from_currency.strip().upper()
        to_curr = to_currency.strip().upper()
        rate_date = rate_date.strip()

        if from_curr == to_curr:
            return float(amount)

        # 1. Direct rate lookup
        direct_key = (rate_date, from_curr, to_curr)
        if direct_key in self.rates:
            return round(amount * self.rates[direct_key], 4)

        # 2. Inverse rate lookup
        inverse_key = (rate_date, to_curr, from_curr)
        if inverse_key in self.rates:
            inv_rate = self.rates[inverse_key]
            if inv_rate == 0:
                raise ZeroDivisionError(f"Exchange rate for {inverse_key} is zero.")
            return round(amount / inv_rate, 4)

        raise ValueError(
            f"No exchange rate found for {from_curr} -> {to_curr} on date {rate_date}. "
            f"Cannot perform conversion without inventing rates."
        )

# Global default instance for convenience
_default_converter: Optional[CurrencyConverter] = None

def get_default_converter() -> CurrencyConverter:
    global _default_converter
    if _default_converter is None:
        _default_converter = CurrencyConverter()
    return _default_converter

def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    rate_date: str
) -> float:
    """Convenience function delegating to default CurrencyConverter instance."""
    return get_default_converter().convert_amount(amount, from_currency, to_currency, rate_date)
