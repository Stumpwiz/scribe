# tests/test_ingestor_smoke.py
import sys
import types


def test_main_invokes_ingestion(monkeypatch):
    # Stub the async ingestion function
    async def fake_monitor_and_ingest_email_reports(context, agent, task):
        return {"ok": True, "called": True}

    # Stub the loader to return a minimal task-like object
    FakeTask = types.SimpleNamespace

    def fake_load_task_from_yaml(name: str):
        assert name == "monitor_and_ingest_email_reports"
        return FakeTask(agent=None)

    # Build fake modules to avoid importing real code with side effects
    fake_tasks_mod = types.ModuleType("src.scribe.config.tasks")
    setattr(fake_tasks_mod, "monitor_and_ingest_email_reports", fake_monitor_and_ingest_email_reports)

    fake_loader_mod = types.ModuleType("src.scribe.config.loader")
    setattr(fake_loader_mod, "load_task_from_yaml", fake_load_task_from_yaml)

    # Ensure parent packages exist in sys.modules for import resolution
    sys.modules.setdefault("src", types.ModuleType("src"))
    sys.modules.setdefault("src.scribe", types.ModuleType("src.scribe"))
    sys.modules.setdefault("src.scribe.config", types.ModuleType("src.scribe.config"))

    # Install our fakes
    sys.modules["src.scribe.config.tasks"] = fake_tasks_mod
    sys.modules["src.scribe.config.loader"] = fake_loader_mod

    # Import the runner and execute its main
    from scripts import run_ingestor

    run_ingestor.main()
