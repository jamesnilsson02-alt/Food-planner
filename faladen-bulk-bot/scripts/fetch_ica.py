"""
fetch_ica.py
Hämtar veckans extrapriser från ICA genom att skrapa butiksidan och
extrahera window.__INITIAL_DATA__ som är inbakat i HTML:en.
"""

import re
import json
import requests

# Butikssida – accountNumber i URL:en (inte bmsId)
ICA_STORE_URL = "https://www.ica.se/erbjudanden/ica-supermarket-faladstorget-1004223/"

BLACKLIST_KEYWORDS = [
    "schampo", "balsam", "tvål", "tvätt", "diskmedel", "blöja", "servett",
    "toalett", "hushållspapper", "hushållsrulle", "rengöring", "tandkräm", "rakblad", "deodorant",
    "snus", "tobak", "öl", "vin", "sprit", "cider", "energidryck",
    "godis", "chips", "snacks", "kex", "choklad", "glass", "sockerkaka",
    "juice", "läsk", "nektar", "smoothie", "rosor", "blombukett", "orkidé",
]

FOOD_WHITELIST_KEYWORDS = [
    "kyckling", "kycklingfilé", "kycklinglår", "kycklingbröst", "kycklingköttbullar",
    "nöt", "nötfärs", "nötkött", "biff", "entrecôte",
    "fläsk", "fläskfilé", "fläskkarré", "fläskfärs", "fläskytterfilé", "flintastek",
    "lax", "torsk", "fisk", "räkor", "tonfisk", "kaviar",
    "ägg", "kvarg", "kesella", "skyr", "cottage",
    "mjölk", "fil", "yoghurt", "ost", "grädde",
    "bönor", "linser", "kikärtor", "tofu", "tempeh",
    "ris", "pasta", "makaroner", "spaghetti", "havre", "havregryn",
    "potatis", "sötpotatis", "potatisgratäng",
    "bröd", "knäcke", "limpa",
    "broccoli", "spenat", "blomkål", "kål", "tomat", "lök", "vitlök",
    "paprika", "zucchini", "aubergine",
    "banan", "äpple", "apelsin", "körsbär", "melon", "blåbär",
    "olivolja", "rapsolja", "smör", "margarin",
    "bacon", "skinka", "korv", "falukorv", "kebab", "köttbullar",
    "ribs", "kamben",
]


def fetch_page(store_url: str) -> str:
    """Hämtar HTML från ICA:s butiksida."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "sv-SE,sv;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    resp = requests.get(store_url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def extract_offers_from_html(html: str) -> list[dict]:
    """Plockar ut weeklyOffers från window.__INITIAL_DATA__ i HTML:en."""
    match = re.search(r"window\.__INITIAL_DATA__\s*=\s*(\{.+?\});\s*</script>", html, re.DOTALL)
    if not match:
        print("[ICA] Hittade inte __INITIAL_DATA__ i HTML")
        return []
    data = json.loads(match.group(1))
    return data.get("offers", {}).get("weeklyOffers", [])


def filter_offers(raw_offers: list[dict]) -> list[dict]:
    """Rensar och normaliserar ICA-erbjudanden till samma format som Willys."""
    filtered = []
    for item in raw_offers:
        details = item.get("details", {})
        name = (details.get("name") or "").lower()
        brand = (details.get("brand") or "").lower()
        combined = f"{name} {brand}"

        if any(kw in combined for kw in BLACKLIST_KEYWORDS):
            continue
        if not any(kw in combined for kw in FOOD_WHITELIST_KEYWORDS):
            continue

        mechanics = item.get("parsedMechanics", {})
        price_raw = mechanics.get("value2", "")
        price = float(price_raw) if price_raw else None

        stores = item.get("stores", [{}])
        regular_price = stores[0].get("regularPrice") if stores else None

        filtered.append({
            "store": "ica",
            "name": details.get("name") or "Okänt",
            "brand": details.get("brand") or "",
            "package": details.get("packageInformation") or "",
            "price_sek": price,
            "price_text": mechanics.get("value1", "") + mechanics.get("value2", "") + mechanics.get("unitSign", "") + mechanics.get("value4", ""),
            "regular_price": regular_price,
            "compare_price": item.get("comparisonPrice") or "",
            "savings_text": "",
        })

    return filtered


def get_ica_offers(store_url: str = ICA_STORE_URL) -> list[dict]:
    """Huvudfunktion – skrapar sidan och returnerar filtrerade erbjudanden."""
    try:
        html = fetch_page(store_url)
        raw = extract_offers_from_html(html)
        filtered = filter_offers(raw)
        print(f"[ICA] {len(raw)} råa erbjudanden → {len(filtered)} efter filtrering")
        return filtered
    except Exception as e:
        print(f"[ICA] Fel: {e}")
        return []


if __name__ == "__main__":
    offers = get_ica_offers()
    for o in offers:
        print(f"  {o['name']} ({o['brand']}) {o['package']} – {o['price_text']}")
