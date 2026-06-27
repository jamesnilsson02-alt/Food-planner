"""
fetch_willys.py
Hämtar veckans extrapriser från Willys (Axfood) och returnerar en filtrerad lista.
"""

import requests

WILLYS_API_URL = "https://www.willys.se/offers/offline"

# Ord som direkt diskvalificerar en vara – filtreras bort lokalt för att spara tokens
BLACKLIST_KEYWORDS = [
    "schampo", "balsam", "tvål", "tvätt", "diskmedel", "blöja", "servett",
    "toalett", "hushålls", "rengöring", "tandkräm", "rakblad", "deodorant",
    "snus", "tobak", "öl", "vin", "sprit", "cider", "energidryck",
    "godis", "chips", "snacks", "kex", "choklad", "glass", "sockerkaka",
    "juice", "läsk", "nektar", "smoothie",
]

# Ord som starkt indikerar mat vi faktiskt vill ha
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


def fetch_offers(location_id: str) -> list[dict]:
    """Anropar Willys API och returnerar råa erbjudanden."""
    try:
        params = {"location": location_id, "channel": "WEB"}
        headers = {"Accept": "application/json", "User-Agent": "FaladenBulkBot/1.0"}
        resp = requests.get(WILLYS_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Axfood API returnerar offers i olika strukturer – försök båda
        return data.get("results", data.get("offers", []))
    except Exception as e:
        print(f"[Willys] Fel vid hämtning: {e}")
        return []


def filter_offers(raw_offers: list[dict]) -> list[dict]:
    """
    Rensar bort icke-matvaror och onödigt innehåll.
    Returnerar en kompakt lista med bara relevanta fält.
    """
    filtered = []
    for item in raw_offers:
        name = (item.get("name") or item.get("title") or "").lower()
        description = (item.get("description") or item.get("subtitle") or "").lower()
        combined = f"{name} {description}"

        # Steg 1: uteslut svartlistade kategorier
        if any(kw in combined for kw in BLACKLIST_KEYWORDS):
            continue

        # Steg 2: ta med om det matchar whitelist, annars skippa
        if not any(kw in combined for kw in FOOD_WHITELIST_KEYWORDS):
            continue

        # Steg 3: extrahera pris
        price = (
            item.get("price")
            or item.get("priceValue")
            or item.get("currentPrice", {}).get("price")
        )
        compare_price = item.get("comparePriceText") or item.get("comparePrice")
        origin = item.get("country") or item.get("origin") or ""

        filtered.append({
            "store": "willys",
            "name": item.get("name") or item.get("title") or "Okänt",
            "price_sek": price,
            "compare_price": compare_price,
            "origin": origin,
            "savings_text": item.get("savingsText") or item.get("promotionSavingsText") or "",
        })

    return filtered


def get_willys_offers(location_id: str) -> list[dict]:
    """Huvudfunktion – anropar API och returnerar filtrerade erbjudanden."""
    raw = fetch_offers(location_id)
    filtered = filter_offers(raw)
    print(f"[Willys] {len(raw)} råa erbjudanden → {len(filtered)} efter filtrering")
    return filtered
