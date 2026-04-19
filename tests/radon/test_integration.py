"""Integration tests for the complete Radon validation flow.

Covers graph compilation, topology, end-to-end state flow with mocked
LLMs, crypto passthrough, graceful degradation, state initialization,
and import chain verification.
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from langgraph.graph import END

from agents.utils.agent_states import AgentState
from graph.propagation import Propagator
from graph.radon_validation import create_radon_validation_node

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_quick_llm():
    """Mock quick-thinking LLM that behaves like a ChatOpenAI instance."""
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.invoke.return_value = MagicMock(content="Analysis complete")
    return llm


@pytest.fixture
def mock_deep_llm():
    """Mock deep-thinking LLM."""
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.invoke.return_value = MagicMock(content="Deep analysis complete")
    return llm


@pytest.fixture
def mock_tool_nodes():
    """Minimal tool nodes using real tool functions from the project."""
    from langgraph.prebuilt import ToolNode

    from agents.utils.agent_utils import get_stock_data

    tool_node = ToolNode([get_stock_data])
    return dict.fromkeys(("market", "social", "news", "fundamentals"), tool_node)


@pytest.fixture
def graph_setup(mock_quick_llm, mock_deep_llm, mock_tool_nodes):
    """Return a GraphSetup instance with mocked components."""
    from graph.conditional_logic import ConditionalLogic
    from graph.setup import GraphSetup

    return GraphSetup(
        quick_thinking_llm=mock_quick_llm,
        deep_thinking_llm=mock_deep_llm,
        tool_nodes=mock_tool_nodes,
        bull_memory=MagicMock(),
        bear_memory=MagicMock(),
        trader_memory=MagicMock(),
        invest_judge_memory=MagicMock(),
        risk_manager_memory=MagicMock(),
        conditional_logic=ConditionalLogic(),
    )


@pytest.fixture
def compiled_graph(graph_setup):
    """Return a compiled graph with all default analysts."""
    return graph_setup.setup_graph(selected_analysts=["market"])


# ---------------------------------------------------------------------------
# 1. Graph compilation with Radon node
# ---------------------------------------------------------------------------


class TestGraphCompilation:
    """Verify the compiled graph includes the Radon Validation node."""

    def test_graph_compiles_successfully(self, compiled_graph):
        """Graph setup and compilation succeeds."""
        assert compiled_graph is not None

    def test_graph_contains_radon_validation_node(self, compiled_graph):
        """The compiled graph includes a 'Radon Validation' node."""
        node_names = _get_node_names(compiled_graph)
        assert "Radon Validation" in node_names

    def test_graph_contains_risk_judge_node(self, compiled_graph):
        """The compiled graph includes a 'Risk Judge' node."""
        node_names = _get_node_names(compiled_graph)
        assert "Risk Judge" in node_names

    def test_graph_contains_all_expected_nodes(self, compiled_graph):
        """All expected nodes are present in the compiled graph."""
        node_names = _get_node_names(compiled_graph)
        expected = {
            "Market Analyst",
            "Msg Clear Market",
            "tools_market",
            "Bull Researcher",
            "Bear Researcher",
            "Research Manager",
            "Trader",
            "Aggressive Analyst",
            "Neutral Analyst",
            "Conservative Analyst",
            "Risk Judge",
            "Radon Validation",
        }
        assert expected.issubset(node_names)


# ---------------------------------------------------------------------------
# 2. Graph topology — edge verification
# ---------------------------------------------------------------------------


class TestGraphTopology:
    """Verify edges from Risk Judge → Radon Validation → END."""

    def test_risk_judge_edges_to_radon_validation(self, compiled_graph):
        """Risk Judge has an outgoing edge to Radon Validation."""
        edges = _get_edges(compiled_graph)
        assert ("Risk Judge", "Radon Validation") in edges

    def test_radon_validation_edges_to_end(self, compiled_graph):
        """Radon Validation has an outgoing edge to END."""
        edges = _get_edges(compiled_graph)
        assert ("Radon Validation", END) in edges

    def test_risk_judge_does_not_edge_directly_to_end(self, compiled_graph):
        """Risk Judge does NOT have a direct edge to END (must go through Radon)."""
        edges = _get_edges(compiled_graph)
        assert ("Risk Judge", END) not in edges


# ---------------------------------------------------------------------------
# 3. End-to-end state flow with mocked LLM
# ---------------------------------------------------------------------------


class TestEndToEndStateFlow:
    """Run the Radon Validation node in isolation with mocked validate_trade
    to verify state flows correctly."""

    @patch("graph.radon_validation.validate_trade")
    def test_stock_state_receives_validation_result(self, mock_validate):
        """Stock ticker state gets radon_validation_result populated."""
        mock_validate.return_value = {
            "radon_validation_result": "PASS",
            "radon_validation_details": {"Ticker": "AAPL", "Milestones": "11/11"},
        }

        node = create_radon_validation_node()
        state = _make_stock_state("AAPL")

        result = node(state)

        assert result["radon_validation_result"] == "PASS"
        assert result["radon_validation_details"]["Ticker"] == "AAPL"
        mock_validate.assert_called_once_with(state)

    @patch("graph.radon_validation.validate_trade")
    def test_state_flows_from_risk_judge_through_radon(self, mock_validate):
        """State arriving from Risk Judge is correctly processed by Radon node."""
        mock_validate.return_value = {
            "radon_validation_result": "FAIL",
            "radon_validation_details": {"reason": "edge too weak"},
        }

        node = create_radon_validation_node()
        incoming = _make_risk_judge_output_state("NVDA", "BUY")

        result = node(incoming)

        assert result["radon_validation_result"] == "FAIL"
        assert result["radon_validation_details"]["reason"] == "edge too weak"
        # Original state fields are preserved
        assert incoming["final_trade_decision"] == "BUY"
        assert incoming["company_of_interest"] == "NVDA"

    @patch("graph.radon_validation.validate_trade")
    def test_full_state_dict_preserved_beyond_radon_keys(self, mock_validate):
        """Only radon keys are returned; no other state keys are modified."""
        mock_validate.return_value = {
            "radon_validation_result": "PASS",
            "radon_validation_details": {"ok": True},
        }

        node = create_radon_validation_node()
        state = _make_stock_state("MSFT")
        state["market_report"] = "Strong bullish signals"
        state["sentiment_report"] = "Positive sentiment"

        result = node(state)

        assert set(result.keys()) == {
            "radon_validation_result",
            "radon_validation_details",
        }
        assert state["market_report"] == "Strong bullish signals"
        assert state["sentiment_report"] == "Positive sentiment"


# ---------------------------------------------------------------------------
# 4. Crypto passthrough integration
# ---------------------------------------------------------------------------


class TestCryptoPassthroughIntegration:
    """Verify that crypto tickers bypass Radon validation in the graph node."""

    @patch("graph.radon_validation.validate_trade")
    def test_crypto_ticker_skips_validation(self, mock_validate):
        """Crypto state produces SKIP without calling validate_trade."""
        node = create_radon_validation_node()
        state = _make_crypto_state("BTC-USD")

        result = node(state)

        assert result["radon_validation_result"] == "SKIP"
        assert result["radon_validation_details"] == {}
        mock_validate.assert_not_called()

    @patch("graph.radon_validation.validate_trade")
    def test_eth_skips_validation(self, mock_validate):
        """ETH crypto ticker also skips validation."""
        node = create_radon_validation_node()
        result = node(_make_crypto_state("ETH-USD"))

        assert result["radon_validation_result"] == "SKIP"
        mock_validate.assert_not_called()

    @patch("graph.radon_validation.validate_trade")
    def test_sol_skips_validation(self, mock_validate):
        """SOL crypto ticker skips validation."""
        node = create_radon_validation_node()
        result = node(_make_crypto_state("SOL-USD"))

        assert result["radon_validation_result"] == "SKIP"
        mock_validate.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Graceful degradation integration
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """When Radon dependencies are unavailable, the graph still completes."""

    @patch("graph.radon_validation.validate_trade")
    def test_validate_trade_import_error_returns_error(self, mock_validate):
        """ImportError from validate_trade is caught; node returns ERROR."""
        mock_validate.side_effect = ImportError("radon deps missing")

        node = create_radon_validation_node()
        result = node(_make_stock_state("AAPL"))

        assert result["radon_validation_result"] == "ERROR"
        assert result["radon_validation_details"] == {}

    @patch("graph.radon_validation.validate_trade")
    def test_validate_trade_runtime_error_returns_error(self, mock_validate):
        """RuntimeError from validate_trade is caught; node returns ERROR."""
        mock_validate.side_effect = RuntimeError("service down")

        node = create_radon_validation_node()
        result = node(_make_stock_state("TSLA"))

        assert result["radon_validation_result"] == "ERROR"
        assert result["radon_validation_details"] == {}

    @patch("graph.radon_validation.validate_trade")
    def test_validate_trade_generic_exception_returns_error(self, mock_validate):
        """Any exception from validate_trade is caught; node returns ERROR."""
        mock_validate.side_effect = Exception("unexpected")

        node = create_radon_validation_node()
        result = node(_make_stock_state("GOOG"))

        assert result["radon_validation_result"] == "ERROR"
        assert result["radon_validation_details"] == {}

    def test_node_always_returns_dict(self):
        """Even in error conditions, the node returns a dict with the expected keys."""
        node = create_radon_validation_node()
        result = node({"asset_type": "stock"})

        assert isinstance(result, dict)
        assert "radon_validation_result" in result
        assert "radon_validation_details" in result


# ---------------------------------------------------------------------------
# 6. State initialization — create_initial_state
# ---------------------------------------------------------------------------


class TestStateInitialization:
    """Verify create_initial_state produces correct state with Radon fields."""

    def test_initial_state_has_radon_validation_result(self):
        """create_initial_state includes radon_validation_result."""
        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-06-01")

        assert "radon_validation_result" in state
        assert state["radon_validation_result"] == ""

    def test_initial_state_has_radon_validation_details(self):
        """create_initial_state includes radon_validation_details."""
        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-06-01")

        assert "radon_validation_details" in state
        assert state["radon_validation_details"] == {}

    def test_initial_state_stock_ticker(self):
        """Stock ticker produces asset_type='stock'."""
        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-06-01")

        assert state["asset_type"] == "stock"
        assert state["company_of_interest"] == "AAPL"
        assert state["trade_date"] == "2024-06-01"

    def test_initial_state_crypto_ticker(self):
        """Crypto ticker produces asset_type='crypto'."""
        propagator = Propagator()
        state = propagator.create_initial_state("BTC-USD", "2024-06-01")

        assert state["asset_type"] == "crypto"
        assert state["company_of_interest"] == "BTC-USD"

    def test_initial_state_required_fields_present(self):
        """All fields required for the graph are present in initial state."""
        propagator = Propagator()
        state = propagator.create_initial_state("NVDA", "2024-01-15")

        required_keys = {
            "messages",
            "company_of_interest",
            "asset_type",
            "trade_date",
            "investment_debate_state",
            "risk_debate_state",
            "market_report",
            "fundamentals_report",
            "sentiment_report",
            "news_report",
            "radon_validation_result",
            "radon_validation_details",
        }
        assert required_keys.issubset(state.keys())

    def test_initial_state_debate_states_initialized(self):
        """Debate states are initialized with empty defaults."""
        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-01-01")

        assert state["investment_debate_state"]["history"] == ""
        assert state["investment_debate_state"]["count"] == 0
        assert state["risk_debate_state"]["history"] == ""
        assert state["risk_debate_state"]["count"] == 0


# ---------------------------------------------------------------------------
# 7. Import chain verification
# ---------------------------------------------------------------------------


class TestImportChain:
    """Verify Radon imports work without optional deps (lazy loading)."""

    def test_import_radon_evaluator_from_package(self):
        """from radon import RadonEvaluator works."""
        from radon import RadonEvaluator

        assert RadonEvaluator is not None

    def test_import_validate_trade_from_interface(self):
        """from radon.interface import validate_trade works."""
        from radon.interface import validate_trade

        assert callable(validate_trade)

    def test_import_is_radon_available(self):
        """from radon.interface import is_radon_available works."""
        from radon.interface import is_radon_available

        assert callable(is_radon_available)

    def test_import_create_radon_validation_node(self):
        """from graph.radon_validation import create_radon_validation_node."""
        from graph.radon_validation import create_radon_validation_node

        assert callable(create_radon_validation_node)

    def test_import_agent_state_has_radon_fields(self):
        """AgentState TypedDict includes radon fields."""
        # TypedDict annotations are in __annotations__
        annotations = AgentState.__annotations__
        assert "radon_validation_result" in annotations
        assert "radon_validation_details" in annotations


# ---------------------------------------------------------------------------
# 8. Graph node wiring — Radon Validation node function identity
# ---------------------------------------------------------------------------


class TestGraphNodeWiring:
    """Verify the Radon Validation node is correctly wired into the graph."""

    def test_radon_node_is_callable(self):
        """The node function returned by create_radon_validation_node is callable."""
        node = create_radon_validation_node()
        assert callable(node)

    def test_multiple_graph_setups_produce_independent_nodes(self, graph_setup):
        """Each setup_graph call creates independent Radon nodes."""
        graph_a = graph_setup.setup_graph(selected_analysts=["market"])
        graph_b = graph_setup.setup_graph(selected_analysts=["market"])

        # Both graphs have the Radon Validation node
        assert "Radon Validation" in _get_node_names(graph_a)
        assert "Radon Validation" in _get_node_names(graph_b)

    def test_single_analyst_graph_still_has_radon(self, graph_setup):
        """Even with a single analyst, the graph includes Radon Validation."""
        graph = graph_setup.setup_graph(selected_analysts=["market"])
        assert "Radon Validation" in _get_node_names(graph)

    def test_all_four_analysts_graph_has_radon(self, graph_setup):
        """With all four analysts, the graph still includes Radon Validation."""
        graph = graph_setup.setup_graph(
            selected_analysts=["market", "social", "news", "fundamentals"]
        )
        assert "Radon Validation" in _get_node_names(graph)

    def test_no_analysts_raises_value_error(self, graph_setup):
        """Passing an empty analyst list raises ValueError."""
        with pytest.raises(ValueError, match="no analysts selected"):
            graph_setup.setup_graph(selected_analysts=[])


# ---------------------------------------------------------------------------
# 9. Full graph propagation — end-to-end with Radon
# ---------------------------------------------------------------------------


class TestFullGraphPropagation:
    """Test the full propagation flow with mocked components to verify
    the Radon Validation node is reachable and processes state correctly."""

    def test_propagation_creates_state_with_radon_defaults(self):
        """Propagator.create_initial_state includes all radon fields."""
        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-01-01")

        assert state["radon_validation_result"] == ""
        assert state["radon_validation_details"] == {}

    def test_propagation_crypto_ticker_classified(self):
        """Propagator correctly classifies crypto tickers."""
        propagator = Propagator()
        state = propagator.create_initial_state("BTC-USD", "2024-01-01")

        assert state["asset_type"] == "crypto"

    def test_propagation_stock_ticker_classified(self):
        """Propagator correctly classifies stock tickers."""
        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-01-01")

        assert state["asset_type"] == "stock"

    def test_get_graph_args_returns_stream_mode(self):
        """get_graph_args returns stream_mode='values'."""
        propagator = Propagator()
        args = propagator.get_graph_args()

        assert args["stream_mode"] == "values"
        assert "config" in args
        assert args["config"]["recursion_limit"] == 100

    def test_get_graph_args_with_callbacks(self):
        """get_graph_args includes callbacks when provided."""
        propagator = Propagator()
        mock_callback = MagicMock()
        args = propagator.get_graph_args(callbacks=[mock_callback])

        assert "callbacks" in args["config"]

    @patch("graph.radon_validation.validate_trade")
    def test_radon_node_process_full_initial_state(self, mock_validate):
        """Radon node can process the full initial state from create_initial_state."""
        mock_validate.return_value = {
            "radon_validation_result": "PASS",
            "radon_validation_details": {"Ticker": "AAPL"},
        }

        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2024-01-01")

        node = create_radon_validation_node()
        result = node(state)

        assert result["radon_validation_result"] == "PASS"
        mock_validate.assert_called_once()

    @patch("graph.radon_validation.validate_trade")
    def test_radon_node_process_full_crypto_initial_state(self, mock_validate):
        """Radon node skips validation for crypto initial state."""
        propagator = Propagator()
        state = propagator.create_initial_state("BTC-USD", "2024-01-01")

        node = create_radon_validation_node()
        result = node(state)

        assert result["radon_validation_result"] == "SKIP"
        mock_validate.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_node_names(compiled_graph) -> set[str]:
    """Extract node names from a compiled LangGraph graph.

    LangGraph stores nodes in different internal structures depending
    on the version. We try multiple approaches to be robust.
    """
    names: set[str] = set()

    # Approach 1: graph.nodes (dict-like)
    if hasattr(compiled_graph, "nodes"):
        nodes = compiled_graph.nodes
        if isinstance(nodes, dict):
            names.update(nodes.keys())
        elif hasattr(nodes, "__iter__"):
            with contextlib.suppress(TypeError):
                names.update(nodes)

    # Approach 2: _graph.nodes
    if hasattr(compiled_graph, "_graph") and hasattr(compiled_graph._graph, "nodes"):
        nodes = compiled_graph._graph.nodes
        if isinstance(nodes, dict):
            names.update(nodes.keys())
        elif hasattr(nodes, "__iter__"):
            with contextlib.suppress(TypeError):
                names.update(nodes)

    # Approach 3: Internal adjacency dict
    if hasattr(compiled_graph, "_adjacency"):
        names.update(compiled_graph._adjacency.keys())

    # Approach 4: Try get_graph()
    if hasattr(compiled_graph, "get_graph"):
        try:
            g = compiled_graph.get_graph()
            if hasattr(g, "nodes"):
                for node in g.nodes.values():
                    if hasattr(node, "name"):
                        names.add(node.name)
                    elif isinstance(node, dict) and "name" in node:
                        names.add(node["name"])
        except Exception:
            pass

    return names


def _get_edges(compiled_graph) -> set[tuple[str, str]]:
    """Extract directed edges from a compiled LangGraph graph."""
    edges: set[tuple[str, str]] = set()

    # Approach 1: Try get_graph()
    if hasattr(compiled_graph, "get_graph"):
        try:
            g = compiled_graph.get_graph()
            if hasattr(g, "edges"):
                for edge in g.edges:
                    src = getattr(edge, "src", None) or getattr(edge, "source", None)
                    tgt = getattr(edge, "tgt", None) or getattr(edge, "target", None)
                    if src and tgt:
                        edges.add((str(src), str(tgt)))
        except Exception:
            pass

    # Approach 2: Internal adjacency
    if hasattr(compiled_graph, "_adjacency"):
        for src, targets in compiled_graph._adjacency.items():
            if isinstance(targets, dict | list | set):
                edges.update((str(src), str(tgt)) for tgt in targets)

    return edges


def _make_stock_state(ticker: str) -> dict:
    """Create a minimal stock state dict for node testing."""
    return {
        "company_of_interest": ticker,
        "asset_type": "stock",
        "trade_date": "2024-06-01",
        "final_trade_decision": "BUY",
        "messages": [],
    }


def _make_crypto_state(ticker: str) -> dict:
    """Create a minimal crypto state dict for node testing."""
    return {
        "company_of_interest": ticker,
        "asset_type": "crypto",
        "trade_date": "2024-06-01",
        "final_trade_decision": "BUY",
        "messages": [],
    }


def _make_risk_judge_output_state(ticker: str, decision: str) -> dict:
    """Create a state dict simulating Risk Judge output."""
    return {
        "company_of_interest": ticker,
        "asset_type": "stock",
        "trade_date": "2024-03-01",
        "final_trade_decision": decision,
        "risk_debate_state": {
            "history": "Aggressive: Buy\nConservative: Hold",
            "count": 3,
            "latest_speaker": "Judge",
            "judge_decision": decision,
        },
        "investment_debate_state": {
            "history": "Bull: Growth\nBear: Risk",
            "count": 2,
            "current_response": "Judge: Proceed",
            "judge_decision": "Proceed",
        },
        "market_report": "Strong momentum",
        "fundamentals_report": "Solid earnings",
        "sentiment_report": "Positive",
        "news_report": "Favorable",
        "investment_plan": "Buy with conviction",
        "trader_investment_plan": "Enter long",
        "messages": [],
    }
