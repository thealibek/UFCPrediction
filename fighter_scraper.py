"""Fighter database scraper.

Источники:
1. UFCStats.com — официальные данные UFC: ~4000 бойцов всех времён
   (списки A-Z + индивидуальные карточки со SLpM/StrAcc/TDAvg/etc.)
2. Sherdog — не-UFC organizations (Bellator/PFL/ONE) через rosters

Сохраняет в `fighters_db.json` (отдельно от текущего fighters.json
чтобы не перетереть пользовательские правки).

Структура одной записи:
{
  "name", "nickname", "org" ("UFC"/"Bellator"/"PFL"/"ONE"),
  "height_in", "height_cm", "weight_lb", "reach_in", "reach_cm",
  "stance", "wins", "losses", "draws", "is_champion",
  "ufcstats_url", "ufcstats_id",
  "SLpM", "StrAcc", "SApM", "StrDef",
  "TDAvg", "TDAcc", "TDDef", "SubAvg",
  "dob", "age", "career_record_str",
  "scraped_at": ISO,
}
"""
from __future__ import annotations

import json
import re
import string
import time
from datetime import datetime, date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

DB_FILE = Path("fighters_db.json")
UFC_LIST_URL = "http://ufcstats.com/statistics/fighters?char={c}&page=all"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ht_to_cm(ht: str) -> int | None:
    """'5\\' 11\"' → 180 (cm)."""
    if not ht or ht == "--":
        return None
    m = re.match(r"(\d+)'\s*(\d+)\"", ht)
    if not m:
        return None
    feet, inches = int(m.group(1)), int(m.group(2))
    return round((feet * 12 + inches) * 2.54)


def _ht_to_in(ht: str) -> int | None:
    if not ht or ht == "--":
        return None
    m = re.match(r"(\d+)'\s*(\d+)\"", ht)
    if not m:
        return None
    return int(m.group(1)) * 12 + int(m.group(2))


def _reach_to_cm(r: str) -> int | None:
    if not r or r in ("--", ""):
        return None
    m = re.match(r"(\d+(?:\.\d+)?)", r)
    return round(float(m.group(1)) * 2.54) if m else None


def _reach_to_in(r: str) -> float | None:
    if not r or r in ("--", ""):
        return None
    m = re.match(r"(\d+(?:\.\d+)?)", r)
    return float(m.group(1)) if m else None


def _wt_to_lb(w: str) -> int | None:
    if not w or w == "--":
        return None
    m = re.match(r"(\d+)", w)
    return int(m.group(1)) if m else None


def _pct_to_float(s: str) -> float | None:
    if not s or s in ("--", ""):
        return None
    s = s.replace("%", "").strip()
    try:
        return float(s) / 100.0
    except Exception:
        return None


def _f(s: str) -> float | None:
    if not s or s in ("--", ""):
        return None
    try:
        return float(s)
    except Exception:
        return None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _calc_age(dob: str) -> int | None:
    """'Apr 18, 1994' → age."""
    if not dob or dob == "--":
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            d = datetime.strptime(dob, fmt).date()
            today = date.today()
            return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# UFCStats: list scraper (A-Z, fast)
# ---------------------------------------------------------------------------

def scrape_ufcstats_list(letter: str,
                         session: requests.Session | None = None) -> list[dict]:
    """Парсит одну букву списка."""
    sess = session or requests.Session()
    url = UFC_LIST_URL.format(c=letter)
    r = sess.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    rows = soup.select("tr.b-statistics__table-row")
    out = []
    for row in rows:
        cols = row.select("td")
        if len(cols) < 11:
            continue
        link = cols[0].select_one("a")
        if not link:
            continue
        url = link.get("href", "")
        ufc_id = url.rstrip("/").split("/")[-1]
        first = link.text.strip()
        last_el = cols[1].select_one("a")
        last = last_el.text.strip() if last_el else cols[1].text.strip()
        nickname = cols[2].text.strip()
        height = cols[3].text.strip()
        weight = cols[4].text.strip()
        reach = cols[5].text.strip()
        stance = cols[6].text.strip()
        wins = cols[7].text.strip()
        losses = cols[8].text.strip()
        draws = cols[9].text.strip()
        belt = bool(cols[10].select_one("img"))

        name = f"{first} {last}".strip()
        if not name:
            continue

        out.append({
            "name": name, "nickname": nickname or None,
            "org": "UFC",
            "height_in": _ht_to_in(height),
            "height_cm": _ht_to_cm(height),
            "weight_lb": _wt_to_lb(weight),
            "reach_in": _reach_to_in(reach),
            "reach_cm": _reach_to_cm(reach),
            "stance": stance or None,
            "wins": int(wins) if wins.isdigit() else None,
            "losses": int(losses) if losses.isdigit() else None,
            "draws": int(draws) if draws.isdigit() else None,
            "is_champion": belt,
            "ufcstats_url": url,
            "ufcstats_id": ufc_id,
            "scraped_at": _now(),
        })
    return out


def scrape_ufcstats_all(progress_cb=None) -> list[dict]:
    """A-Z скрейп всех UFC бойцов (только list-данные, без deep stats)."""
    sess = requests.Session()
    all_rows = []
    letters = string.ascii_lowercase
    for i, c in enumerate(letters, 1):
        for attempt in range(3):
            try:
                rows = scrape_ufcstats_list(c, sess)
                all_rows.extend(rows)
                if progress_cb:
                    progress_cb(i, len(letters),
                                f"letter {c.upper()}: +{len(rows)} (total {len(all_rows)})")
                break
            except Exception as e:
                wait = 2 + attempt * 3
                if progress_cb:
                    progress_cb(i, len(letters),
                                f"letter {c.upper()} retry {attempt+1}: {e} (wait {wait}s)")
                time.sleep(wait)
        time.sleep(0.4)  # politeness
    return all_rows


# ---------------------------------------------------------------------------
# UFCStats: deep profile (per-fighter)
# ---------------------------------------------------------------------------

def scrape_ufcstats_profile(url: str,
                            session: requests.Session | None = None) -> dict:
    """Парсит отдельную страницу бойца — Career stats + DOB."""
    sess = session or requests.Session()
    r = sess.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = {}

    # Career stats: <li class="b-list__box-list-item ..."> Label: <i>Value</i>
    for li in soup.select("li.b-list__box-list-item"):
        text = " ".join(li.get_text(" ", strip=True).split())
        # Format: "LABEL: VALUE"
        m = re.match(r"([\w\.\s]+):\s*(.*)", text)
        if not m:
            continue
        label = m.group(1).strip().lower()
        val = m.group(2).strip()
        out[label] = val

    # DOB
    dob = out.get("dob")
    if dob:
        out["age"] = _calc_age(dob)

    # Career stats
    profile = {
        "dob": out.get("dob") if out.get("dob") and out["dob"] != "--" else None,
        "age": out.get("age"),
        "SLpM": _f(out.get("slpm")),
        "StrAcc": _pct_to_float(out.get("str. acc.") or out.get("str acc")),
        "SApM": _f(out.get("sapm")),
        "StrDef": _pct_to_float(out.get("str. def") or out.get("str def")),
        "TDAvg": _f(out.get("td avg.") or out.get("td avg")),
        "TDAcc": _pct_to_float(out.get("td acc.") or out.get("td acc")),
        "TDDef": _pct_to_float(out.get("td def.") or out.get("td def")),
        "SubAvg": _f(out.get("sub. avg.") or out.get("sub avg")),
    }
    return profile


def enrich_with_profiles(fighters: list[dict],
                         max_workers: int = 8,
                         progress_cb=None,
                         limit: int | None = None) -> list[dict]:
    """Дёргает индивидуальные страницы для всех бойцов (параллельно)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    targets = [f for f in fighters if f.get("ufcstats_url") and not f.get("SLpM")]
    if limit:
        targets = targets[:limit]
    sess = requests.Session()

    def _one(f):
        try:
            prof = scrape_ufcstats_profile(f["ufcstats_url"], sess)
            f.update(prof)
        except Exception as e:
            f["_profile_err"] = str(e)[:120]
        return f

    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_one, f): f for f in targets}
        for fut in as_completed(futures):
            done += 1
            if progress_cb and (done % 20 == 0 or done == len(targets)):
                progress_cb(done, len(targets), "profiles")
    return fighters


# ---------------------------------------------------------------------------
# Sherdog: non-UFC orgs (Bellator/PFL/ONE)
# ---------------------------------------------------------------------------

SHERDOG_ROSTERS = {
    "Bellator": "https://www.sherdog.com/organizations/Bellator-MMA-72/fighters",
    "PFL":      "https://www.sherdog.com/organizations/Professional-Fighters-League-26953/fighters",
    "ONE":      "https://www.sherdog.com/organizations/ONE-Championship-12450/fighters",
}


def scrape_sherdog_roster(org: str, max_pages: int = 5) -> list[dict]:
    """Скрейпит Sherdog roster (упрощённо, базовые данные).
    Sherdog часто меняет HTML — это best-effort; если сломалось, list возвращается пустой.
    """
    base = SHERDOG_ROSTERS.get(org)
    if not base:
        return []
    out = []
    sess = requests.Session()
    for page in range(1, max_pages + 1):
        url = f"{base}/page/{page}" if page > 1 else base
        try:
            r = sess.get(url, headers=UA, timeout=20)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "lxml")
            rows = soup.select("table.fighter_list tbody tr") \
                or soup.select("table tr")
            page_out = []
            for tr in rows:
                cols = tr.select("td")
                if len(cols) < 4:
                    continue
                a = tr.select_one("a")
                if not a:
                    continue
                name = a.get_text(strip=True)
                href = a.get("href", "")
                # cols variable layout — best effort
                texts = [c.get_text(" ", strip=True) for c in cols]
                # try to detect height/weight/record
                rec = next((t for t in texts if re.match(r"^\d+-\d+-\d+", t)), None)
                w = next((t for t in texts if re.search(r"\d+\s*lb|\d+\s*kg", t.lower())), None)
                page_out.append({
                    "name": name, "org": org,
                    "sherdog_url": ("https://www.sherdog.com" + href) if href.startswith("/") else href,
                    "career_record_str": rec,
                    "weight_str": w,
                    "scraped_at": _now(),
                })
            if not page_out:
                break
            out.extend(page_out)
            time.sleep(0.6)
        except Exception:
            break
    # dedupe
    seen = set(); uniq = []
    for f in out:
        if f["name"] in seen: continue
        seen.add(f["name"]); uniq.append(f)
    return uniq


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def save_db(fighters: list[dict], file: Path = DB_FILE) -> None:
    file.write_text(json.dumps(fighters, indent=2, ensure_ascii=False))


def load_db(file: Path = DB_FILE) -> list[dict]:
    if not file.exists():
        return []
    return json.loads(file.read_text())
