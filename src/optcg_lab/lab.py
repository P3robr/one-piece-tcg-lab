from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator


CARD_NUMBER = re.compile(r"^[A-Z0-9]+-\d{3}$")
DECK_LINE = re.compile(r"^\s*(\d+)\s*(?:x|X)?\s*([A-Za-z0-9]+-\d{3})\s*$")
CARD_CATEGORIES = {"Leader", "Character", "Event", "Stage"}


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cards (
    number TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Leader', 'Character', 'Event', 'Stage')),
    cost INTEGER,
    power INTEGER,
    life INTEGER,
    counter INTEGER NOT NULL DEFAULT 0 CHECK (counter >= 0),
    attribute TEXT,
    rarity TEXT,
    block_icon TEXT NOT NULL,
    deck_rule_override INTEGER NOT NULL DEFAULT 0 CHECK (deck_rule_override IN (0, 1)),
    effect TEXT NOT NULL DEFAULT '',
    trigger TEXT NOT NULL DEFAULT '',
    source_url TEXT,
    captured_at TEXT,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS card_printings (
    print_id TEXT PRIMARY KEY,
    card_number TEXT NOT NULL REFERENCES cards(number) ON DELETE CASCADE,
    block_icon TEXT NOT NULL,
    set_name TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS card_attributes (
    card_number TEXT NOT NULL REFERENCES cards(number) ON DELETE CASCADE,
    attribute TEXT NOT NULL,
    PRIMARY KEY (card_number, attribute)
);

CREATE TABLE IF NOT EXISTS card_keywords (
    card_number TEXT NOT NULL REFERENCES cards(number) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('intrinsic', 'granted')),
    evidence TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    PRIMARY KEY (card_number, keyword, scope, evidence)
);

CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    url TEXT NOT NULL,
    UNIQUE(name, url)
);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(id),
    captured_at TEXT NOT NULL,
    content_hash TEXT,
    item_count INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS card_colors (
    card_number TEXT NOT NULL REFERENCES cards(number) ON DELETE CASCADE,
    color TEXT NOT NULL,
    PRIMARY KEY (card_number, color)
);

CREATE TABLE IF NOT EXISTS card_traits (
    card_number TEXT NOT NULL REFERENCES cards(number) ON DELETE CASCADE,
    trait TEXT NOT NULL,
    PRIMARY KEY (card_number, trait)
);

CREATE TABLE IF NOT EXISTS effect_facts (
    id INTEGER PRIMARY KEY,
    card_number TEXT NOT NULL REFERENCES cards(number) ON DELETE CASCADE,
    mechanic TEXT NOT NULL,
    subject TEXT,
    target TEXT,
    timing TEXT,
    condition_text TEXT,
    cost_text TEXT,
    duration_text TEXT,
    value INTEGER,
    evidence TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    parser_version TEXT,
    reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1))
);

CREATE TABLE IF NOT EXISTS formats (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source_url TEXT,
    UNIQUE (name, region, valid_from)
);

CREATE TABLE IF NOT EXISTS format_blocks (
    format_id INTEGER NOT NULL REFERENCES formats(id) ON DELETE CASCADE,
    block_icon TEXT NOT NULL,
    PRIMARY KEY (format_id, block_icon)
);

CREATE TABLE IF NOT EXISTS restrictions (
    format_id INTEGER NOT NULL REFERENCES formats(id) ON DELETE CASCADE,
    card_number TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('banned', 'restricted')),
    max_copies INTEGER,
    source_url TEXT,
    PRIMARY KEY (format_id, card_number)
);

CREATE TABLE IF NOT EXISTS banned_pairs (
    format_id INTEGER NOT NULL REFERENCES formats(id) ON DELETE CASCADE,
    card_a TEXT NOT NULL,
    card_b TEXT NOT NULL,
    source_url TEXT,
    PRIMARY KEY (format_id, card_a, card_b),
    CHECK (card_a < card_b)
);

CREATE TABLE IF NOT EXISTS usage_stats (
    source_name TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    environment TEXT NOT NULL,
    format_name TEXT NOT NULL,
    leader_number TEXT NOT NULL,
    card_number TEXT NOT NULL,
    deck_count INTEGER NOT NULL CHECK (deck_count >= 0),
    decks_with_card INTEGER NOT NULL CHECK (decks_with_card >= 0),
    copies_total INTEGER NOT NULL CHECK (copies_total >= 0),
    source_url TEXT,
    PRIMARY KEY (source_name, captured_at, environment, leader_number, card_number)
);

CREATE TABLE IF NOT EXISTS matchup_stats (
    source_name TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    environment TEXT NOT NULL,
    format_name TEXT NOT NULL,
    leader_a TEXT NOT NULL,
    leader_b TEXT NOT NULL,
    games INTEGER NOT NULL CHECK (games > 0),
    wins_a INTEGER NOT NULL CHECK (wins_a >= 0 AND wins_a <= games),
    going_first_games INTEGER,
    source_url TEXT,
    notes TEXT,
    PRIMARY KEY (source_name, captured_at, environment, leader_a, leader_b)
);

CREATE TABLE IF NOT EXISTS leader_stats (
    source_name TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    environment TEXT NOT NULL,
    format_name TEXT NOT NULL,
    leader_number TEXT NOT NULL,
    games INTEGER NOT NULL CHECK (games > 0),
    wins INTEGER NOT NULL CHECK (wins >= 0 AND wins <= games),
    source_rank INTEGER,
    sample_kind TEXT NOT NULL,
    source_url TEXT,
    PRIMARY KEY (source_name, captured_at, environment, leader_number, sample_kind)
);

CREATE TABLE IF NOT EXISTS personal_matches (
    id INTEGER PRIMARY KEY,
    played_at TEXT NOT NULL,
    my_leader TEXT NOT NULL,
    opponent_leader TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
    went_first INTEGER CHECK (went_first IN (0, 1)),
    my_deck_label TEXT,
    notes TEXT
);
"""


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def parse_decklist(text: str) -> dict[str, int]:
    entries: Counter[str] = Counter()
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = DECK_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"Linha {line_number} inválida: {raw!r}")
        quantity = int(match.group(1))
        number = match.group(2).upper()
        if quantity <= 0:
            raise ValueError(f"Linha {line_number}: quantidade deve ser positiva")
        entries[number] += quantity
    if not entries:
        raise ValueError("Decklist vazia")
    return dict(entries)


class LabDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(cards)")}
            if "trigger" not in columns:
                connection.execute("ALTER TABLE cards ADD COLUMN trigger TEXT NOT NULL DEFAULT ''")

    def import_dataset(self, dataset: dict) -> None:
        self.initialize()
        with self.connect() as connection:
            printing_blocks: dict[str, str] = {}
            for printing in dataset.get("printings", []):
                printing_blocks.setdefault(printing["card_number"].upper(), str(printing["block_icon"]))
            for card in dataset.get("cards", []):
                if "block_icon" not in card:
                    card = {**card, "block_icon": printing_blocks.get(card["number"].upper(), "?")}
                self._import_card(connection, card)
            for printing in dataset.get("printings", []):
                connection.execute(
                    """
                    INSERT INTO card_printings(print_id, card_number, block_icon, set_name, source_url)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(print_id) DO UPDATE SET card_number=excluded.card_number,
                      block_icon=excluded.block_icon, set_name=excluded.set_name,
                      source_url=excluded.source_url
                    """,
                    (
                        printing["print_id"], printing["card_number"].upper(),
                        str(printing["block_icon"]), printing.get("set_name"),
                        printing.get("source_url"),
                    ),
                )
            source = dataset.get("source")
            if source:
                cursor = connection.execute(
                    """INSERT INTO data_sources(name, kind, url) VALUES (?, ?, ?)
                    ON CONFLICT(name, url) DO UPDATE SET kind=excluded.kind RETURNING id""",
                    (source["name"], source["kind"], source["url"]),
                )
                source_id = int(cursor.fetchone()[0])
                connection.execute(
                    """INSERT INTO import_runs(source_id, captured_at, content_hash, item_count, status)
                    VALUES (?, ?, ?, ?, 'complete')""",
                    (source_id, source["captured_at"], source.get("content_hash"), len(dataset.get("cards", []))),
                )
            format_ids: dict[tuple[str, str, str], int] = {}
            for item in dataset.get("formats", []):
                key = (item["name"], item["region"], item["valid_from"])
                cursor = connection.execute(
                    """
                    INSERT INTO formats(name, region, valid_from, valid_to, source_url)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name, region, valid_from) DO UPDATE SET
                      valid_to=excluded.valid_to, source_url=excluded.source_url
                    RETURNING id
                    """,
                    (*key, item.get("valid_to"), item.get("source_url")),
                )
                format_id = int(cursor.fetchone()[0])
                format_ids[key] = format_id
                connection.execute("DELETE FROM format_blocks WHERE format_id=?", (format_id,))
                connection.executemany(
                    "INSERT INTO format_blocks(format_id, block_icon) VALUES (?, ?)",
                    ((format_id, str(block)) for block in item.get("allowed_blocks", [])),
                )
            for item in dataset.get("restrictions", []):
                format_id = self._resolve_format_id(connection, item, format_ids)
                kind = item["kind"]
                max_copies = item.get("max_copies", 1 if kind == "restricted" else 0)
                connection.execute(
                    """
                    INSERT INTO restrictions(format_id, card_number, kind, max_copies, source_url)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(format_id, card_number) DO UPDATE SET
                      kind=excluded.kind, max_copies=excluded.max_copies,
                      source_url=excluded.source_url
                    """,
                    (format_id, item["card_number"].upper(), kind, max_copies, item.get("source_url")),
                )
            for item in dataset.get("banned_pairs", []):
                format_id = self._resolve_format_id(connection, item, format_ids)
                card_a, card_b = sorted((item["card_a"].upper(), item["card_b"].upper()))
                connection.execute(
                    """
                    INSERT INTO banned_pairs(format_id, card_a, card_b, source_url)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(format_id, card_a, card_b) DO UPDATE SET
                      source_url=excluded.source_url
                    """,
                    (format_id, card_a, card_b, item.get("source_url")),
                )
            for item in dataset.get("usage_stats", []):
                connection.execute(
                    """INSERT OR REPLACE INTO usage_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["source_name"], item["captured_at"], item["environment"],
                        item["format_name"], item["leader_number"].upper(),
                        item["card_number"].upper(), item["deck_count"],
                        item["decks_with_card"], item["copies_total"], item.get("source_url"),
                    ),
                )
            for item in dataset.get("matchups", []):
                connection.execute(
                    """INSERT OR REPLACE INTO matchup_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["source_name"], item["captured_at"], item["environment"],
                        item["format_name"], item["leader_a"].upper(), item["leader_b"].upper(),
                        item["games"], item["wins_a"], item.get("going_first_games"),
                        item.get("source_url"), item.get("notes"),
                    ),
                )
            for item in dataset.get("leader_stats", []):
                connection.execute(
                    """INSERT OR REPLACE INTO leader_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["source_name"], item["captured_at"], item["environment"],
                        item["format_name"], item["leader_number"].upper(), item["games"],
                        item["wins"], item.get("source_rank"), item["sample_kind"],
                        item.get("source_url"),
                    ),
                )
            for item in dataset.get("personal_matches", []):
                connection.execute(
                    """INSERT INTO personal_matches(played_at, my_leader, opponent_leader,
                    result, went_first, my_deck_label, notes) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["played_at"], item["my_leader"].upper(),
                        item["opponent_leader"].upper(), item["result"],
                        item.get("went_first"), item.get("my_deck_label"), item.get("notes"),
                    ),
                )

    @staticmethod
    def _resolve_format_id(
        connection: sqlite3.Connection,
        item: dict,
        imported: dict[tuple[str, str, str], int],
    ) -> int:
        if "format_valid_from" in item:
            key = (item["format_name"], item["region"], item["format_valid_from"])
            if key in imported:
                return imported[key]
            row = connection.execute(
                "SELECT id FROM formats WHERE name=? AND region=? AND valid_from=?",
                key,
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT id FROM formats WHERE name=? AND region=?
                ORDER BY valid_from DESC LIMIT 1
                """,
                (item["format_name"], item["region"]),
            ).fetchone()
        if row is None:
            raise ValueError(f"Formato não encontrado para restrição: {item}")
        return int(row[0])

    @staticmethod
    def _import_card(connection: sqlite3.Connection, card: dict) -> None:
        number = card["number"].upper()
        if not CARD_NUMBER.fullmatch(number):
            raise ValueError(f"Número de card inválido: {number}")
        if card["category"] not in CARD_CATEGORIES:
            raise ValueError(f"Categoria inválida para {number}: {card['category']}")
        colors = sorted(set(card.get("colors", [])))
        if not colors:
            raise ValueError(f"Card sem cor: {number}")
        connection.execute(
            """
            INSERT INTO cards(
              number, name, category, cost, power, life, counter, attribute,
              rarity, block_icon, deck_rule_override, effect, source_url,
              trigger, captured_at, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(number) DO UPDATE SET
              name=excluded.name, category=excluded.category, cost=excluded.cost,
              power=excluded.power, life=excluded.life, counter=excluded.counter,
              attribute=excluded.attribute, rarity=excluded.rarity,
              block_icon=excluded.block_icon,
              deck_rule_override=excluded.deck_rule_override,
              effect=excluded.effect, trigger=excluded.trigger,
              source_url=excluded.source_url, captured_at=excluded.captured_at,
              content_hash=excluded.content_hash
            """,
            (
                number,
                card["name"],
                card["category"],
                card.get("cost"),
                card.get("power"),
                card.get("life"),
                card.get("counter", 0),
                card.get("attribute"),
                card.get("rarity"),
                str(card["block_icon"]),
                int(bool(card.get("deck_rule_override", False))),
                card.get("effect", ""),
                card.get("source_url"),
                card.get("trigger", ""),
                card.get("captured_at"),
                card.get("content_hash"),
            ),
        )
        connection.execute("DELETE FROM card_colors WHERE card_number=?", (number,))
        connection.executemany(
            "INSERT INTO card_colors(card_number, color) VALUES (?, ?)",
            ((number, color) for color in colors),
        )
        connection.execute("DELETE FROM card_traits WHERE card_number=?", (number,))
        connection.executemany(
            "INSERT INTO card_traits(card_number, trait) VALUES (?, ?)",
            ((number, trait) for trait in sorted(set(card.get("traits", [])))),
        )
        connection.execute("DELETE FROM card_attributes WHERE card_number=?", (number,))
        attributes = card.get("attributes", [card["attribute"]] if card.get("attribute") else [])
        connection.executemany(
            "INSERT INTO card_attributes(card_number, attribute) VALUES (?, ?)",
            ((number, attribute) for attribute in sorted(set(attributes))),
        )
        connection.execute("DELETE FROM card_keywords WHERE card_number=?", (number,))
        keyword_rows = {
            (number, fact["keyword"], fact["scope"], fact["evidence"], fact.get("confidence", 1.0))
            for fact in card.get("keywords", [])
        }
        connection.executemany(
            """INSERT INTO card_keywords(card_number, keyword, scope, evidence, confidence)
            VALUES (?, ?, ?, ?, ?)""",
            sorted(keyword_rows),
        )

    def load_cards(self, numbers: Iterable[str]) -> dict[str, dict]:
        normalized = sorted({number.upper() for number in numbers})
        if not normalized:
            return {}
        placeholders = ",".join("?" for _ in normalized)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM cards WHERE number IN ({placeholders})", normalized
            ).fetchall()
            cards = {row["number"]: dict(row) for row in rows}
            color_rows = connection.execute(
                f"SELECT card_number, color FROM card_colors WHERE card_number IN ({placeholders})",
                normalized,
            ).fetchall()
            trait_rows = connection.execute(
                f"SELECT card_number, trait FROM card_traits WHERE card_number IN ({placeholders})",
                normalized,
            ).fetchall()
            attribute_rows = connection.execute(
                f"SELECT card_number, attribute FROM card_attributes WHERE card_number IN ({placeholders})",
                normalized,
            ).fetchall()
            keyword_rows = connection.execute(
                f"SELECT card_number, keyword, scope, evidence, confidence FROM card_keywords WHERE card_number IN ({placeholders})",
                normalized,
            ).fetchall()
            printing_rows = connection.execute(
                f"SELECT * FROM card_printings WHERE card_number IN ({placeholders})", normalized
            ).fetchall()
        for card in cards.values():
            card["colors"] = []
            card["traits"] = []
            card["attributes"] = []
            card["keywords"] = []
            card["printings"] = []
        for row in color_rows:
            cards[row["card_number"]]["colors"].append(row["color"])
        for row in trait_rows:
            cards[row["card_number"]]["traits"].append(row["trait"])
        for row in attribute_rows:
            cards[row["card_number"]]["attributes"].append(row["attribute"])
        for row in keyword_rows:
            cards[row["card_number"]]["keywords"].append(dict(row))
        for row in printing_rows:
            cards[row["card_number"]]["printings"].append(dict(row))
        return cards

    def active_format(self, name: str, region: str, on_date: str) -> dict:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM formats
                WHERE name=? AND region=? AND valid_from<=?
                  AND (valid_to IS NULL OR valid_to>=?)
                ORDER BY valid_from DESC LIMIT 1
                """,
                (name, region, on_date, on_date),
            ).fetchone()
            if row is None:
                raise ValueError(f"Formato {name}/{region} não encontrado em {on_date}")
            result = dict(row)
            result["allowed_blocks"] = {
                item[0]
                for item in connection.execute(
                    "SELECT block_icon FROM format_blocks WHERE format_id=?", (row["id"],)
                )
            }
            result["restrictions"] = {
                item["card_number"]: dict(item)
                for item in connection.execute(
                    "SELECT * FROM restrictions WHERE format_id=?", (row["id"],)
                )
            }
            result["banned_pairs"] = [
                (item["card_a"], item["card_b"])
                for item in connection.execute(
                    "SELECT * FROM banned_pairs WHERE format_id=?", (row["id"],)
                )
            ]
            return result

    def reindex_keywords(self) -> int:
        from .official import extract_keywords

        with self.connect() as connection:
            cards = connection.execute("SELECT number, effect, trigger FROM cards").fetchall()
            connection.execute("DELETE FROM card_keywords")
            rows = {
                (card["number"], fact["keyword"], fact["scope"], fact["evidence"], fact["confidence"])
                for card in cards
                for fact in extract_keywords(card["effect"], card["trigger"])
            }
            connection.executemany(
                "INSERT INTO card_keywords(card_number, keyword, scope, evidence, confidence) VALUES (?, ?, ?, ?, ?)",
                sorted(rows),
            )
        return len(rows)

    def record_match(
        self,
        played_at: str,
        my_leader: str,
        opponent_leader: str,
        result: str,
        went_first: bool | None = None,
        my_deck_label: str | None = None,
        notes: str | None = None,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO personal_matches(played_at, my_leader, opponent_leader,
                result, went_first, my_deck_label, notes) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (played_at, my_leader.upper(), opponent_leader.upper(), result,
                 None if went_first is None else int(went_first), my_deck_label, notes),
            )
            return int(cursor.lastrowid)

    def status(self) -> dict:
        self.initialize()
        with self.connect() as connection:
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("cards", "card_printings", "card_keywords", "formats", "leader_stats", "matchup_stats", "usage_stats", "personal_matches")
            }
            counts["unknown_block_printings"] = connection.execute(
                "SELECT COUNT(*) FROM card_printings WHERE block_icon='?'"
            ).fetchone()[0]
            imports = [
                dict(row)
                for row in connection.execute(
                    """SELECT s.name, s.kind, s.url, r.captured_at, r.content_hash,
                    r.item_count, r.status FROM import_runs r LEFT JOIN data_sources s
                    ON s.id=r.source_id ORDER BY r.captured_at DESC LIMIT 10"""
                )
            ]
        return {"database": str(self.path), "counts": counts, "imports": imports}


def validate_deck(
    db: LabDB,
    entries: dict[str, int],
    format_name: str,
    region: str = "EN",
    on_date: str | None = None,
) -> ValidationResult:
    check_date = on_date or date.today().isoformat()
    cards = db.load_cards(entries)
    errors: list[str] = []
    warnings: list[str] = []
    for number, quantity in sorted(entries.items()):
        if quantity <= 0:
            errors.append(f"{number}: quantidade deve ser positiva")
    missing = sorted(set(entries) - set(cards))
    if missing:
        errors.append("Cards ausentes do catálogo: " + ", ".join(missing))

    leaders = [(number, quantity) for number, quantity in entries.items() if cards.get(number, {}).get("category") == "Leader"]
    if len(leaders) != 1 or leaders[0][1] != 1:
        errors.append("Deck deve conter exatamente 1 card Leader com quantidade 1")
        leader = None
    else:
        leader = cards[leaders[0][0]]

    main_total = sum(quantity for number, quantity in entries.items() if cards.get(number, {}).get("category") != "Leader")
    if main_total != 50:
        errors.append(f"Deck principal deve conter 50 cards; encontrado: {main_total}")

    for number, quantity in sorted(entries.items()):
        if quantity > 4 and cards.get(number, {}).get("category") != "Leader":
            errors.append(f"{number}: {quantity} cópias excedem máximo padrão de 4")

    active = db.active_format(format_name, region, check_date)
    allowed_blocks = active["allowed_blocks"]
    for number, card in cards.items():
        blocks = {item["block_icon"] for item in card.get("printings", [])}
        if not blocks:
            blocks = {card["block_icon"]}
        if blocks.isdisjoint(allowed_blocks):
            errors.append(f"{number}: Block Icon {sorted(blocks)} não permitido em {format_name}/{region} em {check_date}")

    if leader is not None:
        if leader["deck_rule_override"]:
            errors.append(
                f"{leader['number']}: regra especial de construção ainda requer revisão manual"
            )
        leader_colors = set(leader["colors"])
        for number, card in cards.items():
            if not set(card["colors"]).issubset(leader_colors):
                errors.append(
                    f"{number}: cores {card['colors']} incompatíveis com líder {leader['number']} {leader['colors']}"
                )

    for number, restriction in active["restrictions"].items():
        quantity = entries.get(number, 0)
        if restriction["kind"] == "banned" and quantity:
            errors.append(f"{number}: card banido")
        elif restriction["kind"] == "restricted" and quantity > restriction["max_copies"]:
            errors.append(f"{number}: máximo permitido é {restriction['max_copies']}")

    for card_a, card_b in active["banned_pairs"]:
        if entries.get(card_a, 0) and entries.get(card_b, 0):
            errors.append(f"Par proibido presente: {card_a} + {card_b}")

    if missing:
        warnings.append("Métricas podem ficar incompletas até catálogo conter todos os cards")
    return ValidationResult(tuple(errors), tuple(warnings))


def analyze_deck(db: LabDB, entries: dict[str, int]) -> dict:
    cards = db.load_cards(entries)
    curve: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    traits: Counter[str] = Counter()
    counter_total = 0
    no_counter = 0
    keywords: Counter[str] = Counter()
    triggers = 0
    for number, quantity in entries.items():
        card = cards.get(number)
        if not card or card["category"] == "Leader":
            continue
        categories[card["category"]] += quantity
        curve[str(card["cost"]) if card["cost"] is not None else "N/A"] += quantity
        counter_total += card["counter"] * quantity
        if card["counter"] == 0:
            no_counter += quantity
        for trait in card["traits"]:
            traits[trait] += quantity
        for fact in card["keywords"]:
            if fact["scope"] == "intrinsic":
                keywords[fact["keyword"]] += quantity
        if card.get("trigger"):
            triggers += quantity
    return {
        "main_deck_cards": sum(categories.values()),
        "categories": dict(sorted(categories.items())),
        "cost_curve": dict(sorted(curve.items(), key=lambda item: (item[0] == "N/A", int(item[0]) if item[0].isdigit() else 0))),
        "counter_total": counter_total,
        "cards_without_counter": no_counter,
        "intrinsic_keywords": dict(keywords.most_common()),
        "trigger_cards": triggers,
        "top_traits": dict(traits.most_common(10)),
        "unknown_cards": sorted(set(entries) - set(cards)),
    }


def search_cards(
    db: LabDB,
    *,
    colors: Iterable[str] = (),
    trait: str | None = None,
    text: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    max_cost: int | None = None,
    min_counter: int | None = None,
    legal_blocks: Iterable[str] = (),
    limit: int = 50,
) -> list[dict]:
    clauses = ["1=1"]
    values: list[object] = []
    requested_colors = list(colors)
    if category:
        clauses.append("c.category=?")
        values.append(category)
    if max_cost is not None:
        clauses.append("c.cost<=?")
        values.append(max_cost)
    if min_counter is not None:
        clauses.append("c.counter>=?")
        values.append(min_counter)
    if text:
        clauses.append("(c.name LIKE ? OR c.effect LIKE ? OR c.trigger LIKE ?)")
        needle = f"%{text}%"
        values.extend((needle, needle, needle))
    if trait:
        clauses.append("EXISTS (SELECT 1 FROM card_traits t WHERE t.card_number=c.number AND t.trait LIKE ?)")
        values.append(f"%{trait}%")
    if keyword:
        clauses.append("EXISTS (SELECT 1 FROM card_keywords k WHERE k.card_number=c.number AND k.keyword=? AND k.scope='intrinsic')")
        values.append(keyword)
    if requested_colors:
        placeholders = ",".join("?" for _ in requested_colors)
        clauses.append(
            f"NOT EXISTS (SELECT 1 FROM card_colors cc WHERE cc.card_number=c.number AND cc.color NOT IN ({placeholders}))"
        )
        values.extend(requested_colors)
    blocks = list(legal_blocks)
    if blocks:
        placeholders = ",".join("?" for _ in blocks)
        clauses.append(
            f"(EXISTS (SELECT 1 FROM card_printings p WHERE p.card_number=c.number AND p.block_icon IN ({placeholders})) "
            f"OR (NOT EXISTS (SELECT 1 FROM card_printings p WHERE p.card_number=c.number) AND c.block_icon IN ({placeholders})))"
        )
        values.extend(blocks + blocks)
    values.append(limit)
    with db.connect() as connection:
        rows = connection.execute(
            f"SELECT c.number FROM cards c WHERE {' AND '.join(clauses)} ORDER BY c.cost, c.number LIMIT ?",
            values,
        ).fetchall()
    cards = db.load_cards(row[0] for row in rows)
    return [cards[row[0]] for row in rows]


def recommend_candidates(
    db: LabDB,
    entries: dict[str, int],
    format_name: str,
    region: str = "EN",
    on_date: str | None = None,
    limit: int = 20,
) -> list[dict]:
    cards = db.load_cards(entries)
    leader = next((card for card in cards.values() if card["category"] == "Leader"), None)
    if leader is None:
        raise ValueError("Deck precisa conter um líder conhecido")
    active = db.active_format(format_name, region, on_date or date.today().isoformat())
    pool = search_cards(
        db, colors=leader["colors"], legal_blocks=active["allowed_blocks"], limit=10_000
    )
    deck_traits = Counter(
        trait
        for number, quantity in entries.items()
        for trait in cards.get(number, {}).get("traits", [])
        for _ in range(quantity)
    )
    top_traits = {trait for trait, _ in deck_traits.most_common(5)}
    with db.connect() as connection:
        usage: dict[str, dict] = {}
        for row in connection.execute(
            """SELECT * FROM usage_stats WHERE leader_number=? AND format_name=?
            ORDER BY captured_at DESC, deck_count DESC, source_name""",
            (leader["number"], format_name),
        ):
            usage.setdefault(row["card_number"], dict(row))
    ranked: list[dict] = []
    for card in pool:
        if card["category"] == "Leader" or card["number"] in entries:
            continue
        reasons: list[str] = []
        score = 0.0
        overlap = top_traits.intersection(card["traits"])
        if overlap:
            score += 3 + len(overlap)
            reasons.append("tipos em comum: " + ", ".join(sorted(overlap)))
        searchable = f"{card['effect']} {card['trigger']}".lower()
        if leader["name"].lower() in searchable:
            score += 5
            reasons.append(f"cita o líder {leader['name']}")
        mentioned_traits = [trait for trait in leader["traits"] if trait.lower() in searchable]
        if mentioned_traits:
            score += 3
            reasons.append("efeito cita: " + ", ".join(mentioned_traits))
        intrinsic = {fact["keyword"] for fact in card["keywords"] if fact["scope"] == "intrinsic"}
        if intrinsic:
            score += min(2, len(intrinsic))
            reasons.append("funções: " + ", ".join(sorted(intrinsic)))
        stat = usage.get(card["number"])
        usage_rate = None
        if stat and stat["deck_count"]:
            usage_rate = stat["decks_with_card"] / stat["deck_count"]
            if usage_rate <= 0.10:
                score += 2
                reasons.append(f"pouco usada nesta amostra ({usage_rate:.1%} de {stat['deck_count']} decks)")
        if score:
            ranked.append(
                {
                    "number": card["number"], "name": card["name"], "score": score,
                    "cost": card["cost"], "counter": card["counter"],
                    "traits": card["traits"], "effect": card["effect"],
                    "trigger": card["trigger"],
                    "usage_rate": usage_rate, "reasons": reasons,
                }
            )
    return sorted(ranked, key=lambda item: (-item["score"], item["usage_rate"] if item["usage_rate"] is not None else 1, item["number"]))[:limit]


def matchup_report(db: LabDB, leader_a: str, leader_b: str) -> dict:
    a, b = leader_a.upper(), leader_b.upper()
    with db.connect() as connection:
        rows = connection.execute(
            """SELECT * FROM matchup_stats WHERE
            (leader_a=? AND leader_b=?) OR (leader_a=? AND leader_b=?)
            ORDER BY captured_at DESC, source_name""",
            (a, b, b, a),
        ).fetchall()
        personal = connection.execute(
            """SELECT result FROM personal_matches WHERE my_leader=? AND opponent_leader=?""",
            (a, b),
        ).fetchall()
    sources = []
    total_games = total_wins = 0
    for row in rows:
        wins = row["wins_a"] if row["leader_a"] == a else row["games"] - row["wins_a"]
        games = row["games"]
        rate = wins / games
        z = 1.96
        center = (rate + z * z / (2 * games)) / (1 + z * z / games)
        margin = z * math.sqrt(rate * (1 - rate) / games + z * z / (4 * games * games)) / (1 + z * z / games)
        sources.append({**dict(row), "wins_for_a": wins, "win_rate_a": rate, "wilson_95": [center - margin, center + margin]})
        total_games += games
        total_wins += wins
    personal_wins = sum(row[0] == "win" for row in personal)
    return {
        "leader_a": a, "leader_b": b, "sources": sources,
        "pooled": None if not total_games else {"games": total_games, "wins_a": total_wins, "win_rate_a": total_wins / total_games},
        "warning": "O agregado combina fontes e só deve ser usado se ambiente, período e formato forem comparáveis." if len(sources) > 1 else None,
        "personal": {"games": len(personal), "wins": personal_wins, "win_rate": personal_wins / len(personal) if personal else None},
    }


def meta_report(db: LabDB, format_name: str, environment: str | None = None) -> dict:
    clauses = ["format_name=?"]
    values: list[object] = [format_name]
    if environment:
        clauses.append("environment=?")
        values.append(environment)
    with db.connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM leader_stats WHERE {' AND '.join(clauses)} ORDER BY captured_at DESC, source_rank, games DESC",
            values,
        ).fetchall()
    latest: dict[tuple[str, str, str, str], dict] = {}
    for row in rows:
        key = (row["source_name"], row["environment"], row["leader_number"], row["sample_kind"])
        if key not in latest:
            item = dict(row)
            item["win_rate"] = item["wins"] / item["games"]
            latest[key] = item
    return {
        "format": format_name,
        "environment_filter": environment,
        "leaders": list(latest.values()),
        "warning": "Ranking e win rate descrevem a amostra e o tipo indicados; não equivalem automaticamente ao meta presencial inteiro.",
    }


def build_context(
    db: LabDB,
    entries: dict[str, int],
    format_name: str,
    region: str = "EN",
    on_date: str | None = None,
    opponent_leader: str | None = None,
) -> str:
    checked = on_date or date.today().isoformat()
    cards = db.load_cards(entries)
    validation = validate_deck(db, entries, format_name, region, checked)
    metrics = analyze_deck(db, entries)
    candidates = recommend_candidates(db, entries, format_name, region, checked)
    leader = next((card for card in cards.values() if card["category"] == "Leader"), None)
    lines = [
        "# Pacote de contexto — One Piece TCG Lab", "",
        f"Data da análise: {checked}", f"Formato/região: {format_name}/{region}",
        f"Legal: {'sim' if validation.valid else 'não'}", "",
        "## Líder", "",
    ]
    if leader:
        lines.extend([
            f"{leader['number']} — {leader['name']}",
            f"Cores: {', '.join(leader['colors'])}; Vida: {leader['life']}; Poder: {leader['power']}",
            f"Tipos: {', '.join(leader['traits'])}", f"Efeito: {leader['effect']}", "",
        ])
    lines.extend(["## Validação", ""])
    lines.extend([f"- ERRO: {item}" for item in validation.errors] or ["- Nenhum erro."])
    lines.extend([f"- AVISO: {item}" for item in validation.warnings])
    lines.extend(["", "## Métricas", "", "```json", json.dumps(metrics, ensure_ascii=False, indent=2), "```", "", "## Deck", ""])
    for number, quantity in sorted(entries.items()):
        card = cards.get(number)
        if card:
            keywords = ", ".join(sorted({fact['keyword'] for fact in card['keywords']})) or "nenhuma"
            lines.append(f"- {quantity}x {number} {card['name']} | custo {card['cost']} | counter {card['counter']} | keywords {keywords} | tipos {', '.join(card['traits'])} | {card['effect']} {card['trigger']}".strip())
        else:
            lines.append(f"- {quantity}x {number} (desconhecida)")
    lines.extend(["", "## Candidatos fora da lista", ""])
    for item in candidates:
        text = " ".join(part for part in (item["effect"], item["trigger"]) if part)
        lines.append(f"- {item['number']} {item['name']} (score {item['score']:.1f}): {'; '.join(item['reasons'])}. Texto: {text}")
    if opponent_leader and leader:
        lines.extend(["", "## Evidência de matchup", "", "```json", json.dumps(matchup_report(db, leader["number"], opponent_leader), ensure_ascii=False, indent=2), "```"])
    lines.extend([
        "", "## Instruções para a IA", "",
        "Não declare uma carta esquecida ou um matchup favorável sem amostra. Diferencie fato, inferência e hipótese de teste. Preserve 1 líder, 50 cartas, cores, limite de cópias, rotação e restrições. Ao sugerir trocas, diga entradas, saídas, objetivo e matchups-alvo.",
    ])
    return "\n".join(lines) + "\n"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
