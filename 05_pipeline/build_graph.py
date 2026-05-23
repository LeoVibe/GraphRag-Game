#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES_CSV = REPO_ROOT / '03_graphrag' / 'sanguo_v3_nodes.csv'
DEFAULT_RELS_CSV = REPO_ROOT / '03_graphrag' / 'sanguo_v3_relationships.csv'
DEFAULT_NODES_OUT = REPO_ROOT / '03_graphrag' / 'nodes.json'
DEFAULT_RELS_OUT = REPO_ROOT / '03_graphrag' / 'rels.json'

def _split_int_list(raw):
    if not raw: return []
    return [int(x) for x in raw.split(';') if x.strip()]

def _split_str_list(raw):
    if not raw: return []
    return [x.strip() for x in raw.split('|') if x.strip()]

def _to_bool(raw):
    return raw.strip().lower() == 'true'

def _to_int(raw, default=0):
    try: return int(raw)
    except: return default

def _to_float(raw, default=0.0):
    try: return float(raw)
    except: return default

def _convert_node(row):
    return {'id': row['id'], 'name': row['name'], 'type': row['type'], 'typeLabel': row['typeLabel'], 'kind': row['kind'], 'camp': row['camp'], 'campLabel': row['campLabel'], 'chapters': _split_int_list(row.get('chapters', '')), 'chapterStart': _to_int(row.get('chapterStart')), 'chapterEnd': _to_int(row.get('chapterEnd')), 'chapterCount': _to_int(row.get('chapterCount')), 'degree': _to_int(row.get('degree')), 'score': _to_float(row.get('score')), 'isTrunk': _to_bool(row.get('isTrunk', '')), 'aliases': _split_str_list(row.get('aliases', '')), 'description': row.get('description', '')}

def _convert_rel(row):
    return {'id': row['id'], 'source': row['source'], 'target': row['target'], 'relationType': row['relationType'], 'category': row['category'], 'categoryLabel': row['categoryLabel'], 'chapters': _split_int_list(row.get('chapters', '')), 'chapterStart': _to_int(row.get('chapterStart')), 'chapterEnd': _to_int(row.get('chapterEnd')), 'weight': _to_float(row.get('weight')), 'confidence': _to_float(row.get('confidence')), 'description': row.get('description', ''), 'kind': row.get('kind', '')}

def build(nodes_csv=DEFAULT_NODES_CSV, rels_csv=DEFAULT_RELS_CSV, nodes_out=DEFAULT_NODES_OUT, rels_out=DEFAULT_RELS_OUT):
    with open(nodes_csv, encoding='utf-8', newline='') as f:
        nodes = [_convert_node(row) for row in csv.DictReader(f)]
    nodes_out.parent.mkdir(parents=True, exist_ok=True)
    with open(nodes_out, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    print(f'wrote {len(nodes)} nodes to {nodes_out}', file=sys.stderr)
    with open(rels_csv, encoding='utf-8', newline='') as f:
        rels = [_convert_rel(row) for row in csv.DictReader(f)]
    with open(rels_out, 'w', encoding='utf-8') as f:
        json.dump(rels, f, ensure_ascii=False, indent=2)
    print(f'wrote {len(rels)} relationships to {rels_out}', file=sys.stderr)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes-csv', type=Path, default=DEFAULT_NODES_CSV)
    parser.add_argument('--rels-csv', type=Path, default=DEFAULT_RELS_CSV)
    parser.add_argument('--nodes-out', type=Path, default=DEFAULT_NODES_OUT)
    parser.add_argument('--rels-out', type=Path, default=DEFAULT_RELS_OUT)
    args = parser.parse_args()
    build(args.nodes_csv, args.rels_csv, args.nodes_out, args.rels_out)

if __name__ == '__main__':
    main()
