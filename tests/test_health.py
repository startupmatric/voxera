import urllib.request
import json


BASE = \"http://localhost:8000\"


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return r.status, json.loads(r.read())


def test_health():
    status, body = _get(\"/health\")
    assert status == 200
    assert body == {\"status\": \"ok\", \"service\": \"voxera\"}
