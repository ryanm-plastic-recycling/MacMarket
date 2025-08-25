"""Parse QuiverQuant strategy email HTML."""
from __future__ import annotations
from bs4 import BeautifulSoup
from decimal import Decimal
from dateutil import parser as dateparser
from typing import List, Dict, Tuple

EXPECTED_HEADERS = [
    "ticker",
    "new allocation in %",
    "current allocation in %",
    "transaction",
    "rebalance date",
]


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def parse_email_html(html: str) -> List[Tuple[str, "date", List[Dict]]]:
    soup = BeautifulSoup(html, "lxml")
    strategies = []
    for table in soup.find_all("table"):
        header_cells = table.find("tr")
        if not header_cells:
            continue
        headers = [_norm(c.get_text()) for c in header_cells.find_all(["th", "td"])]
        if len(headers) < 5 or any(h not in headers for h in EXPECTED_HEADERS):
            continue
        # strategy name is previous bold/strong text
        name = "Unknown Strategy"
        prev = table.find_previous()
        while prev:
            if prev.name in {"b", "strong"}:
                name = prev.get_text(strip=True)
                break
            if prev.name in {"p", "div"} and prev.find("b"):
                name = prev.get_text(strip=True)
                break
            prev = prev.find_previous()
        rows = []
        rebalance_date = None
        for tr in table.find_all("tr")[1:]:
            cells = [c.get_text(strip=True) for c in tr.find_all("td")]
            if len(cells) < 5:
                continue
            ticker = cells[0].strip().upper()
            new_pct = Decimal(cells[1].replace("%", "").strip() or "0") / Decimal(100)
            cur_pct = Decimal(cells[2].replace("%", "").strip() or "0") / Decimal(100)
            txn_map = {
                "open trade": "Open Trade",
                "rebalance": "Rebalance",
                "close trade": "Close Trade",
            }
            txn = txn_map.get(cells[3].strip().lower(), cells[3].strip())
            r_date = dateparser.parse(cells[4]).date()
            rebalance_date = rebalance_date or r_date
            rows.append(
                {
                    "ticker": ticker,
                    "target_weight": new_pct,
                    "current_weight": cur_pct,
                    "transaction": txn,
                    "rebalance_date": r_date,
                }
            )
        if rows:
            strategies.append((name, rebalance_date, rows))
    return strategies
