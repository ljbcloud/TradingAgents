from unittest.mock import patch

from graph.propagation import Propagator
from graph.radon_validation import create_radon_validation_node

# ---------------------------------------------------------------------------
# 1. Node creation
# ---------------------------------------------------------------------------


def test_create_radon_validation_node_returns_callable():
    """Factory returns a callable node function."""
    node = create_radon_validation_node()
    assert callable(node)


# ---------------------------------------------------------------------------
# 2. Stock ticker validation — happy path
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_stock_ticker_populates_validation_result(mock_validate):
    """For a stock ticker the node delegates to validate_trade and propagates result."""
    mock_validate.return_value = {
        "radon_validation_result": "PASS",
        "radon_validation_details": {"Ticker": "AAPL", "Status": "PASS"},
    }

    node = create_radon_validation_node()
    state = {
        "company_of_interest": "AAPL",
        "asset_type": "stock",
        "trade_date": "2024-06-01",
        "final_trade_decision": "BUY",
    }

    result = node(state)

    assert result["radon_validation_result"] == "PASS"
    assert result["radon_validation_details"] == {"Ticker": "AAPL", "Status": "PASS"}
    mock_validate.assert_called_once_with(state)


@patch("graph.radon_validation.validate_trade")
def test_stock_ticker_populates_details_as_dict(mock_validate):
    """radon_validation_details is populated as a dict when validate_trade returns one."""
    mock_validate.return_value = {
        "radon_validation_result": "FAIL",
        "radon_validation_details": {"Ticker": "TSLA", "Milestones": "1/3 passed"},
    }

    node = create_radon_validation_node()
    result = node({"company_of_interest": "TSLA", "asset_type": "stock"})

    assert isinstance(result["radon_validation_details"], dict)
    assert result["radon_validation_details"]["Ticker"] == "TSLA"


# ---------------------------------------------------------------------------
# 3. Crypto passthrough
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_crypto_asset_type_returns_skip(mock_validate):
    """Crypto assets skip Radon validation entirely."""
    node = create_radon_validation_node()
    state = {
        "company_of_interest": "BTC",
        "asset_type": "crypto",
    }

    result = node(state)

    assert result["radon_validation_result"] == "SKIP"
    assert result["radon_validation_details"] == {}
    mock_validate.assert_not_called()


def test_crypto_passthrough_empty_details():
    """Crypto skip result has empty details dict."""
    node = create_radon_validation_node()
    result = node({"asset_type": "crypto"})

    assert result == {"radon_validation_result": "SKIP", "radon_validation_details": {}}


# ---------------------------------------------------------------------------
# 4. All deps unavailable — validate_trade raises
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_validate_trade_exception_returns_error(mock_validate):
    """When validate_trade raises, the node returns ERROR gracefully."""
    mock_validate.side_effect = RuntimeError("Radon unavailable")

    node = create_radon_validation_node()
    result = node({"company_of_interest": "AAPL", "asset_type": "stock"})

    assert result["radon_validation_result"] == "ERROR"
    assert result["radon_validation_details"] == {}


@patch("graph.radon_validation.validate_trade")
def test_validate_trade_import_error_returns_error(mock_validate):
    """ImportError from validate_trade is caught and returns ERROR."""
    mock_validate.side_effect = ImportError("Missing radon deps")

    node = create_radon_validation_node()
    result = node({"company_of_interest": "MSFT", "asset_type": "stock"})

    assert result["radon_validation_result"] == "ERROR"
    assert result["radon_validation_details"] == {}


# ---------------------------------------------------------------------------
# 5. State preservation — input state not mutated, only radon keys updated
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_input_state_preserved_only_radon_keys_updated(mock_validate):
    """The node returns only radon keys without modifying the input state dict."""
    mock_validate.return_value = {
        "radon_validation_result": "PASS",
        "radon_validation_details": {"summary": "ok"},
    }

    node = create_radon_validation_node()
    state = {
        "company_of_interest": "AAPL",
        "asset_type": "stock",
        "trade_date": "2024-01-15",
        "final_trade_decision": "BUY",
        "market_report": "Bullish",
    }

    result = node(state)

    assert state["market_report"] == "Bullish"
    assert state["final_trade_decision"] == "BUY"
    assert set(result.keys()) == {"radon_validation_result", "radon_validation_details"}


def test_crypto_passthrough_preserves_input_state():
    """Crypto passthrough does not alter the input state dict."""
    node = create_radon_validation_node()
    state = {
        "company_of_interest": "ETH",
        "asset_type": "crypto",
        "final_trade_decision": "HOLD",
    }

    result = node(state)

    assert state["final_trade_decision"] == "HOLD"
    assert set(result.keys()) == {"radon_validation_result", "radon_validation_details"}


# ---------------------------------------------------------------------------
# 6. Required state fields — company_of_interest and asset_type
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_missing_company_of_interest_defaults_to_empty_string(mock_validate):
    """When company_of_interest is absent, validate_trade still gets called with the state."""
    mock_validate.return_value = {
        "radon_validation_result": "UNAVAILABLE",
        "radon_validation_details": "Skipped",
    }

    node = create_radon_validation_node()
    result = node({"asset_type": "stock"})

    mock_validate.assert_called_once()
    assert "radon_validation_result" in result


def test_missing_asset_type_defaults_to_stock():
    """When asset_type is absent it defaults to 'stock' — validate_trade is called."""
    with patch("graph.radon_validation.validate_trade") as mock_validate:
        mock_validate.return_value = {
            "radon_validation_result": "PASS",
            "radon_validation_details": {},
        }

        node = create_radon_validation_node()
        result = node({"company_of_interest": "AAPL"})

        mock_validate.assert_called_once()
        assert result["radon_validation_result"] == "PASS"


# ---------------------------------------------------------------------------
# 7. State transition — simulated Risk Judge → Radon Validation
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_state_transition_from_risk_judge_to_radon(mock_validate):
    """Simulates state flowing from Risk Judge output into the Radon node."""
    mock_validate.return_value = {
        "radon_validation_result": "PASS",
        "radon_validation_details": {"Ticker": "NVDA", "Milestones": "3/3 passed"},
    }

    incoming_state = {
        "company_of_interest": "NVDA",
        "asset_type": "stock",
        "trade_date": "2024-03-01",
        "final_trade_decision": "BUY",
        "risk_debate_state": {
            "history": "Aggressive: Buy\nConservative: Hold",
            "count": 3,
            "latest_speaker": "Judge",
            "judge_decision": "Buy",
        },
        "messages": [],
    }

    node = create_radon_validation_node()
    result = node(incoming_state)

    assert result["radon_validation_result"] == "PASS"
    assert isinstance(result["radon_validation_details"], dict)
    assert result["radon_validation_details"]["Ticker"] == "NVDA"


@patch("graph.radon_validation.validate_trade")
def test_state_transition_with_prior_radon_fields_overwritten(mock_validate):
    """If state already has radon fields, the node overwrites them."""
    mock_validate.return_value = {
        "radon_validation_result": "FAIL",
        "radon_validation_details": {"reason": "insufficient data"},
    }

    node = create_radon_validation_node()
    state = {
        "company_of_interest": "AMD",
        "asset_type": "stock",
        "radon_validation_result": "",
        "radon_validation_details": {},
    }

    result = node(state)

    assert result["radon_validation_result"] == "FAIL"
    assert result["radon_validation_details"]["reason"] == "insufficient data"


# ---------------------------------------------------------------------------
# 8. create_initial_state integration — radon defaults
# ---------------------------------------------------------------------------


def test_initial_state_includes_radon_defaults():
    """create_initial_state populates radon fields with empty defaults."""
    propagator = Propagator()
    state = propagator.create_initial_state("AAPL", "2024-06-01")

    assert "radon_validation_result" in state
    assert state["radon_validation_result"] == ""
    assert "radon_validation_details" in state
    assert state["radon_validation_details"] == {}


def test_initial_state_radon_result_is_string():
    """radon_validation_result in initial state is a string."""
    propagator = Propagator()
    state = propagator.create_initial_state("TSLA", "2024-01-01")

    assert isinstance(state["radon_validation_result"], str)


def test_initial_state_radon_details_is_dict():
    """radon_validation_details in initial state is a dict."""
    propagator = Propagator()
    state = propagator.create_initial_state("MSFT", "2024-01-01")

    assert isinstance(state["radon_validation_details"], dict)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@patch("graph.radon_validation.validate_trade")
def test_validate_trade_returns_missing_result_key(mock_validate):
    """When validate_trade omits radon_validation_result, node defaults to empty string."""
    mock_validate.return_value = {
        "radon_validation_details": {"summary": "partial"},
    }

    node = create_radon_validation_node()
    result = node({"company_of_interest": "GOOG", "asset_type": "stock"})

    assert result["radon_validation_result"] == ""
    assert result["radon_validation_details"] == {"summary": "partial"}


@patch("graph.radon_validation.validate_trade")
def test_validate_trade_returns_missing_details_key(mock_validate):
    """When validate_trade omits radon_validation_details, node defaults to empty dict."""
    mock_validate.return_value = {
        "radon_validation_result": "PASS",
    }

    node = create_radon_validation_node()
    result = node({"company_of_interest": "META", "asset_type": "stock"})

    assert result["radon_validation_result"] == "PASS"
    assert result["radon_validation_details"] == {}


def test_node_created_independently_multiple_times():
    """Each factory call returns a new function instance."""
    node_a = create_radon_validation_node()
    node_b = create_radon_validation_node()
    assert node_a is not node_b
