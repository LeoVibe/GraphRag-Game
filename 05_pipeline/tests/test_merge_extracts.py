import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "05_pipeline"))

import merge_extracts  # noqa: E402


class MergeExtractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="merge_extracts_test_"))
        cls.nodes_json = cls.tmpdir / "nodes.json"
        cls.rels_json = cls.tmpdir / "rels.json"
        merge_extracts.build(
            extract_dir=REPO_ROOT / "03_graphrag" / "extract",
            v3_nodes_csv=REPO_ROOT / "03_graphrag" / "sanguo_v3_nodes.csv",
            v3_rels_csv=REPO_ROOT / "03_graphrag" / "sanguo_v3_relationships.csv",
            nodes_out=cls.nodes_json,
            rels_out=cls.rels_json,
        )
        with open(cls.nodes_json, encoding="utf-8") as f:
            cls.nodes = json.load(f)
        with open(cls.rels_json, encoding="utf-8") as f:
            cls.rels = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _character(self, name):
        return next(
            (
                node
                for node in self.nodes
                if node["name"] == name and node["type"] == "character"
            ),
            None,
        )

    def test_zhuge_liang_is_character_with_data(self):
        zhuge_liang = self._character("諸葛亮")
        self.assertIsNotNone(zhuge_liang)
        self.assertEqual(zhuge_liang["type"], "character")
        self.assertEqual(zhuge_liang["kind"], "entity")
        self.assertGreaterEqual(len(zhuge_liang["chapters"]), 5)
        self.assertGreaterEqual(zhuge_liang["degree"], 5)
        self.assertTrue(zhuge_liang["isTrunk"])
        self.assertEqual(zhuge_liang["camp"], "shu")
        self.assertEqual(zhuge_liang["campLabel"], "劉蜀")

    def test_sima_yi_has_chapter_data(self):
        sima_yi = self._character("司馬懿")
        self.assertIsNotNone(sima_yi)
        self.assertGreaterEqual(sima_yi["chapterCount"], 1)
        self.assertEqual(sima_yi["camp"], "wei")

    def test_yu_jin_exists_as_character(self):
        yu_jin = self._character("于禁")
        self.assertIsNotNone(yu_jin)
        self.assertEqual(yu_jin["type"], "character")
        self.assertEqual(yu_jin["camp"], "wei")
        self.assertGreaterEqual(yu_jin["chapterCount"], 5)
        self.assertGreaterEqual(yu_jin["degree"], 5)
        self.assertTrue(yu_jin["isTrunk"])

    def test_liu_bei_still_exists(self):
        liu_bei = self._character("劉備")
        self.assertIsNotNone(liu_bei)
        self.assertGreaterEqual(len(liu_bei["chapters"]), 30)
        self.assertGreaterEqual(liu_bei["degree"], 50)

    def test_all_rels_have_known_category(self):
        known_categories = {
            "command",
            "military",
            "strategy",
            "kinship",
            "place",
            "office",
            "object",
            "story",
            "other",
        }
        for rel in self.rels:
            self.assertIn(rel["category"], known_categories)

    def test_relations_use_unified_ids(self):
        self.assertGreater(len(self.rels), 0)
        sample = self.rels[0]
        self.assertTrue(sample["source"].startswith("entity:"))
        self.assertTrue(sample["target"].startswith("entity:"))


if __name__ == "__main__":
    unittest.main()
