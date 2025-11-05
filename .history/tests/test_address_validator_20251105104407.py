import requests
import pytest
from app.services.address_validator import validate_address_nominatim

def _make_resp(json_data, status_code=200):
    class Resp:
        def __init__(self, data, status):
            self._data = data
            self.status_code = status
        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.RequestException(f"HTTP {self.status_code}")
        def json(self):
            return self._data
    return Resp(json_data, status_code)

def test_validate_address_success_strict(monkeypatch):
    sample = [{
        "display_name": "10 Rue de Test, 75001 Paris, France",
        "lat": "48.8566",
        "lon": "2.3522",
        "address": {"road": "Rue de Test", "city": "Paris", "postcode": "75001"}
    }]
    called = {}
    def fake_get(url, params=None, headers=None, timeout=None):
        called['url'] = url
        called['params'] = params
        called['headers'] = headers
        called['timeout'] = timeout
        return _make_resp(sample, 200)

    monkeypatch.setattr("requests.get", fake_get)
    out = validate_address_nominatim("10 rue de test, paris", countrycodes="fr", strict=True)
    assert out is not None
    assert out["display_name"] == sample[0]["display_name"]
    assert out["lat"] == sample[0]["lat"]
    assert out["lon"] == sample[0]["lon"]
    assert "address" in out and out["address"]["city"] == "Paris"
    # verify params and headers forwarded
    assert called["params"]["q"].lower().startswith("10 rue")
    assert called["params"]["countrycodes"] == "fr"
    assert "User-Agent" in called["headers"]
    assert called["timeout"] == 6

def test_validate_address_no_results(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _make_resp([], 200)
    monkeypatch.setattr("requests.get", fake_get)
    assert validate_address_nominatim("address that matches nothing") is None

def test_validate_address_network_error(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        raise requests.RequestException("network down")
    monkeypatch.setattr("requests.get", fake_get)
    assert validate_address_nominatim("any address") is None

def test_validate_address_strict_vs_non_strict(monkeypatch):
    # result has city but no postcode
    sample = [{
        "display_name": "Some Town",
        "lat": "1.0",
        "lon": "2.0",
        "address": {"city": "Smallville"}
    }]
    def fake_get(url, params=None, headers=None, timeout=None):
        return _make_resp(sample, 200)
    monkeypatch.setattr("requests.get", fake_get)

    # strict True -> requires postcode -> should return None
    assert validate_address_nominatim("smallville", strict=True) is None
    # strict False -> accepts city only -> should return data
    out = validate_address_nominatim("smallville", strict=False)
    assert out is not None
    assert out["address"]["city"] == "Smallville"

def test_validate_address_empty_input():
    assert validate_address_nominatim("") is None
    assert validate_address_nominatim("   ") is None

def test_validate_address_http_error(monkeypatch):
    # server returns 500 -> raise_for_status -> function returns None
    def fake_get(url, params=None, headers=None, timeout=None):
        return _make_resp({"error": "oops"}, 500)
    monkeypatch.setattr("requests.get", fake_get)
    assert validate_address_nominatim("some address") is None