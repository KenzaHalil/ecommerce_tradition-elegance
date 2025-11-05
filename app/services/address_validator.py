import requests
from typing import Optional, Dict

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

def validate_address_nominatim(raw_address: str, countrycodes: Optional[str] = None, strict: bool = True) -> Optional[Dict]:
    """
    Valide et normalise une adresse via Nominatim (OpenStreetMap).
    Retourne un dict avec display_name, lat, lon, address si OK, sinon None.
    - strict=True : exige au moins ville et code postal.
    Remarque: respecter les règles d'usage Nominatim (User-Agent, rate limit).
    """
    if not raw_address or not raw_address.strip():
        return None

    params = {
        "q": raw_address,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 3,
    }
    if countrycodes:
        params["countrycodes"] = countrycodes  # ex: "fr"

    headers = {
        # Remplace contact@example.com par ton email ou info de contact
        "User-Agent": "Tradition-Elegance/1.0 (contact@example.com)"
    }

    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=6)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None

        best = data[0]
        addr = best.get("address", {})

        has_street = any(k in addr for k in ("road", "house_number", "pedestrian"))
        has_city = any(k in addr for k in ("city", "town", "village", "municipality"))
        has_postcode = "postcode" in addr

        if strict:
            if not (has_city and has_postcode):
                return None

        return {
            "display_name": best.get("display_name"),
            "lat": best.get("lat"),
            "lon": best.get("lon"),
            "address": addr
        }
    except requests.RequestException:
        # En cas d'erreur réseau, renvoyer None (inscription bloquée) ou adapter pour soft-fallback.
        return None