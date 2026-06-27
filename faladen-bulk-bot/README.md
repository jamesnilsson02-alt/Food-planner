# 🏋️ Fäladen Bulk Bot

Automatiserad veckovis matsedel optimerad för bulk/muskelbyggnad. Jämför extrapriser från Willys och ICA på Norra Fäladen, låter Claude API välja billigaste proteinrika matsedeln, och publicerar en mobilanpassad inköpslista via GitHub Pages.

---

## Kom igång

### 1. Skapa repo & klona
```bash
git clone https://github.com/DITT_USERNAME/faladen-bulk-bot.git
cd faladen-bulk-bot
```

### 2. Lägg till GitHub Secrets
Gå till **Settings → Secrets and variables → Actions** och lägg till:

| Secret | Beskrivning |
|---|---|
| `ANTHROPIC_API_KEY` | Din Anthropic API-nyckel |
| `DISCORD_WEBHOOK_URL` | Discord webhook-URL (valfritt) |

### 3. Aktivera GitHub Pages
Gå till **Settings → Pages** och sätt:
- Source: `Deploy from a branch`
- Branch: `main` / mapp: `/docs`

### 4. Aktivera GitHub Actions
Actions bör vara aktiverade per default. Kör en manuell trigger via:
**Actions → Weekly Menu Generator → Run workflow**

---

## Konfiguration

### `config/stores_config.json`
Aktivera/inaktivera butiker och ställ in tröskel för delad butikstur:
```json
{
  "stores": {
    "willys": { "enabled": true, ... },
    "ica":    { "enabled": true, ... },
    "lidl":   { "enabled": false, ... }
  },
  "split_threshold_sek": 50
}
```

### `config/user_preferences.md`
Anpassa kostmål, köttursprung och matlagningsstil direkt i markdown-filen.

---

## Arkitektur

```
Måndag 08:00
    │
    ├─ fetch_willys.py  ──┐
    ├─ fetch_ica.py     ──┼─→ Filtrerade erbjudanden
    │                      │
    └─ generate_menu.py ───┴─→ Claude API → current_menu.json → GitHub Pages
                                                              └→ Discord notis
```

---

## Kostnad
- **GitHub Actions:** Gratis (public repo eller inom free tier)
- **GitHub Pages:** Gratis
- **Claude API:** ~$0.01–0.05 per körning med claude-sonnet-4-6 (budget ~$5 totalt)
- **Discord:** Gratis
