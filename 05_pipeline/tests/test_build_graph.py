import json, os, shutil, sys, tempfile, unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / '05_pipeline'))
import build_graph

class BuildGraphSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix='build_graph_test_'))
        cls.nodes_csv = REPO_ROOT / '03_graphrag' / 'sanguo_v3_nodes.csv'
        cls.rels_csv = REPO_ROOT / '03_graphrag' / 'sanguo_v3_relationships.csv'
        cls.nodes_json = cls.tmpdir / 'nodes.json'
        cls.rels_json = cls.tmpdir / 'rels.json'
        build_graph.build(nodes_csv=cls.nodes_csv, rels_csv=cls.rels_csv, nodes_out=cls.nodes_json, rels_out=cls.rels_json)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_nodes_json_row_count_matches_csv(self):
        with open(self.nodes_csv, encoding='utf-8') as f:
            csv_rows = sum(1 for _ in f) - 1
        with open(self.nodes_json, encoding='utf-8') as f:
            nodes = json.load(f)
        self.assertEqual(len(nodes), csv_rows)

    def test_rels_json_row_count_matches_csv(self):
        with open(self.rels_csv, encoding='utf-8') as f:
            csv_rows = sum(1 for _ in f) - 1
        with open(self.rels_json, encoding='utf-8') as f:
            rels = json.load(f)
        self.assertEqual(len(rels), csv_rows)

    def test_chapters_field_is_int_array(self):
        with open(self.nodes_json, encoding='utf-8') as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n['name'] == '曹操')
        self.assertIsInstance(cao_cao['chapters'], list)
        for ch in cao_cao['chapters']:
            self.assertIsInstance(ch, int)
        self.assertGreater(len(cao_cao['chapters']), 50)

    def test_aliases_field_is_string_array(self):
        with open(self.nodes_json, encoding='utf-8') as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n['name'] == '曹操')
        self.assertIsInstance(cao_cao['aliases'], list)
        self.assertIn('孟德', cao_cao['aliases'])

    def test_isTrunk_is_bool(self):
        with open(self.nodes_json, encoding='utf-8') as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n['name'] == '曹操')
        self.assertIsInstance(cao_cao['isTrunk'], bool)
        self.assertTrue(cao_cao['isTrunk'])

    def test_numeric_fields_are_numbers(self):
        with open(self.nodes_json, encoding='utf-8') as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n['name'] == '曹操')
        self.assertIsInstance(cao_cao['degree'], int)
        self.assertIsInstance(cao_cao['score'], (int, float))

    def test_rel_chapters_is_int_array(self):
        with open(self.rels_json, encoding='utf-8') as f:
            rels = json.load(f)
        sample = rels[0]
        self.assertIsInstance(sample['chapters'], list)
        if sample['chapters']:
            self.assertIsInstance(sample['chapters'][0], int)

    def test_rel_weight_confidence_are_numeric(self):
        with open(self.rels_json, encoding='utf-8') as f:
            rels = json.load(f)
        sample = rels[0]
        self.assertIsInstance(sample['weight'], (int, float))
        self.assertIsInstance(sample['confidence'], float)

if __name__ == '__main__':
    unittest.main()
