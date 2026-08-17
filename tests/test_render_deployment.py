from pathlib import Path

from src.agents.checkpoint import _checkpoint_pool_size


ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_is_free_and_contains_no_secret_values():
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "plan: free" in blueprint
    assert "runtime: docker" in blueprint
    assert "healthCheckPath: /health" in blueprint
    assert "FINANCE_ENVIRONMENT\n        value: production" in blueprint
    assert blueprint.count("sync: false") == 4
    assert "postgresql://" not in blueprint
    assert "rediss://" not in blueprint
    assert "replace-with" not in blueprint


def test_checkpoint_pool_can_release_every_idle_connection(monkeypatch):
    monkeypatch.setenv("FINANCE_CHECKPOINT_POOL_MIN_SIZE", "0")

    assert _checkpoint_pool_size(
        "FINANCE_CHECKPOINT_POOL_MIN_SIZE", 1, minimum=0
    ) == 0
