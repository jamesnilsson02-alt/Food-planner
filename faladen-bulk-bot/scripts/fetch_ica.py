"""
fetch_ica.py
Hämtar veckans extrapriser från ICA och returnerar en filtrerad lista.
"""

import requests

ICA_OFFERS_URL = "https://www.ica.se/api/store/v2/stores/{store_id}/offers"

BLACKLIST_KEYWORDS = [
    "schampo", "balsam", "tvål", "tvätt", "diskmedel", "blöja", "servett",
    "toalett", "hushålls", "rengöring", "tandkräm", "rakblad", "deodorant",
    "snus", "tobak", "öl", "vin", "sprit", "cider", "energidryck",
    "godis", "chips", "snacks", "kex", "choklad", "glass", "sockerkaka",
    "juice", "läsk", "nektar", "smoothie",
]

FOOD_WHITELIST_KEYWORDS = [
    "kyckling", "kycklingfilé", "kycklinglår", "kycklingbröst",
    "nöt", "nötfärs", "nötkött", "biff", "entrecôte",
    "fläsk", "fläskfilé", "fläskkarré", "fläskfärs",
    "lax", "torsk", "fisk", "räkor", "tonfisk",
    "ägg", "kvarg", "kesella", "skyr", "cottage",
    "mjölk", "fil", "yoghurt", "ost", "proteinpulver",
    "bönor", "linser", "kikärtor", "tofu", "tempeh",
    "ris", "pasta", "havre", "havregryn", "potatis", "sötpotatis",
    "bröd", "knäcke",
    "broccoli", "spenat", "blomkål", "kål", "tomat", "lök", "vitlök",
    "banan", "äpple", "apelsin",
    "olivolja", "rapsolja", "smör",
]


def fetch_offers(store_id: str) -> list[dict]:
    """Anropar ICA:s butiks-API och returnerar råa erbjudanden."""
    try:
        url = ICA_OFFERS_URL.format(store_id=store_id)
        headers = {
            "Accept": "application/json",
            "User-Agent": "FaladenBulkBot/1.0",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("offers", data.get("Offers", []))
    except Exception as e:
        print(f"[ICA] Fel vid hämtning: {e}")
        return []


def filter_offers(raw_offers: list[dict]) -> list[dict]:
    """Rensar och komprimerar ICA-erbjudanden."""
    filtered = []
    for item in raw_offers:
        name = (item.get("Name") or item.get("name") or "").lower()
        description = (item.get("Description") or item.get("description") or "").lower()
        combined = f"{name} {description}"

        if any(kw in combined for kw in BLACKLIST_KEYWORDS):
            continue
        if not any(kw in combined for kw in FOOD_WHITELIST_KEYWORDS):
            continue

        # ICA använder ofta camelCase
        price = (
            item.get("OfferPrice")
            or item.get("offerPrice")
            or item.get("Price")
            or item.get("price")
        )
        compare_price = item.get("ComparePrice") or item.get("comparePrice")
        origin = item.get("CountryOfOrigin") or item.get("country") or ""

        filtered.append({
            "store": "ica",
            "name": item.get("Name") or item.get("name") or "Okänt",
            "price_sek": price,
            "compare_price": compare_price,
            "origin": origin,
            "savings_text": item.get("SavingsText") or item.get("savingsText") or "",
        })

    return filtered


def get_ica_offers(store_id: str) -> list[dict]:
    """Huvudfunktion – anropar API och returnerar filtrerade erbjudanden."""
    raw = fetch_offers(store_id)
    filtered = filter_offers(raw)
    print(f"[ICA] {len(raw)} råa erbjudanden → {len(filtered)} efter filtrering")
    return filtered
