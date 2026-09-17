from __future__ import annotations

import html
import re
import time
from collections import Counter
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


_TEXT_DECK = re.compile(r'<section class="text-deck">(.*?)</section>', re.I | re.S)
_CARD = re.compile(
    r'<span class="qty">(\d+)x</span>.*?'
    r'<span class="muted card-id">([A-Z0-9]+-\d{3})</span>',
    re.I | re.S,
)


def fetch_text(url: str, timeout: float = 45.0) -> str:
    request = Request(url, headers={"User-Agent": "OnePieceTCGLab/0.2 (personal research)"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def parse_deck_page(page: str) -> dict[str, int]:
    section = _TEXT_DECK.search(page)
    if not section:
        raise ValueError("Página sem seção de deck textual")
    entries: Counter[str] = Counter()
    for quantity, number in _CARD.findall(section.group(1)):
        entries[number.upper()] += int(quantity)
    if not entries:
        raise ValueError("Seção de deck textual sem cartas")
    return dict(entries)


def fetch_decklists(hub_url: str, delay: float = 0.2) -> list[dict]:
    hub = fetch_text(hub_url)
    hub_path = urlparse(hub_url).path
    directory = hub_path.rsplit(".", 1)[0] + "/"
    link_pattern = re.compile(rf'href="({re.escape(directory)}[^"]+\.html)"', re.I)
    urls = list(dict.fromkeys(urljoin(hub_url, html.unescape(path)) for path in link_pattern.findall(hub)))
    results = []
    for position, url in enumerate(urls):
        if position:
            time.sleep(delay)
        results.append({"url": url, "entries": parse_deck_page(fetch_text(url))})
    return results
