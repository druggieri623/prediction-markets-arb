import json
from pathlib import Path

from src.pm_arb import storage


def test_save_load_and_remove(tmp_path):
    p = tmp_path / "sub" / "data.json"
    data = {"x": 1, "y": [1, 2, 3]}

    # save
    storage.save_json(p, data)
    assert storage.exists(p)

    # load
    loaded = storage.load_json(p)
    assert loaded == data

    # remove
    storage.remove(p)
    assert not storage.exists(p)

    # default on missing
    assert storage.load_json(p, default={"ok": True}) == {"ok": True}
