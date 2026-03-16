"""Unit tests for CoinGecko data vendor."""

# ruff: noqa: S101 - assert is expected in tests
# ruff: noqa: PLC2701 - testing private function is intentional

from tradingagents.dataflows.coingecko import _get_coingecko_id


class TestGetCoingeckoId:
    """Tests for _get_coingecko_id symbol normalization."""

    def test_plain_symbol_btc(self):
        """_get_coingecko_id should resolve plain BTC symbol."""
        result = _get_coingecko_id("BTC")
        assert result == "bitcoin"

    def test_plain_symbol_eth(self):
        """_get_coingecko_id should resolve plain ETH symbol."""
        result = _get_coingecko_id("ETH")
        assert result == "ethereum"

    def test_pair_format_with_dash(self):
        """_get_coingecko_id should extract base currency from BTC-USD format."""
        result = _get_coingecko_id("BTC-USD")
        assert result == "bitcoin"

    def test_pair_format_with_slash(self):
        """_get_coingecko_id should extract base currency from ETH/USDT format."""
        result = _get_coingecko_id("ETH/USDT")
        assert result == "ethereum"

    def test_pair_format_sol_usd(self):
        """_get_coingecko_id should extract base currency from SOL-USD format."""
        result = _get_coingecko_id("SOL-USD")
        assert result == "solana"

    def test_lowercase_symbol(self):
        """_get_coingecko_id should normalize lowercase input."""
        result = _get_coingecko_id("btc-usd")
        assert result == "bitcoin"

    def test_mixed_case_symbol(self):
        """_get_coingecko_id should normalize mixed case input."""
        result = _get_coingecko_id("EtH/UsDt")
        assert result == "ethereum"

    def test_symbol_with_whitespace(self):
        """_get_coingecko_id should strip whitespace."""
        result = _get_coingecko_id("  BTC-USD  ")
        assert result == "bitcoin"

    def test_unknown_symbol_returns_none(self):
        """_get_coingecko_id should return None for unknown symbols."""
        result = _get_coingecko_id("UNKNOWNCOIN")
        assert result is None

    def test_unknown_pair_format_returns_none(self):
        """_get_coingecko_id should return None for unknown symbols in pair format."""
        result = _get_coingecko_id("UNKNOWN-USD")
        assert result is None

    def test_empty_string_returns_none(self):
        """_get_coingecko_id should return None for empty string."""
        result = _get_coingecko_id("")
        assert result is None

    def test_all_common_symbols(self):
        """_get_coingecko_id should resolve all common symbols in mapping."""
        # Test a representative sample from SYMBOL_TO_ID mapping
        test_cases = [
            ("BTC", "bitcoin"),
            ("ETH", "ethereum"),
            ("BNB", "binancecoin"),
            ("XRP", "ripple"),
            ("SOL", "solana"),
            ("ADA", "cardano"),
            ("DOGE", "dogecoin"),
            ("DOT", "polkadot"),
            ("MATIC", "matic-network"),
            ("LTC", "litecoin"),
        ]
        for symbol, expected_id in test_cases:
            result = _get_coingecko_id(symbol)
            assert result == expected_id, (
                f"Expected {symbol} -> {expected_id}, got {result}"
            )
