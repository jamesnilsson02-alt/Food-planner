"""
generate_menu.py
Huvudscript: hämtar extrapriser, anropar Claude API, sparar current_menu.json,
skickar Discord-notis.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

import anthropic
import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "stores_config.json"
PREFS_PATH = ROOT / "config" / "user_preferences.md"
OUTPUT_PATH = ROOT / "docs" / "current_menu.json"

# ── Ladda config ───────────────────────────────────────────────────────────────
with open(CONFIG_PATH) as f:
    config = json.load(f)

stores = config["stores"]
SPLIT_THRESHOLD = config["split_threshold_sek"]

with open(PREFS_PATH) as f:
    user_prefs = f.read()

# ── Importera fetch-moduler (bara om butiken är aktiverad) ──────────────────
sys.path.insert(0, str(ROOT / "scripts"))

active_offers: list[dict] = []

if stores["willys"]["enabled"]:
    from fetch_willys import get_willys_offers
    willys_offers = get_willys_offers(stores["willys"]["location_id"])
    active_offers.extend(willys_offers)

if stores["ica"]["enabled"]:
    from fetch_ica import get_ica_offers
    ica_offers = get_ica_offers(stores["ica"].get("store_url"))
    active_offers.extend(ica_offers)

if not active_offers:
    print("Inga erbjudanden hittades. Avbryter.")
    sys.exit(1)

print(f"Totalt {len(active_offers)} filtrerade erbjudanden skickas till Claude.")

# ── Bygg Claude-prompt ─────────────────────────────────────────────────────────
active_store_names = {
    key: val["name"]
    for key, val in stores.items()
    if val["enabled"]
}

offers_json = json.dumps(active_offers, ensure_ascii=False)

system_prompt = f"""Du är en erfaren kostrådgivare och kock specialiserad på budgetvänlig bulkkost för styrketräning.

Användarprofil:
{user_prefs}

Aktiva butiker denna vecka:
{json.dumps(active_store_names, ensure_ascii=False)}

Regel för delad butikstur: Dela BARA upp inköpen på två butiker om den totala besparingen
på den sekundära butiken överstiger {SPLIT_THRESHOLD} SEK. Annars: välj EN huvudbutik.

VIKTIGA REGLER FÖR RECEPT:
- Basera recepten på beprövade recept – som om de hämtats från en matblogg eller receptsajt. Kombinationerna ska kännas genomtänkta och smakliga, inte slumpmässiga.
- Varje rätt ska vara aptitlig, mättande och enkel att meal-prepa i stor sats.
- Utnyttja veckans extrapriser som bas – bygg recepten kring de billigaste proteinkällorna på extrapris.
- Varje rätt ska ha 4-5 portioner.
- Varorna i listan är VECKANS EXTRAPRISER – bygg recepten kring dem, inte kring fullprisvaror.

KRITISK REGEL FÖR INKÖPSLISTAN:
- Inköpslistan MÅSTE innehålla VARJE enskild ingrediens från ALLA 4 recept.
- Gå igenom varje recept rad för rad och lägg till alla ingredienser i shopping_list.
- Slå ihop samma ingrediens om den används i flera recept (t.ex. om två recept använder lök, skriv totalmängden).
- Bas-ingredienser som olivolja, salt, peppar, vitlök, lök, kryddor SKA vara med – de är inte självklara.
- Det är oacceptabelt om en ingrediens nämns i ett recept men saknas i inköpslistan.

Du MÅSTE svara med ENBART giltig JSON, utan förklarande text, markdown eller kodblock.
Strukturen måste matcha detta schema exakt:

{{
  "week": "ÅÅÅÅ-MM-DD",
  "strategy": {{
    "primary_store": "willys" | "ica",
    "split": true | false,
    "split_reason": "Förklaring om split=true, annars null",
    "split_savings_sek": 0
  }},
  "meals": [
    {{
      "name": "Rättens namn",
      "description": "Kort beskrivning 1–2 meningar",
      "protein_g_per_serving": 40,
      "servings": 4,
      "instructions": ["Steg 1", "Steg 2", "Steg 3"],
      "ingredients": [
        {{
          "name": "Kycklingfilé",
          "amount": "1 kg",
          "store": "willys" | "ica" | "bas",
          "price_sek": 69.90,
          "origin_flag": "🇸🇪" | "⚠️ Ursprung okänt" | null
        }}
      ]
    }}
  ],
  "shopping_list": {{
    "primary": [
      {{ "name": "Vara", "amount": "X kg", "price_sek": 0, "checked": false }}
    ],
    "secondary": []
  }},
  "total_cost_sek": 0,
  "estimated_protein_g_week": 0,
  "notes": "Eventuella varningar om ursprung eller substitut"
}}"""

user_message = f"Dagens datum: {date.today()}\n\nVeckans erbjudanden:\n{offers_json}\n\nGenerera veckans matsedel."

# ── Anropa Claude API ──────────────────────────────────────────────────────────
print("Anropar Claude API...")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_message}],
)

raw_response = message.content[0].text
print(f"Tokens använt: {message.usage.input_tokens} in / {message.usage.output_tokens} out")

# ── Parsa och spara JSON ───────────────────────────────────────────────────────
try:
    # Rensa eventuella markdown-kodblock om Claude ändå inkluderar dem
    clean = raw_response.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    menu_data = json.loads(clean)
except json.JSONDecodeError as e:
    print(f"Fel: Claude returnerade ogiltig JSON: {e}")
    print("Råsvar:", raw_response[:500])
    sys.exit(1)

# Sätt veckodatum om Claude missade det
menu_data.setdefault("week", str(date.today()))

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(menu_data, f, ensure_ascii=False, indent=2)

print(f"✅ Matsedel sparad till {OUTPUT_PATH}")

# ── Discord-notis ──────────────────────────────────────────────────────────────
webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
if webhook_url:
    week = menu_data.get("week", str(date.today()))
    primary = menu_data.get("strategy", {}).get("primary_store", "?").capitalize()
    total = menu_data.get("total_cost_sek", "?")
    protein = menu_data.get("estimated_protein_g_week", "?")
    split = menu_data.get("strategy", {}).get("split", False)
    split_text = "✂️ Delad butikstur" if split else "🏪 Samlad tur"

    embed = {
        "embeds": [{
            "title": f"🍗 Veckans matsedel – {week}",
            "description": (
                f"**Huvudbutik:** {primary}\n"
                f"**Strategi:** {split_text}\n"
                f"**Kostnad:** ~{total} kr\n"
                f"**Protein:** ~{protein} g för veckan"
            ),
            "color": 0x4CAF50,
            "url": "https://jamesnilsson02-alt.github.io/Food-planner/",
            "footer": {"text": "Fäladen Bulk Bot 🤖"},
        }]
    }

    try:
        resp = requests.post(webhook_url, json=embed, timeout=10)
        resp.raise_for_status()
        print("✅ Discord-notis skickad")
    except Exception as e:
        print(f"⚠️ Discord-notis misslyckades: {e}")
else:
    print("ℹ️ DISCORD_WEBHOOK_URL ej satt – hoppar över notis")
