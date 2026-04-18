from __future__ import annotations

from api.services.storage import FilesystemResultStorage


async def test_save_and_load_roundtrip(tmp_results_dir):
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    data = {"decision": "BUY", "confidence": 0.9}
    await storage.save("job-1", data)

    loaded = await storage.load("job-1")
    assert loaded == data


async def test_load_nonexistent_returns_none(tmp_results_dir):
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    result = await storage.load("no-such-job")
    assert result is None


async def test_exists_true_after_save(tmp_results_dir):
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    await storage.save("job-2", {"result": True})
    assert await storage.exists("job-2") is True


async def test_exists_false_for_missing(tmp_results_dir):
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    assert await storage.exists("ghost") is False


async def test_delete_removes_file(tmp_results_dir):
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    await storage.save("job-3", {"temp": True})
    assert await storage.exists("job-3") is True

    await storage.delete("job-3")
    assert await storage.exists("job-3") is False
    assert await storage.load("job-3") is None
