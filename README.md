# 🏆 Monte Carlo World Cup 2026 Simulator

**Data Science Series · @fhrzl**

Interactive Monte Carlo simulator untuk FIFA World Cup 2026 — 48 tim resmi, grup aktual, dan **strength rating yang terupdate otomatis** setelah setiap pertandingan nyata.

## 🔄 Cara Kerja Auto-Update

```
Hasil match nyata (openfootball/worldcup.json)
        ↓  setiap 30 menit via GitHub Actions
  update_strengths.py  →  data/strengths.json
        ↓  auto-commit
  GitHub Pages serve docs/index.html
        ↓  fetch on load + auto-refresh 30 mnt
  Browser user dapat data terbaru
```

### Data Source
- **Match results**: [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) — free, no API key
- **Base strength**: FIFA Ranking resmi 1 April 2026
- **Live adjustment**: Bayesian-style update per match selesai

### Strength Update Formula
```python
expected_win = sigmoid(strength_A - strength_B)
delta = LEARNING_RATE * (actual - expected) ± gd_bonus
strength_A += delta
strength_B -= delta
```
- `LEARNING_RATE = 0.012` — converge pelan tapi stabil
- `gd_bonus = 0.003 × min(gol_selisih, 3)` — big win = bigger impact
- Strength diklem di `[0.30, 0.99]`

## 📁 Struktur Repo

```
wc2026-simulator/
├── .github/
│   └── workflows/
│       └── update-strengths.yml   ← GitHub Actions cron
├── data/
│   └── strengths.json             ← auto-updated setiap 30 mnt
├── docs/
│   └── index.html                 ← web app (GitHub Pages)
├── update_strengths.py            ← script fetch + update
└── README.md
```

## 🚀 Setup di GitHub

1. **Fork / upload repo ini ke GitHub**
2. Settings → Pages → Source: `Deploy from branch` → branch `main` → folder `/docs`
3. Actions tab → pastikan workflow `Update WC2026 Strengths` aktif
4. Manual trigger pertama: Actions → `Update WC2026 Strengths` → `Run workflow`

Setelah itu berjalan otomatis. Setiap match selesai, dalam 30 menit strength rating tim terupdate dan simulasi mencerminkan performa nyata.

## 📊 Live Results

- Matches played: lihat di `data/strengths.json` → `meta.matches_played`
- Last update: `meta.updated_at`
- Recent deltas: `results_log`

---

*Built with Python + vanilla JS + GitHub Actions. No paid API, no server, zero cost.*
