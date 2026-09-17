from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from .lab import (
    LabDB,
    analyze_deck,
    build_context,
    load_json,
    matchup_report,
    meta_report,
    parse_decklist,
    recommend_candidates,
    search_cards,
    validate_deck,
)
from .official import fetch_catalog, parse_cardlist
from .community import fetch_decklists


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="optcg-lab")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init-db")
    init.add_argument("database")

    import_json = commands.add_parser("import-json")
    import_json.add_argument("database")
    import_json.add_argument("dataset")

    import_html = commands.add_parser("import-official-html")
    import_html.add_argument("database")
    import_html.add_argument("html")
    import_html.add_argument("--url", default="https://en.onepiece-cardgame.com/cardlist/")

    sync = commands.add_parser("sync-official")
    sync.add_argument("database")

    usage = commands.add_parser("sync-usage")
    usage.add_argument("database")
    usage.add_argument("hub_url")
    usage.add_argument("leader")
    usage.add_argument("format")
    usage.add_argument("--region", default="EN")
    usage.add_argument("--date", default=date.today().isoformat())

    reindex = commands.add_parser("reindex-keywords")
    reindex.add_argument("database")

    status = commands.add_parser("status")
    status.add_argument("database")

    validate = commands.add_parser("validate")
    validate.add_argument("database")
    validate.add_argument("decklist")
    validate.add_argument("format")
    validate.add_argument("--region", default="EN")
    validate.add_argument("--date")

    analyze = commands.add_parser("analyze")
    analyze.add_argument("database")
    analyze.add_argument("decklist")

    search = commands.add_parser("search")
    search.add_argument("database")
    search.add_argument("--color", action="append", default=[])
    search.add_argument("--trait")
    search.add_argument("--text")
    search.add_argument("--category")
    search.add_argument("--keyword")
    search.add_argument("--max-cost", type=int)
    search.add_argument("--min-counter", type=int)
    search.add_argument("--block", action="append", default=[])
    search.add_argument("--limit", type=int, default=50)

    recommend = commands.add_parser("recommend")
    recommend.add_argument("database")
    recommend.add_argument("decklist")
    recommend.add_argument("format")
    recommend.add_argument("--region", default="EN")
    recommend.add_argument("--date")
    recommend.add_argument("--limit", type=int, default=20)

    context = commands.add_parser("context")
    context.add_argument("database")
    context.add_argument("decklist")
    context.add_argument("format")
    context.add_argument("output")
    context.add_argument("--region", default="EN")
    context.add_argument("--date")
    context.add_argument("--opponent")

    matchup = commands.add_parser("matchup")
    matchup.add_argument("database")
    matchup.add_argument("leader_a")
    matchup.add_argument("leader_b")

    meta = commands.add_parser("meta")
    meta.add_argument("database")
    meta.add_argument("format")
    meta.add_argument("--environment")

    record = commands.add_parser("record-match")
    record.add_argument("database")
    record.add_argument("played_at")
    record.add_argument("my_leader")
    record.add_argument("opponent_leader")
    record.add_argument("result", choices=["win", "loss", "draw"])
    turn = record.add_mutually_exclusive_group()
    turn.add_argument("--first", action="store_true")
    turn.add_argument("--second", action="store_true")
    record.add_argument("--deck-label")
    record.add_argument("--notes")

    args = parser.parse_args()
    db = LabDB(args.database)
    if args.command == "init-db":
        db.initialize()
        return 0
    if args.command == "import-json":
        db.import_dataset(load_json(args.dataset))
        return 0
    if args.command == "import-official-html":
        db.import_dataset(parse_cardlist(Path(args.html).read_text(encoding="utf-8"), args.url))
        return 0
    if args.command == "sync-official":
        dataset = fetch_catalog()
        db.import_dataset(dataset)
        print(json.dumps({"cards": len(dataset["cards"]), "printings": len(dataset["printings"]), "source": dataset["source"]}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "sync-usage":
        fetched = fetch_decklists(args.hub_url)
        accepted = []
        rejected = []
        for item in fetched:
            result = validate_deck(db, item["entries"], args.format, args.region, args.date)
            (accepted if result.valid else rejected).append(item if result.valid else {"url": item["url"], "errors": result.errors})
        if not accepted:
            raise ValueError("Nenhuma lista válida; uso não importado")
        leader_card = db.load_cards([args.leader]).get(args.leader.upper())
        if not leader_card:
            raise ValueError("Líder ausente do catálogo")
        active = db.active_format(args.format, args.region, args.date)
        pool = search_cards(db, colors=leader_card["colors"], legal_blocks=active["allowed_blocks"], limit=10_000)
        presence: Counter[str] = Counter()
        copies: Counter[str] = Counter()
        for item in accepted:
            for number, quantity in item["entries"].items():
                if number != args.leader.upper():
                    presence[number] += 1
                    copies[number] += quantity
        rows = [{
            "source_name": "One Piece Decklists hub", "captured_at": args.date,
            "environment": f"mixed_public_lists:{args.format}", "format_name": args.format,
            "leader_number": args.leader.upper(), "card_number": card["number"],
            "deck_count": len(accepted), "decks_with_card": presence[card["number"]],
            "copies_total": copies[card["number"]], "source_url": args.hub_url,
        } for card in pool if card["category"] != "Leader"]
        db.import_dataset({"usage_stats": rows})
        print(json.dumps({"fetched": len(fetched), "accepted": len(accepted), "rejected": rejected, "cards_profiled": len(rows)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "reindex-keywords":
        print(json.dumps({"keywords": db.reindex_keywords()}))
        return 0
    if args.command == "status":
        print(json.dumps(db.status(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "search":
        print(json.dumps(search_cards(db, colors=args.color, trait=args.trait, text=args.text,
            category=args.category, keyword=args.keyword, max_cost=args.max_cost,
            min_counter=args.min_counter, legal_blocks=args.block, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.command == "matchup":
        print(json.dumps(matchup_report(db, args.leader_a, args.leader_b), ensure_ascii=False, indent=2))
        return 0
    if args.command == "meta":
        print(json.dumps(meta_report(db, args.format, args.environment), ensure_ascii=False, indent=2))
        return 0
    if args.command == "record-match":
        went_first = True if args.first else False if args.second else None
        match_id = db.record_match(args.played_at, args.my_leader, args.opponent_leader,
                                   args.result, went_first, args.deck_label, args.notes)
        print(json.dumps({"match_id": match_id}))
        return 0

    entries = parse_decklist(Path(args.decklist).read_text(encoding="utf-8"))
    if args.command == "analyze":
        print(json.dumps(analyze_deck(db, entries), ensure_ascii=False, indent=2))
        return 0
    if args.command == "recommend":
        print(json.dumps(recommend_candidates(db, entries, args.format, args.region, args.date, args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.command == "context":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_context(db, entries, args.format, args.region, args.date, args.opponent), encoding="utf-8")
        print(output)
        return 0

    result = validate_deck(db, entries, args.format, args.region, args.date)
    print(json.dumps({"valid": result.valid, "errors": result.errors, "warnings": result.warnings}, ensure_ascii=False, indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
