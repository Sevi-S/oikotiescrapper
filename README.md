# Oikotie Metro Apartment Finder

Scrapes apartment listings from [Oikotie](https://asunnot.oikotie.fi) and filters by walking distance to Helsinki/Espoo metro stations. Tracks seen listings so you only get notified about new ones.

## Quick Start (Docker)

```bash
# Start the web viewer
docker compose up -d viewer

# Run the scraper
./run_scraper.sh
```

Viewer at `http://localhost:8080`. Add a cron job for daily scraping:

```
0 8 * * * /path/to/run_scraper.sh >> /path/to/cron.log 2>&1
```

## Quick Start (Local)

```bash
pip install requests beautifulsoup4 geopy tabulate

# Run scraper
python3 oikotie_metro.py --price-min 100000 --price-max 300000 --rooms-min 3 --size-min 50 --metro-max 15

# Start viewer
python3 viewer.py
```

## Scraper Options

| Flag | Description | Default |
|------|-------------|---------|
| `--city` | Comma-separated cities | `Helsinki,Espoo` |
| `--price-min` | Min price € | - |
| `--price-max` | Max price € | - |
| `--size-min` | Min size m² | - |
| `--size-max` | Max size m² | - |
| `--rooms-min` | Min rooms | - |
| `--rooms-max` | Max rooms | - |
| `--metro-max` | Max walking minutes to metro | - |
| `--metro-from` | First metro stop in range | `Matinkylä` |
| `--metro-to` | Last metro stop in range | `Kalasatama` |
| `--building-type` | 1=kerrostalo, 2=rivitalo, 4=omakotitalo, 256=paritalo | - |
| `--max-pages` | Max API pages to scan | `50` |
| `--all` | Show all matches, not just new | - |
| `--reset` | Clear seen history | - |

## Files

| File | Purpose |
|------|---------|
| `results.csv` | Cumulative list of all matching apartments |
| `seen.json` | IDs of already-processed listings (dedup) |
| `notes.json` | Your notes from the web viewer |

## Metro Stations

The default range is Matinkylä → Kalasatama (15 stops). Available stations:

Mellunmäki, Kontula, Myllypuro, Itäkeskus, Puotila, Rastila, Vuosaari, Herttoniemi, Siilitie, Kulosaari, **Kalasatama**, Sörnäinen, Hakaniemi, Kaisaniemi, Rautatientori, Kamppi, Ruoholahti, Lauttasaari, Koivusaari, Keilaniemi, Aalto-yliopisto, Tapiola, Urheilupuisto, Niittykumpu, **Matinkylä**, Finnoo, Kivenlahti, Espoonlahti

---

Written with help from [Amazon Kiro](https://kiro.dev).
