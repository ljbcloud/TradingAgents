import pytest

from tradingagents.agents.utils.memory import FinancialSituationMemory


def test_memory_initialization():
    memory = FinancialSituationMemory("test_memory", {})
    assert memory.name == "test_memory"
    assert memory.bm25 is None


def test_memory_initialization_with_situations():
    memory = FinancialSituationMemory("test_memory", {})
    memory.add_situations([("test situation", "test advice")])
    assert memory.bm25 is not None


def test_tokenize_simple_text():
    memory = FinancialSituationMemory("test", {})
    tokens = memory._tokenize("The market is up")
    assert "market" in tokens
    assert "up" in tokens


def test_tokenize_removes_special_chars():
    memory = FinancialSituationMemory("test", {})
    tokens = memory._tokenize("Market's UP! $AAPL")
    assert "$" not in tokens
    assert "!" not in tokens
    assert "market" in tokens
    assert "aapl" in tokens


def test_add_situations_single():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("market crash", "buy gold")])
    assert memory.bm25 is not None


def test_add_situations_multiple():
    memory = FinancialSituationMemory("test", {})
    situations = [
        ("market crash", "buy gold"),
        ("high inflation", "buy real estate"),
        ("recession", "hold cash"),
    ]
    memory.add_situations(situations)
    assert memory.bm25 is not None


def test_add_situations_empty_list():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([])
    assert memory.bm25 is None


def test_get_memories_single_match():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("market crash today", "buy gold")])
    results = memory.get_memories("market crashed", n_matches=1)
    assert len(results) == 1
    assert results[0]["recommendation"] == "buy gold"
    assert "similarity_score" in results[0]


def test_get_memories_multiple_matches():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([
        ("market crash", "buy gold"),
        ("market up", "buy stocks"),
        ("market down", "buy bonds"),
    ])
    results = memory.get_memories("market", n_matches=2)
    assert len(results) == 2


def test_get_memories_no_match():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("weather sunny", "go outside")])
    results = memory.get_memories("market analysis")
    assert len(results) == 1
    assert results[0]["similarity_score"] <= 0


def test_get_memories_empty_memory():
    memory = FinancialSituationMemory("test", {})
    results = memory.get_memories("any query")
    assert len(results) == 0


def test_rebuild_index_empty():
    memory = FinancialSituationMemory("test", {})
    memory._rebuild_index()
    assert memory.bm25 is None


def test_rebuild_index_after_add():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("test situation", "test advice")])
    assert memory.bm25 is not None


def test_clear_memory():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("test", "advice")])
    memory.clear()
    assert memory.bm25 is None


def test_tokenize_empty_string():
    memory = FinancialSituationMemory("test", {})
    tokens = memory._tokenize("")
    assert tokens == []


def test_get_memories_returns_correct_structure():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("market crash", "buy gold")])
    results = memory.get_memories("market")
    assert all(
        key in results[0]
        for key in ["matched_situation", "recommendation", "similarity_score"]
    )


def test_add_situations_rebuilds_index():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([("situation1", "advice1")])
    assert memory.bm25 is not None


def test_get_memories_respects_n_matches():
    memory = FinancialSituationMemory("test", {})
    memory.add_situations([
        ("market crash", "buy gold"),
        ("market up", "buy stocks"),
        ("market down", "buy bonds"),
    ])
    results = memory.get_memories("market", n_matches=1)
    assert len(results) == 1
