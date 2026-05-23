"""Tests for precompute_questions: 個性比例與 traits 預算。"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "05_pipeline"))

import precompute_questions  # noqa: E402


class PrecomputeQuestionsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="precompute_test_"))
        cls.nodes_json = REPO_ROOT / "03_graphrag" / "nodes.json"
        cls.rels_json = REPO_ROOT / "03_graphrag" / "rels.json"
        cls.out_json = cls.tmpdir / "character_personality.json"
        precompute_questions.compute(
            nodes_json=cls.nodes_json,
            rels_json=cls.rels_json,
            output=cls.out_json,
        )
        with open(cls.out_json, encoding="utf-8") as f:
            cls.data = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_output_is_dict_keyed_by_id(self):
        self.assertIsInstance(self.data, dict)
        self.assertIn("entity:character_曹操", self.data)

    def test_each_entry_has_required_fields(self):
        entry = self.data["entity:character_曹操"]
        self.assertIn("id", entry)
        self.assertIn("name", entry)
        self.assertIn("ratios", entry)
        self.assertIn("traits", entry)
        self.assertEqual(entry["name"], "曹操")

    def test_ratios_sum_to_approx_one(self):
        entry = self.data["entity:character_曹操"]
        total = sum(entry["ratios"].values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_cao_cao_has_command_or_strategy_trait(self):
        entry = self.data["entity:character_曹操"]
        self.assertTrue(
            "會算計" in entry["traits"] or "會帶人" in entry["traits"],
            f"曹操 traits 應含 會算計 或 會帶人，實際: {entry['traits']}",
        )

    def test_traits_are_unique(self):
        for entry in self.data.values():
            self.assertEqual(len(entry["traits"]), len(set(entry["traits"])))

    def test_only_character_entities_present(self):
        for entry_id in self.data.keys():
            self.assertIn("character_", entry_id, f"非人物 id 混入: {entry_id}")

    def test_ratios_categories_known_set(self):
        known = {"command", "military", "strategy", "kinship", "office",
                 "place", "story", "object", "other"}
        for entry in self.data.values():
            for cat in entry["ratios"].keys():
                self.assertIn(cat, known, f"未知 category: {cat}")


if __name__ == "__main__":
    unittest.main()
