"""Third-party currency conversion (Frankfurter / ECB rates).

Used only to *display* the inventory valuation in other currencies. Inventory
operations never depend on it: on timeout, connection failure or an invalid
payload we log the problem and fall back to bundled reference rates.
"""
import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("inventory.app")

CACHE_KEY = "currency_rates_v1"
CACHE_SECONDS = 60 * 60
TARGET_CURRENCIES = ("EUR", "GBP", "INR", "JPY")

# Approximate reference rates (USD base) used only when the live API is unavailable.
FALLBACK_RATES = {"EUR": 0.92, "GBP": 0.78, "INR": 84.0, "JPY": 150.0}
FALLBACK_DATE = "reference rates"


class CurrencyAPIError(Exception):
    pass


def _fetch_live_rates(base, symbols, timeout):
    try:
        response = requests.get(
            settings.CURRENCY_API_URL,
            params={"from": base, "to": ",".join(symbols)},
            timeout=timeout,
            headers={"Accept": "application/json", "User-Agent": "InventoryManagementSystem/1.0"},
        )
    except requests.Timeout as exc:
        raise CurrencyAPIError(f"timeout after {timeout}s") from exc
    except requests.ConnectionError as exc:
        raise CurrencyAPIError("connection error") from exc
    except requests.RequestException as exc:
        raise CurrencyAPIError(f"request failed: {exc.__class__.__name__}") from exc

    if response.status_code != 200:
        raise CurrencyAPIError(f"unexpected HTTP status {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise CurrencyAPIError("response was not valid JSON") from exc

    rates = payload.get("rates") if isinstance(payload, dict) else None
    if not isinstance(rates, dict):
        raise CurrencyAPIError("response missing 'rates'")
    cleaned = {}
    for code in symbols:
        value = rates.get(code)
        if not isinstance(value, (int, float)) or value <= 0:
            raise CurrencyAPIError(f"invalid rate for {code}")
        cleaned[code] = float(value)
    return {"rates": cleaned, "date": str(payload.get("date", "")), "source": "live", "provider": "Frankfurter (ECB)"}


def get_exchange_rates(use_cache=True):
    base = settings.BASE_CURRENCY
    if use_cache:
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached
    try:
        data = _fetch_live_rates(base, TARGET_CURRENCIES, settings.CURRENCY_API_TIMEOUT)
        logger.info("Currency API success base=%s date=%s", base, data["date"])
        ttl = CACHE_SECONDS
    except CurrencyAPIError as exc:
        logger.warning("Currency API unavailable (%s); using fallback rates", exc)
        data = {"rates": dict(FALLBACK_RATES), "date": FALLBACK_DATE, "source": "fallback",
                "provider": "Built-in reference rates", "error": str(exc)}
        ttl = 300  # retry the live API again after 5 minutes
    data["base"] = base
    cache.set(CACHE_KEY, data, ttl)
    return data


def convert_valuation(amount):
    data = get_exchange_rates()
    amount = Decimal(amount or 0)
    converted = [
        {"currency": code, "rate": rate, "amount": (amount * Decimal(str(rate))).quantize(Decimal("0.01"))}
        for code, rate in data["rates"].items()
    ]
    return {**data, "converted": converted}
