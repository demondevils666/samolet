# Jeff Sackmann tennis_atp / tennis_wta on GitHub — access log

Accessed: 2026-10-26 (UTC). github.com HTML pages are not reachable through this session's proxy (it answers for non-attached repos with its own message), so several independent routes were used.

## 1. WebFetch tool (fetches github.com directly, outside this session's proxy)

| URL | Result |
|---|---|
| https://github.com/JeffSackmann/tennis_atp | "The server returned HTTP 404 Not Found." |
| https://github.com/JeffSackmann/tennis_wta | "The server returned HTTP 404 Not Found." |
| https://github.com/torvalds/linux (control) | page returned; description "Linux kernel source tree" |
| https://github.com/JeffSackmann (profile) | see below |
| https://api.github.com/repos/JeffSackmann/tennis_atp | "The server returned HTTP 403 Forbidden." |

WebFetch output for https://github.com/JeffSackmann:

> The profile is available. It shows JeffSackmann with 1.4k followers and 0 following.
>
> The page shows one public repository, and it appears only in the Pinned section:
>
> - **tennis_MatchChartingProject**: "Raw, user-submitted point-by-point data for pro tennis matches" (453 stars, 146 forks). No license is displayed.
>
> The Repositories tab reports a count of 1, but the page does not show a separate repository list. The pinned section also displays an error message ("Something went wrong, please refresh the page to try again."), so the content may not have loaded fully.

## 2. raw.githubusercontent.com via curl (HTTP status codes)

| Path | Status |
|---|---|
| JeffSackmann/tennis_atp/{master,main,HEAD}/{README.md, LICENSE, atp_players.csv} | 404 (all 9) |
| JeffSackmann/tennis_wta/{master,main,HEAD}/{README.md, LICENSE, wta_players.csv} | 404 (all 9) |
| JeffSackmann/tennis_MatchChartingProject/master/README.md (control) | 200 |

The control README (tennis_MatchChartingProject) contains: "licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License" and "In other words: Attribution is required. Non-commercial use only."

## 3. Claude Code add_repo (read access) — error text

> add_repo: repository "jeffsackmann/tennis_atp" was not found on github.com, or this session's GitHub credential doesn't have access to it. ... Detail: you don't have access to jeffsackmann/tennis_atp

(same for jeffsackmann/tennis_wta)

## 4. git ls-remote https://github.com/JeffSackmann/tennis_atp

> fatal: could not read Username for 'https://github.com': terminal prompts disabled

(same for tennis_wta; not conclusive on its own, since it goes through the session proxy)

## 5. Third-party reports (not official statements)

See 5-11_*.md (GitHub issue MLT-OSS/FirstData#238) and 5-08/5-09/5-10 (community mirror Aneeshers/tennis-sackmann-archive, which keeps copies of the upstream READMEs).
