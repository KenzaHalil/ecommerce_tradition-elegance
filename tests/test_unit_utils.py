import pytest
from app.utils import luhn_valid
from app.routes import order_routes

def test_luhn_valid_known_good_numbers():
    # exemples valides (tests courants)
    assert luhn_valid("4242424242424242") is True   # Visa test
    assert luhn_valid("378282246310005") is True    # Amex test
    assert luhn_valid("4012888888881881") is True   # Visa

def test_luhn_invalid_examples():
    assert luhn_valid("4256987125475685") is False  # numéro fourni par l'utilisateur
    assert luhn_valid("0000 0000 0000 0000") is False
    assert luhn_valid("123456789") is False

def test_gen_tracking_format_and_uniqueness():
    gen = order_routes.gen_tracking_number
    seen = set()
    for _ in range(200):
        tn = gen()
        # format attendu : commence par TRK et longueur raisonnable
        assert tn.startswith("TRK")
        assert 10 <= len(tn) <= 20
        assert tn not in seen
        seen.add(tn)