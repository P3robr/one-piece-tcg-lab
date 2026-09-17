from __future__ import annotations

import hashlib
import html
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CARDLIST_URL = "https://en.onepiece-cardgame.com/cardlist/"
_DL = re.compile(r'<dl class="modalCol" id="([^"]+)">(.*?)</dl>', re.S)
_INFO = re.compile(
    r'<div class="infoCol">\s*<span>([^<]+)</span>\s*\|\s*'
    r'<span>([^<]+)</span>\s*\|\s*<span>([^<]+)</span>',
    re.S,
)
_SERIES = re.compile(r'<option value="(\d+)"[^>]*>(.*?)</option>', re.S)


def _text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return " ".join(html.unescape(fragment).split())


def _field(block: str, css_class: str) -> str | None:
    match = re.search(
        rf'<div class="{re.escape(css_class)}">(?:<h3>.*?</h3>)?(.*?)</div>',
        block,
        re.S,
    )
    if not match:
        return None
    value = _text(match.group(1))
    return None if value in {"", "-"} else value


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", value.replace(",", ""))
    return int(match.group()) if match else None


def extract_keywords(effect: str, trigger: str) -> list[dict]:
    combined = "\n".join(part for part in (effect, trigger) if part)
    facts: list[dict] = []
    for keyword in ("Rush", "Blocker", "Double Attack", "Banish"):
        token = rf"\[{re.escape(keyword)}(?:\s*:[^\]]+)?\]"
        for match in re.finditer(token, combined, re.I):
            clause = combined[: match.start()].rsplit(".", 1)[-1].rsplit("\n", 1)[-1]
            # A printed keyword begins a clause, optionally after timing/DON tokens.
            # Other occurrences are conditional grants or references, never a base keyword.
            scope = "intrinsic" if re.fullmatch(r"\s*(?:\[[^\]]+\]\s*)*", clause) else "granted"
            facts.append(
                {
                    "keyword": keyword,
                    "scope": scope,
                    "evidence": match.group(),
                    "confidence": 1.0,
                }
            )
    if trigger:
        facts.append(
            {"keyword": "Trigger", "scope": "intrinsic", "evidence": trigger, "confidence": 1.0}
        )
    return facts


def parse_cardlist(html_text: str, source_url: str = CARDLIST_URL) -> dict:
    """Parse Bandai's public text view without copying card images."""
    captured_at = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(html_text.encode("utf-8")).hexdigest()
    cards: dict[str, dict] = {}
    printings: list[dict] = []
    for variant_id, block in _DL.findall(html_text):
        info = _INFO.search(block)
        if not info:
            continue
        number, rarity, category = (_text(part) for part in info.groups())
        number = number.upper()
        if not re.fullmatch(r"[A-Z0-9]+-\d{3}", number):
            continue
        name_match = re.search(r'<div class="cardName">(.*?)</div>', block, re.S)
        name = _text(name_match.group(1)) if name_match else number
        color_text = _field(block, "color") or ""
        colors = [part.strip() for part in color_text.split("/") if part.strip()]
        attribute_match = re.search(r'<div class="attribute">.*?<i>(.*?)</i>', block, re.S)
        attributes = [_text(attribute_match.group(1))] if attribute_match else []
        traits = [part.strip() for part in (_field(block, "feature") or "").split("/") if part.strip()]
        effect = _field(block, "text") or ""
        trigger = _field(block, "trigger") or ""
        card = {
            "number": number,
            "name": name,
            "category": category.title(),
            "colors": colors,
            "cost": _integer(_field(block, "cost")) if category.upper() != "LEADER" else None,
            "life": _integer(_field(block, "cost")) if category.upper() == "LEADER" else None,
            "power": _integer(_field(block, "power")),
            "counter": _integer(_field(block, "counter")) or 0,
            "rarity": rarity,
            "attributes": attributes,
            "traits": traits,
            "effect": effect,
            "trigger": trigger,
            "keywords": extract_keywords(effect, trigger),
            "source_url": source_url,
            "captured_at": captured_at,
            "content_hash": digest,
        }
        prior = cards.get(number)
        if prior is None or variant_id == number:
            cards[number] = card
        printings.append(
            {
                "print_id": variant_id,
                "card_number": number,
                "block_icon": _field(block, "block") or "?",
                "set_name": _field(block, "getInfo"),
                "source_url": source_url,
            }
        )
    series = [
        {"id": series_id, "name": _text(label)}
        for series_id, label in _SERIES.findall(html_text)
    ]
    return {
        "cards": list(cards.values()),
        "printings": printings,
        "series": series,
        "source": {
            "name": "Bandai English card list",
            "kind": "official",
            "url": source_url,
            "captured_at": captured_at,
            "content_hash": digest,
        },
    }


def fetch_page(series_id: str | None = None, timeout: float = 45.0) -> tuple[str, str]:
    url = CARDLIST_URL
    if series_id:
        url += "?" + urlencode({"series": series_id})
    request = Request(url, headers={"User-Agent": "OnePieceTCGLab/0.2 (personal research)"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8"), response.geturl()


def fetch_catalog(delay: float = 0.2) -> dict:
    """Fetch every series listed by Bandai and return one deduplicated dataset."""
    index_html, index_url = fetch_page()
    index = parse_cardlist(index_html, index_url)
    series = index["series"]
    cards: dict[str, dict] = {}
    printings: dict[str, dict] = {}
    hashes: list[str] = []
    for position, item in enumerate(series):
        if position:
            time.sleep(delay)
        page, url = fetch_page(item["id"])
        parsed = parse_cardlist(page, url)
        hashes.append(parsed["source"]["content_hash"])
        for card in parsed["cards"]:
            cards.setdefault(card["number"], card)
        for printing in parsed["printings"]:
            printings[printing["print_id"]] = printing
    return {
        "cards": list(cards.values()),
        "printings": list(printings.values()),
        "source": {
            "name": "Bandai English card list",
            "kind": "official",
            "url": CARDLIST_URL,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": hashlib.sha256("".join(hashes).encode()).hexdigest(),
            "series_count": len(series),
        },
    }
