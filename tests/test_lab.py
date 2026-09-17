import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from optcg_lab import (
    LabDB,
    analyze_deck,
    build_context,
    matchup_report,
    meta_report,
    parse_cardlist,
    parse_decklist,
    recommend_candidates,
    search_cards,
    validate_deck,
)
from optcg_lab.community import parse_deck_page


def dataset():
    cards = [
        {
            "number": "TST5-001",
            "name": "Red Leader",
            "category": "Leader",
            "colors": ["Red"],
            "life": 5,
            "power": 5000,
            "counter": 0,
            "block_icon": "5",
            "traits": ["Test Pirates"],
        }
    ]
    for index in range(2, 16):
        cards.append(
            {
                "number": f"TST5-{index:03d}",
                "name": f"Character {index}",
                "category": "Character",
                "colors": ["Red"],
                "cost": index % 5 + 1,
                "power": 5000,
                "counter": 2000 if index % 3 == 0 else 1000,
                "block_icon": "5",
                "traits": ["Test Pirates"],
            }
        )
    cards.append(
        {
            "number": "TST5-099",
            "name": "Blue Intruder",
            "category": "Character",
            "colors": ["Blue"],
            "cost": 1,
            "power": 1000,
            "counter": 1000,
            "block_icon": "5",
            "traits": [],
        }
    )
    cards.append(
        {
            "number": "TST5-016", "name": "Forgotten Blocker", "category": "Character",
            "colors": ["Red"], "cost": 2, "power": 3000, "counter": 1000,
            "block_icon": "5", "traits": ["Test Pirates"],
            "effect": "[Blocker]", "keywords": [{"keyword": "Blocker", "scope": "intrinsic", "evidence": "[Blocker]"}],
        }
    )
    next(card for card in cards if card["number"] == "TST5-015")["block_icon"] = "1"
    return {
        "cards": cards,
        "printings": [{"print_id": "TST5-015_p1", "card_number": "TST5-015", "block_icon": "X"}],
        "formats": [
            {
                "name": "Standard",
                "region": "EN",
                "valid_from": "2026-04-01",
                "allowed_blocks": ["2", "3", "4", "5", "X"],
            }
        ],
        "restrictions": [
            {
                "format_name": "Standard",
                "region": "EN",
                "card_number": "TST5-099",
                "kind": "restricted",
                "max_copies": 1,
            }
        ],
        "banned_pairs": [
            {
                "format_name": "Standard",
                "region": "EN",
                "card_a": "TST5-012",
                "card_b": "TST5-013",
            }
        ],
        "usage_stats": [{
            "source_name": "Fixture", "captured_at": "2026-09-14", "environment": "tournament",
            "format_name": "Standard", "leader_number": "TST5-001", "card_number": "TST5-016",
            "deck_count": 10, "decks_with_card": 1, "copies_total": 2,
        }],
        "matchups": [{
            "source_name": "Fixture", "captured_at": "2026-09-14", "environment": "simulator",
            "format_name": "Standard", "leader_a": "TST5-001", "leader_b": "TST5-100",
            "games": 100, "wins_a": 60,
        }],
        "leader_stats": [{
            "source_name": "Fixture", "captured_at": "2026-09-14", "environment": "simulator",
            "format_name": "Standard", "leader_number": "TST5-001", "games": 100,
            "wins": 60, "source_rank": 1, "sample_kind": "representative_variant",
        }],
    }


def valid_entries():
    entries = {"TST5-001": 1}
    entries.update({f"TST5-{index:03d}": 4 for index in range(2, 14)})
    entries["TST5-014"] = 2
    return entries


class LabTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = LabDB(Path(self.temp.name) / "lab.db")
        self.db.import_dataset(dataset())

    def tearDown(self):
        self.temp.cleanup()

    def test_parse_decklist_accumulates_duplicate_lines(self):
        self.assertEqual(parse_decklist("1xTST5-001\n2 TST5-002\n2xTST5-002"), {"TST5-001": 1, "TST5-002": 4})

    def test_valid_deck(self):
        entries = valid_entries()
        del entries["TST5-012"]
        entries["TST5-014"] = 4
        entries["TST5-015"] = 2
        result = validate_deck(self.db, entries, "Standard", on_date="2026-09-14")
        self.assertTrue(result.valid, result.errors)

    def test_color_copy_restriction_and_pair_errors(self):
        entries = valid_entries()
        entries["TST5-099"] = 2
        result = validate_deck(self.db, entries, "Standard", on_date="2026-09-14")
        message = "\n".join(result.errors)
        self.assertIn("incompatíveis", message)
        self.assertIn("máximo permitido", message)
        self.assertIn("Par proibido", message)

    def test_analysis_counts_curve_and_counter(self):
        metrics = analyze_deck(self.db, valid_entries())
        self.assertEqual(metrics["main_deck_cards"], 50)
        self.assertGreater(metrics["counter_total"], 50_000)
        self.assertEqual(metrics["top_traits"]["Test Pirates"], 50)

    def test_search_recommend_context_and_matchup(self):
        found = search_cards(self.db, colors=["Red"], keyword="Blocker")
        self.assertEqual([card["number"] for card in found], ["TST5-016"])
        candidates = recommend_candidates(self.db, valid_entries(), "Standard", on_date="2026-09-14")
        forgotten = next(item for item in candidates if item["number"] == "TST5-016")
        self.assertIn("pouco usada", " ".join(forgotten["reasons"]))
        context = build_context(self.db, valid_entries(), "Standard", on_date="2026-09-14")
        self.assertIn("Candidatos fora da lista", context)
        report = matchup_report(self.db, "TST5-001", "TST5-100")
        self.assertEqual(report["pooled"]["win_rate_a"], 0.6)

    def test_official_html_parser_distinguishes_intrinsic_and_granted(self):
        html = '''
        <option value="569117">BOOSTER [OP-17]</option>
        <dl class="modalCol" id="OP17-001"><dt><div class="infoCol"><span>OP17-001</span> | <span>L</span> | <span>LEADER</span></div><div class="cardName">Edward.Newgate</div></dt><dd><div class="backCol"><div class="cost"><h3>Life</h3>5</div><div class="attribute"><h3>Attribute</h3><i>Special</i></div><div class="power"><h3>Power</h3>5000</div><div class="counter"><h3>Counter</h3>-</div><div class="color"><h3>Color</h3>Red</div><div class="block"><h3>Block icon</h3>5</div><div class="feature"><h3>Type</h3>The Four Emperors/Whitebeard Pirates</div><div class="text"><h3>Effect</h3>[On Your Opponent's Attack] gain +4000 power.</div><div class="getInfo"><h3>Card Set(s)</h3>OP-17</div></div></dd></dl>
        <dl class="modalCol" id="OP17-012"><dt><div class="infoCol"><span>OP17-012</span> | <span>C</span> | <span>CHARACTER</span></div><div class="cardName">Blenheim</div></dt><dd><div class="backCol"><div class="cost"><h3>Cost</h3>2</div><div class="power"><h3>Power</h3>1000</div><div class="counter"><h3>Counter</h3>1000</div><div class="color"><h3>Color</h3>Red</div><div class="block"><h3>Block icon</h3>5</div><div class="feature"><h3>Type</h3>Whitebeard Pirates</div><div class="text"><h3>Effect</h3>[Blocker]. Another Character gains [Rush].</div></div></dd></dl>
        '''
        parsed = parse_cardlist(html)
        self.assertEqual(len(parsed["cards"]), 2)
        blocker = next(card for card in parsed["cards"] if card["number"] == "OP17-012")
        scopes = {(fact["keyword"], fact["scope"]) for fact in blocker["keywords"]}
        self.assertIn(("Blocker", "intrinsic"), scopes)
        self.assertIn(("Rush", "granted"), scopes)

    def test_personal_match_and_status(self):
        match_id = self.db.record_match(
            "2026-09-14", "TST5-001", "TST5-100", "win", True, "v1", "teste"
        )
        self.assertGreater(match_id, 0)
        report = matchup_report(self.db, "TST5-001", "TST5-100")
        self.assertEqual(report["personal"]["win_rate"], 1.0)
        self.assertEqual(self.db.status()["counts"]["personal_matches"], 1)

    def test_community_deck_parser_uses_text_section_only(self):
        page = '''<div>4x OP99-999 duplicate picture</div><section class="text-deck">
        <span class="qty">1x</span><span class="card-title">Leader</span><span class="muted card-id">TST5-001</span>
        <span class="qty">4x</span><span class="card-title">Card</span><span class="muted card-id">TST5-002</span>
        </section>'''
        self.assertEqual(parse_deck_page(page), {"TST5-001": 1, "TST5-002": 4})

    def test_meta_report_preserves_sample_kind(self):
        report = meta_report(self.db, "Standard", "simulator")
        self.assertEqual(report["leaders"][0]["leader_number"], "TST5-001")
        self.assertEqual(report["leaders"][0]["win_rate"], 0.6)
        self.assertEqual(report["leaders"][0]["sample_kind"], "representative_variant")

    def test_community_deck_parser_accumulates_duplicate_lines(self):
        page = '''<section class="text-deck">
        <span class="qty">2x</span><span class="muted card-id">TST5-002</span>
        <span class="qty">2x</span><span class="muted card-id">TST5-002</span>
        </section>'''
        self.assertEqual(parse_deck_page(page), {"TST5-002": 4})


if __name__ == "__main__":
    unittest.main()
