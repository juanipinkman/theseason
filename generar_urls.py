import pandas as pd

SEASONS = [
    "2015/16", "2016/17", "2017/18", "2018/19", "2019/20",
    "2020/21", "2021/22", "2022/23", "2023/24", "2024/25", "2025/26"
]

DIVISIONS = {
    "Premier League":                   "https://en.wikipedia.org/wiki/{season_dash}_Premier_League",
    "Championship":                     "https://en.wikipedia.org/wiki/{season_dash}_EFL_Championship",
    "League One":                       "https://en.wikipedia.org/wiki/{season_dash}_EFL_League_One",
    "League Two":                       "https://en.wikipedia.org/wiki/{season_dash}_EFL_League_Two",
    "National League":                  "https://en.wikipedia.org/wiki/{season_dash}_National_League_(football)",
    "National League North":            "https://en.wikipedia.org/wiki/{season_dash}_National_League_North",
    "National League South":            "https://en.wikipedia.org/wiki/{season_dash}_National_League_South",
    "Northern Premier Division":        "https://en.wikipedia.org/wiki/{season_dash}_Northern_Premier_League_Premier_Division",
    "Southern League Premier Central":  "https://en.wikipedia.org/wiki/{season_dash}_Southern_Football_League_Premier_Division_Central",
    "Southern League Premier South":    "https://en.wikipedia.org/wiki/{season_dash}_Southern_Football_League_Premier_Division_South",
    "Isthmian League Premier Division": "https://en.wikipedia.org/wiki/{season_dash}_Isthmian_League_Premier_Division",
}

rows = []
for season in SEASONS:
    season_dash = season.replace("/", "-")
    for division, url_template in DIVISIONS.items():
        url = url_template.format(season_dash=season_dash)
        rows.append({
            "temporada": season,
            "division": division,
            "url": url,
            "activo": 1
        })

df = pd.DataFrame(rows)
df.to_excel("config/urls_scrapeo.xlsx", index=False)
print(f"Generadas {len(rows)} URLs en config/urls_scrapeo.xlsx")