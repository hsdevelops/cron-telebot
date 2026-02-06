from types import SimpleNamespace

import pytest

import main


@pytest.mark.asyncio
async def test_process_update_calls_ptb(monkeypatch):
    called = {"processed": False}

    class DummyPTB:
        def __init__(self):
            self.bot = object()

        async def process_update(self, update):
            called["processed"] = True

    async def fake_json():
        return {"update_id": 1}

    async def fake_de_json(payload, bot):
        return payload

    monkeypatch.setattr(main.Update, "de_json", fake_de_json)

    dummy_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(ptb=DummyPTB())),
        json=fake_json,
    )

    res = await main.process_update(dummy_request)
    assert res.status_code == 200
    assert called["processed"] is True
