"""
fetch_ica.py
Hämtar veckans erbjudanden från ICA genom att skrapa butiksidan och
extrahera window.__INITIAL_DATA__ som är inbakat i HTML:en.
"""

import re
import json
import requests

ICA_STORE_URL = "https://www.ica.se/erbjudanden/ica-supermarket-faladstorget-1004223/"

# Bara uppenbart icke-matrelaterade kategorier – Claude hanterar resten
NON_FOOD_KEYWORDS = [
    "schampo", "balsam", "rakblad", "deodorant", "tandkräm",
    "blöja", "toalettpapper", "hushållspapper", "servett", "rengöring",
    "diskmedel", "tvättmedel", "sköljmedel", "fläckborttagning",
    "snus", "tobak", "rosor", "blombukett", "orkidé", "krukväxt",
    "kolsyrepåfyllning", "batterier",
]


def fetch_page(store_url: str) -> str:
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "sv-SE,sv;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    resp = requests.get(store_url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def extract_offers_from_html(html: str) -> list[dict]:
    match = re.search(r"window\.__INITIAL_DATA__\s*=\s*(\{.+?\});\s*</script>", html, re.DOTALL)
    if not match:
        print("[ICA] Hittade inte __INITIAL_DATA__ i HTML")
        return []
    data = json.loads(match.group(1))
    return data.get("offers", {}).get("weeklyOffers", [])


def filter_and_normalize(raw_offers: list[dict]) -> list[dict]:
    result = []
    for item in raw_offers:
        details = item.get("details", {})
        name = (details.get("name") or "").lower()
        brand = (details.get("brand") or "").lower()
        combined = f"{name} {brand}"

        if any(kw in combined for kw in NON_FOOD_KEYWORDS):
            continue

        mechanics = item.get("parsedMechanics", {})
        price_parts = (
            mechanics.get("value1", "")
            + mechanics.get("value2", "")
            + mechanics.get("unitSign", "")
            + mechanics.get("value4", "")
        )
        stores = item.get("stores", [{}])
        regular_price = stores[0].get("regularPrice") if stores else None

        result.append({
            "store": "ica",
            "name": details.get("name") or "Okänt",
            "brand": details.get("brand") or "",
            "package": details.get("packageInformation") or "",
            "price_text": price_parts,
            "regular_price": regular_price,
            "compare_price": item.get("comparisonPrice") or "",
        })

    return result


def get_ica_offers(store_url: str = ICA_STORE_URL) -> list[dict]:
    try:
        html = fetch_page(store_url)
        raw = extract_offers_from_html(html)
        filtered = filter_and_normalize(raw)
        print(f"[ICA] {len(raw)} råa erbjudanden → {len(filtered)} efter filtrering")
        return filtered
    except Exception as e:
        print(f"[ICA] Fel: {e}")
        return []


if __name__ == "__main__":
    offers = get_ica_offers()
    for o in offers:
        print(f"  {o['name']} ({o['brand']}) {o['package']} – {o['price_text']}")
