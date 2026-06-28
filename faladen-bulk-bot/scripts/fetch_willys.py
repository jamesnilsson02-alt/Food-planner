"""
fetch_willys.py
Hämtar veckans extrapriser från Willys (Axfood API).
"""

import requests

WILLYS_API_URL = "https://www.willys.se/axfood/rest/v1/search/campaigns/offline"

NON_FOOD_KEYWORDS = [
    "schampo", "balsam", "rakblad", "deodorant", "tandkräm",
    "blöja", "toalettpapper", "hushållspapper", "servett", "rengöring",
    "diskmedel", "tvättmedel", "sköljmedel", "fläckborttagning",
    "snus", "tobak", "rosor", "blombukett", "orkidé",
]


def fetch_offers(location_id: str) -> list[dict]:
    try:
        params = {"q": "2176", "type": "PERSONAL_GENERAL", "page": 0, "size": 100}
        headers = {"Accept": "application/json", "User-Agent": "FaladenBulkBot/1.0"}
        resp = requests.get(WILLYS_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data.get("content", []))
    except Exception as e:
        print(f"[Willys] Fel vid hämtning: {e}")
        return []


def filter_and_normalize(raw_offers: list[dict]) -> list[dict]:
    result = []
    for item in raw_offers:
        name = (item.get("name") or item.get("title") or "").lower()
        description = (item.get("description") or item.get("subtitle") or "").lower()
        combined = f"{name} {description}"

        if any(kw in combined for kw in NON_FOOD_KEYWORDS):
            continue

        price = (
            item.get("price")
            or item.get("priceValue")
            or item.get("currentPrice", {}).get("price")
        )

        result.append({
            "store": "willys",
            "name": item.get("name") or item.get("title") or "Okänt",
            "price_sek": price,
            "compare_price": item.get("comparePriceText") or item.get("comparePrice") or "",
            "origin": item.get("country") or item.get("origin") or "",
            "savings_text": item.get("savingsText") or item.get("promotionSavingsText") or "",
        })

    return result


def get_willys_offers(location_id: str) -> list[dict]:
    raw = fetch_offers(location_id)
    filtered = filter_and_normalize(raw)
    print(f"[Willys] {len(raw)} råa erbjudanden → {len(filtered)} efter filtrering")
    return filtered
