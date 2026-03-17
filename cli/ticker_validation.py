"""Ticker symbol validation using yfinance.

Provides validation and disambiguation for stock and crypto ticker symbols
before passing them to trading agents.
"""

import sys
from dataclasses import dataclass

import questionary
import yfinance as yf
from rich.console import Console

from cli.ticker_validation_config import (
    AMBIGUITY_THRESHOLD,
    VALIDATION_TIMEOUT,
)

console = Console()


@dataclass
class TickerValidationResult:
    is_valid: bool
    symbol: str
    company_name: str | None = None
    security_type: str | None = None
    error_message: str | None = None
    is_ambiguous: bool = False
    matches: list[dict] | None = None
    is_fallback: bool = False


def validate_ticker(
    symbol: str, timeout: float | None = None
) -> TickerValidationResult:
    if timeout is None:
        timeout = VALIDATION_TIMEOUT

    normalized = symbol.strip().upper()

    try:
        ticker = yf.Ticker(normalized)
        info = ticker.info

        if not info or not info.get("symbol"):
            return TickerValidationResult(
                is_valid=False,
                symbol=normalized,
                error_message=f"Ticker '{normalized}' not found. Please verify the symbol.",
            )

        return TickerValidationResult(
            is_valid=True,
            symbol=normalized,
            company_name=info.get("longName"),
            security_type=info.get("quoteType", "UNKNOWN"),
        )

    except Exception:
        return TickerValidationResult(
            is_valid=True,
            symbol=normalized,
            is_fallback=True,
        )


def search_ticker(query: str, max_results: int | None = None) -> list[dict]:
    if max_results is None:
        max_results = AMBIGUITY_THRESHOLD

    try:
        search = yf.Search(query, max_results=max_results)
        quotes = search.quotes or []

        return [
            {
                "symbol": q.get("symbol", ""),
                "shortname": q.get("shortname", ""),
                "longname": q.get("longname", ""),
                "quoteType": q.get("quoteType", ""),
                "exchange": q.get("exchange", ""),
            }
            for q in quotes[:max_results]
        ]
    except Exception:
        return []


def check_ambiguity(
    symbol: str, threshold: int | None = None
) -> TickerValidationResult:
    if threshold is None:
        threshold = AMBIGUITY_THRESHOLD

    normalized = symbol.strip().upper()

    try:
        matches = search_ticker(normalized)

        if len(matches) <= 1:
            return TickerValidationResult(
                is_valid=True,
                symbol=normalized,
                is_ambiguous=False,
            )

        exact_matches = [m for m in matches if m.get("symbol") == normalized]

        if len(exact_matches) == 1:
            return TickerValidationResult(
                is_valid=True,
                symbol=normalized,
                company_name=exact_matches[0].get("shortname")
                or exact_matches[0].get("longname"),
                is_ambiguous=False,
            )

        return TickerValidationResult(
            is_valid=True,
            symbol=normalized,
            is_ambiguous=True,
            matches=matches[:threshold],
        )
    except Exception:
        return TickerValidationResult(
            is_valid=True,
            symbol=normalized,
            is_ambiguous=False,
        )


def get_validated_ticker(symbol: str) -> str:
    normalized = symbol.strip().upper()

    if not normalized:
        console.print("[red]Error: No ticker symbol provided.[/red]")
        sys.exit(1)

    validation = validate_ticker(normalized)

    if not validation.is_valid:
        console.print(f"[red]Error: {validation.error_message}[/red]")
        sys.exit(1)

    if validation.is_fallback:
        console.print(
            f"[yellow]Warning: Could not validate '{normalized}' "
            "(network error). Proceeding with unvalidated input.[/yellow]"
        )
        return normalized

    ambiguity = check_ambiguity(normalized)

    if ambiguity.is_ambiguous and ambiguity.matches:
        console.print(f"[yellow]Multiple matches found for '{normalized}':[/yellow]")

        choices = [
            questionary.Choice(
                f"{m['symbol']} - {m.get('shortname', 'Unknown')}",
                value=m["symbol"],
            )
            for m in ambiguity.matches
        ]

        selected = questionary.select(
            "Please select the correct ticker:",
            choices=choices,
        ).ask()

        if not selected:
            console.print("[red]No selection made. Exiting...[/red]")
            sys.exit(1)

        return selected

    if validation.company_name:
        confirmed = questionary.confirm(
            f"Found: {validation.company_name} ({validation.symbol}). Continue?",
            default=True,
        ).ask()

        if not confirmed:
            console.print("[red]Ticker not confirmed. Exiting...[/red]")
            sys.exit(1)

    return normalized
