# Fashion SMB Finder 🏪

**Find fashion/clothing stores with no web presence in any city — grouped by street density and exported as interactive maps, KML routes, and CSV lists.**

Built as a practical prospecting tool for anyone who works with local small businesses in the fashion sector: sales reps, web agencies, consultants, or freelancers looking for clients without an online presence.

---

## What it does

1. Takes a city name as input.
2. Queries **Google Places API** (Nearby Search + Text Search) across multiple fashion categories and keywords.
3. Filters out known retail chains and any store that already has a website via Place Details.
4. Groups the remaining stores by street to surface **high-density zones** — the best areas to visit in one go.
5. Exports the results in three formats:

| Format | Use case |
|--------|----------|
| 🗺️ Interactive HTML map (Folium + heatmap) | Visual overview in any browser |
| 📍 KML route (Google Earth / Maps) | Optimised visit order on your phone |
| 📄 CSV | Further analysis or CRM import |

---

## Demo output

```
  📍 London → 51.5074, -0.1278  (radius: 1000m)

  ✅ Stores without website found: 47

  TOP STREETS BY DENSITY
  #    STORES   STREET
  1    8        Oxford Street
  2    5        Carnaby Street
  3    4        King's Road
  ...
```

---

## Requirements

- Python 3.10+
- A Google Places API key (free tier covers typical personal use — see [guide inside the app](#how-to-get-an-api-key))

```
pip install requests folium simplekml
```

---

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/fashion-smb-finder.git
cd fashion-smb-finder
pip install -r requirements.txt
python fashion_smb_finder.py
```

On first run, go to **Option 5 → Configuration** and paste your API key. Then select **Option 1** to run your first search.

---

## How to get an API key

Google gives **$200 free credit per month** — enough for hundreds of searches at personal scale. A card is required for verification only; set a $0 spending cap to guarantee you are never charged.

The app includes a built-in step-by-step guide (**Option 4** from the main menu).

Short version:
1. [Create a Google Cloud project](https://console.cloud.google.com/)
2. Enable **Places API** in the API library
3. Create an API key under Credentials
4. Paste it into the app (Option 5)

---

## Configuration

Settings are stored in `config.json` (auto-created on first run).

| Key | Default | Description |
|-----|---------|-------------|
| `google_api_key` | `""` | Your Places API key |
| `search_radius_m` | `1000` | Search radius in metres |
| `min_stores_per_street` | `1` | Minimum stores to show a street in results |
| `max_results` | `60` | API result cap per query |

---

## Project structure

```
fashion-smb-finder/
├── fashion_smb_finder.py   # Main application
├── requirements.txt        # Dependencies
├── config.json             # Auto-created on first run (not committed)
├── search_history.csv      # Auto-created on first run (not committed)
└── outputs/                # Generated maps, KML files and CSVs
```

---

## How it filters stores

The tool applies two layers of filtering to surface only genuine small businesses:

**Known chains** (Zara, H&M, Nike, Primark, etc.) are skipped immediately without any API call, saving quota.

**Website check** — for all remaining stores, the app calls Place Details to fetch the `website` field. Any store with a website is excluded. This is the costlier step in terms of API quota; you can monitor usage in the Google Cloud Console.

---

## Limitations

- Results depend on how complete Google Places data is for your city. Smaller cities may return fewer results.
- The website filter only catches stores where Google has recorded a website — some stores may have a site that isn't in the Places database.
- The KML route uses a **nearest-neighbour heuristic** (not exact TSP), which works well in practice for up to ~50 stops.

---

## Tech stack

| Library | Role |
|---------|------|
| `requests` | Google Places API calls |
| `folium` | Interactive HTML map with heatmap layer |
| `simplekml` | KML route generation |
| Standard library (`csv`, `json`, `math`) | Config, history, Haversine distance |

---

## Contributing

This project is feature-complete for its intended use case. That said, if you find a bug or have a focused improvement in mind, feel free to open an issue or a pull request. Ideas that could make this genuinely more useful to others are welcome.

---

## License

MIT — free to use, modify, and distribute.
