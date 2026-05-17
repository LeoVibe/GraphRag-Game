#!/usr/bin/env python3
"""Generate a child-friendly single-file Sanguo GraphRAG adventure map."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES_CSV = REPO_ROOT / "graphrag-demo/sanguo_neo4j_v3/import/sanguo_v3_nodes.csv"
DEFAULT_RELS_CSV = REPO_ROOT / "graphrag-demo/sanguo_neo4j_v3/import/sanguo_v3_relationships.csv"
DEFAULT_METADATA = REPO_ROOT / "graphrag-demo/sanguo_neo4j_v3/metadata.json"
DEFAULT_OUTPUT = REPO_ROOT / "graphrag-demo/三國演義探險地圖_v11.html"


CHAPTER_PRESETS = [
    {"id": "all", "label": "全部章節", "shortLabel": "第1-60回", "start": 1, "end": 60, "focus": ""},
    {"id": "ch001_010", "label": "英雄起義", "shortLabel": "1-10", "start": 1, "end": 10, "focus": "桃園結義、黃巾之亂、董卓進京。"},
    {"id": "ch011_020", "label": "群雄角力", "shortLabel": "11-20", "start": 11, "end": 20, "focus": "曹操、呂布、袁術與劉備反覆交手。"},
    {"id": "ch021_030", "label": "官渡前後", "shortLabel": "21-30", "start": 21, "end": 30, "focus": "袁紹與曹操的勢力走向決戰。"},
    {"id": "ch031_040", "label": "荊州伏龍", "shortLabel": "31-40", "start": 31, "end": 40, "focus": "劉備尋找軍師，諸葛亮開始出場。"},
    {"id": "ch041_050", "label": "赤壁鏖兵", "shortLabel": "41-50", "start": 41, "end": 50, "focus": "孫劉合作，用火攻改變三國局勢。"},
    {"id": "ch051_060", "label": "荊南西川", "shortLabel": "51-60", "start": 51, "end": 60, "focus": "三方勢力各自延伸，準備走向三足鼎立。"},
]


CAMP_OVERRIDES: dict[str, tuple[str, str]] = {
    **{name: ("wei", "曹魏") for name in [
        "曹操", "司馬懿", "夏侯惇", "夏侯淵", "曹仁", "曹洪", "許褚", "張遼", "徐晃", "荀彧",
        "程昱", "郭嘉", "典韋", "李典", "于禁", "於禁", "曹丕", "曹植", "樂進", "滿寵", "賈詡",
    ]},
    **{name: ("shu", "劉蜀") for name in [
        "劉備", "關羽", "張飛", "趙雲", "諸葛亮", "龐統", "馬超", "黃忠", "魏延", "法正",
        "孫乾", "糜竺", "關平", "劉封", "廖化", "簡雍", "徐庶",
    ]},
    **{name: ("wu", "東吳") for name in [
        "孫權", "周瑜", "孫策", "孫堅", "魯肅", "黃蓋", "甘寧", "呂蒙", "程普", "太史慈",
        "諸葛瑾", "張昭", "韓當", "周泰", "蔣欽", "徐盛", "丁奉", "陳武",
    ]},
    **{name: ("lords", "群雄") for name in [
        "呂布", "袁紹", "袁術", "董卓", "劉表", "劉璋", "張魯", "陶謙", "公孫瓚", "張角",
        "馬騰", "韓遂", "何進", "李傕", "郭汜",
    ]},
}


ROLE_INTROS = {
    "曹操": "很會用人與判斷局勢的領袖，也常讓人又佩服又害怕。",
    "劉備": "重視仁義與夥伴的人，常靠關羽、張飛與諸葛亮一起突破困難。",
    "關羽": "以義氣與武勇聞名，關係鏈常連到劉備、張飛、曹操與許多戰役。",
    "張飛": "直率勇猛，常在危急時刻跳出來保護劉備。",
    "呂布": "武力極強、關係變化很多的人物，很適合用關係圖看他的選擇。",
    "諸葛亮": "擅長觀察局勢與設計策略，是劉備陣營的重要軍師。",
    "孫權": "繼承江東後要學會判斷局勢，赤壁前的決定影響很大。",
    "周瑜": "東吳重要統帥，赤壁之戰中展現水戰與合作能力。",
    "趙雲": "忠誠又勇敢，長坂坡故事讓他成為很醒目的英雄。",
    "袁紹": "勢力很大，但決策與用人常被拿來和曹操比較。",
    "董卓": "掌握朝廷造成天下震動，也讓群雄開始聯合對抗。",
    "魯肅": "擅長外交與大局判斷，是孫劉合作的重要推手。",
}


TRAITS = {
    "曹操": {"謀略": 5, "領導": 5, "膽識": 4},
    "劉備": {"仁義": 5, "凝聚": 5, "耐心": 4},
    "關羽": {"武勇": 5, "義氣": 5, "判斷": 3},
    "張飛": {"武勇": 5, "膽識": 5, "耐心": 2},
    "呂布": {"武勇": 5, "選擇": 2, "影響": 4},
    "諸葛亮": {"謀略": 5, "觀察": 5, "說服": 4},
    "孫權": {"領導": 4, "判斷": 4, "外交": 4},
    "周瑜": {"統帥": 5, "水戰": 5, "謀略": 4},
    "趙雲": {"武勇": 5, "忠誠": 5, "守護": 5},
    "袁紹": {"資源": 5, "決斷": 2, "聲望": 4},
    "董卓": {"權勢": 5, "威嚇": 5, "人望": 1},
    "魯肅": {"外交": 5, "遠見": 4, "協調": 5},
    "黃蓋": {"勇氣": 5, "忍耐": 4, "計策": 4},
    "馬超": {"武勇": 5, "衝勁": 5, "穩定": 2},
}


KID_CATEGORY_LABELS = {
    "defeat": "勝負轉折",
    "enemy": "對手或交戰",
    "ally": "合作或援助",
    "strategy": "計策或說服",
    "command": "主從或陣營",
    "family": "親族或結義",
    "office": "官職或任命",
    "place": "地點線索",
    "story": "同一段故事",
    "object": "物品線索",
    "other": "其他關係",
}


TYPE_LABELS = {
    "character": "人物",
    "battle": "戰役",
    "event": "故事",
    "faction": "陣營",
    "army": "軍隊",
    "location": "地點",
    "strategy": "策略",
    "object": "物品",
}


def split_ints(value: str) -> list[int]:
    return [int(part) for part in value.split(";") if part.strip()]


def split_pipe(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def parse_int(value: str, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def parse_float(value: str, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def compact_description(value: str, max_chars: int = 220) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def child_intro(name: str, description: str, type_label: str) -> str:
    if name in ROLE_INTROS:
        return ROLE_INTROS[name]
    first = compact_description(description, 96).split("；", 1)[0].strip()
    if first:
        return first
    return f"這是一個可探索的{type_label}節點，可以點開看它連到誰。"


def classify_relationship(row: dict[str, str]) -> tuple[str, str]:
    category = row.get("category", "other")
    relation_type = row.get("relationType", "")
    description = row.get("description", "")
    text = f"{category} {relation_type} {description}"

    if re.search(r"刺殺|斬殺|殺害|殺死|誅殺|處決|斬之|斬首|砍斷|刺死|被殺|殺", text):
        return "defeat", KID_CATEGORY_LABELS["defeat"]
    if category == "kinship" or re.search(r"父子|兄弟|夫妻|義父|義子|結義|婚|母|子|弟|兄", text):
        return "family", KID_CATEGORY_LABELS["family"]
    if category == "strategy" or re.search(r"獻策|建議|進言|設計|謀|計|說服|勸|離間|詐|議", text):
        return "strategy", KID_CATEGORY_LABELS["strategy"]
    if category == "command" or re.search(r"統領|率領|部將|派遣|隸屬|成員|命令|護衛|麾下|帳下|任命", text):
        return "command", KID_CATEGORY_LABELS["command"]
    if category == "military" or re.search(r"攻|擊|戰|敗|破|擒|圍|伏|追|夾攻|單挑|救|火攻", text):
        return "enemy", KID_CATEGORY_LABELS["enemy"]
    if re.search(r"救援|助戰|會合|同盟|聯合|同行|合作|迎接|投奔|輔佐|推薦|結盟|結好", text):
        return "ally", KID_CATEGORY_LABELS["ally"]
    if category == "office":
        return "office", KID_CATEGORY_LABELS["office"]
    if category == "place":
        return "place", KID_CATEGORY_LABELS["place"]
    if category == "object":
        return "object", KID_CATEGORY_LABELS["object"]
    if category == "story" or row.get("kind") == "story_link":
        return "story", KID_CATEGORY_LABELS["story"]
    return "other", KID_CATEGORY_LABELS["other"]


def load_nodes(path: Path) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            chapters = split_ints(row.get("chapters", ""))
            name = row.get("name", "")
            camp, camp_label = CAMP_OVERRIDES.get(name, (row.get("camp", "neutral"), row.get("campLabel", "未分類")))
            node_type = row.get("type", "entity")
            type_label = TYPE_LABELS.get(node_type, row.get("typeLabel", "節點"))
            description = compact_description(row.get("description", ""), 260)
            nodes.append(
                {
                    "id": row["id"],
                    "name": name,
                    "type": node_type,
                    "typeLabel": type_label,
                    "kind": row.get("kind", "entity"),
                    "camp": camp or "neutral",
                    "campLabel": camp_label or "未分類",
                    "chapters": chapters,
                    "chapterStart": parse_int(row.get("chapterStart", "")),
                    "chapterEnd": parse_int(row.get("chapterEnd", "")),
                    "chapterCount": parse_int(row.get("chapterCount", "")),
                    "degree": parse_int(row.get("degree", "")),
                    "score": parse_int(row.get("score", "")),
                    "isTrunk": parse_bool(row.get("isTrunk", "")),
                    "aliases": split_pipe(row.get("aliases", ""))[:12],
                    "description": description,
                    "kidIntro": child_intro(name, description, type_label),
                    "traits": TRAITS.get(name, {}),
                }
            )
    return nodes


def load_relationships(path: Path) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            chapters = split_ints(row.get("chapters", ""))
            kid_category, kid_label = classify_relationship(row)
            relationships.append(
                {
                    "id": row["id"],
                    "source": row.get("source", ""),
                    "target": row.get("target", ""),
                    "relationType": row.get("relationType", "關係"),
                    "category": row.get("category", "other"),
                    "categoryLabel": row.get("categoryLabel", "其他關係"),
                    "kidCategory": kid_category,
                    "kidLabel": kid_label,
                    "chapters": chapters,
                    "chapterStart": parse_int(row.get("chapterStart", "")),
                    "chapterEnd": parse_int(row.get("chapterEnd", "")),
                    "weight": parse_int(row.get("weight", ""), 1),
                    "confidence": round(parse_float(row.get("confidence", ""), 0.0), 3),
                    "description": compact_description(row.get("description", ""), 220),
                    "kind": row.get("kind", "entity_relation"),
                }
            )
    return relationships


def build_payload(nodes_path: Path, rels_path: Path, metadata_path: Path) -> dict[str, Any]:
    nodes = load_nodes(nodes_path)
    relationships = load_relationships(rels_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    category_counts = Counter(rel["kidCategory"] for rel in relationships)
    type_counts = Counter(node["type"] for node in nodes)
    camp_counts = Counter(node["camp"] for node in nodes if node["kind"] == "entity")

    return {
        "version": "v11-compact-controls",
        "title": "三國演義探險地圖",
        "generatedFrom": {
            "nodes": str(nodes_path.relative_to(REPO_ROOT)),
            "relationships": str(rels_path.relative_to(REPO_ROOT)),
            "metadata": str(metadata_path.relative_to(REPO_ROOT)),
        },
        "summary": {
            "nodes": len(nodes),
            "relationships": len(relationships),
            "entityNodes": metadata.get("entity_nodes"),
            "storyNodes": metadata.get("story_nodes"),
            "trunkNodes": metadata.get("trunk_nodes"),
            "chapters": metadata.get("raw_chapters", 60),
            "typeCounts": dict(type_counts),
            "campCounts": dict(camp_counts),
            "kidRelationCounts": dict(category_counts),
        },
        "chapterPresets": CHAPTER_PRESETS,
        "kidCategories": [
            {"id": key, "label": KID_CATEGORY_LABELS[key], "count": category_counts.get(key, 0)}
            for key in ["story", "enemy", "defeat", "ally", "strategy", "command", "family", "place", "office", "object", "other"]
            if category_counts.get(key, 0)
        ],
        "nodes": nodes,
        "relationships": relationships,
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>三國演義探險地圖 v11</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700&family=Noto+Sans+TC:wght@400;500;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <style>
    :root {
      color-scheme: light;
      --wei-bg: #BDD7F0;
      --wei-border: #7AAED4;
      --wei-text: #1A4A72;
      --shu-bg: #B8E8CA;
      --shu-border: #6DC494;
      --shu-text: #145A32;
      --wu-bg: #F4B8C1;
      --wu-border: #E07D8A;
      --wu-text: #7D1A26;
      --lords-bg: #F7D889;
      --lords-border: #D6A838;
      --lords-text: #6E4B00;
      --mixed-bg: #E8DAEF;
      --mixed-border: #B39DCC;
      --mixed-text: #4A2D6B;
      --neutral-bg: #EDE8E1;
      --neutral-border: #C4B8A8;
      --neutral-text: #5A4A3A;
      --link-ally: #4F94C4;
      --link-enemy: #D76675;
      --link-defeat: #B95052;
      --link-strategy: #D3A540;
      --link-command: #7C9D6F;
      --link-family: #A789C8;
      --link-story: #9C927F;
      --link-place: #7CAAA8;
      --bg: #F5FAF7;
      --surface: #FFFDF7;
      --surface-2: #F8FBFF;
      --ink: #24302B;
      --muted: #68756E;
      --line: rgba(58, 78, 68, 0.16);
      --strong-line: rgba(58, 78, 68, 0.28);
      --shadow: 0 18px 45px rgba(39, 61, 52, 0.14);
      --radius: 8px;
      --space-xs: 4px;
      --space-sm: 8px;
      --space-md: 16px;
      --space-lg: 24px;
      --space-xl: 40px;
      --font-title: "Baloo 2", "Noto Sans TC", sans-serif;
      --font-body: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
      --focus: 0 0 0 3px rgba(74, 129, 178, 0.28);
    }

    * { box-sizing: border-box; }

    html, body {
      margin: 0;
      height: 100%;
      color: var(--ink);
      font-family: var(--font-body);
      background:
        linear-gradient(90deg, rgba(122, 174, 212, 0.08) 1px, transparent 1px),
        linear-gradient(0deg, rgba(109, 196, 148, 0.08) 1px, transparent 1px),
        var(--bg);
      background-size: 36px 36px;
      overflow: hidden;
    }

    button, input, select, textarea {
      font: inherit;
    }

    button {
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      color: var(--ink);
      background: #fff;
      cursor: pointer;
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease, box-shadow 140ms ease;
    }

    button:hover { transform: translateY(-1px); border-color: var(--strong-line); }
    button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible { outline: none; box-shadow: var(--focus); }

    .app {
      height: 100dvh;
      display: grid;
      grid-template-rows: 82px minmax(0, 1fr) auto;
    }

    .topbar {
      display: grid;
      grid-template-columns: minmax(280px, 1fr) minmax(440px, 610px) auto;
      gap: var(--space-md);
      align-items: center;
      padding: 12px 16px;
      background: rgba(255, 253, 247, 0.94);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(12px);
      z-index: 6;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .brand-icon {
      width: 50px;
      height: 50px;
      display: grid;
      place-items: center;
      border-radius: 16px;
      background:
        linear-gradient(135deg, rgba(184, 232, 202, 0.82), rgba(189, 215, 240, 0.9) 55%, rgba(244, 184, 193, 0.72));
      border: 2px solid rgba(36, 48, 43, 0.18);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.86), 0 10px 24px rgba(39,61,52,0.12);
      flex: 0 0 auto;
    }

    .brand-icon svg {
      width: 32px;
      height: 32px;
      stroke: #294235;
      fill: none;
      stroke-width: 2.2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .brand h1 {
      margin: 0;
      font-family: var(--font-title);
      font-size: clamp(27px, 3vw, 36px);
      line-height: 1;
      letter-spacing: 0;
    }

    .brand p {
      margin: 2px 0 0;
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .mode-tabs {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      align-items: center;
      gap: 8px;
      padding: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
    }

    .mode-tabs button {
      min-height: 56px;
      border-radius: var(--radius);
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.86);
      color: var(--muted);
      font-weight: 800;
      padding: 8px 10px;
      text-align: left;
      box-shadow: 0 8px 18px rgba(39,61,52,0.05);
    }

    .mode-tabs button.is-active {
      color: var(--wei-text);
      background: linear-gradient(135deg, #FFFFFF, var(--wei-bg));
      border-color: var(--wei-border);
      box-shadow: 0 10px 24px rgba(122,174,212,0.24), inset 0 0 0 1px rgba(255,255,255,0.74);
      transform: translateY(-1px);
    }

    .mode-name {
      display: block;
      font-size: 16px;
      font-weight: 900;
      line-height: 1.12;
    }

    .mode-desc {
      display: block;
      margin-top: 3px;
      font-size: 11px;
      font-weight: 800;
      color: var(--muted);
      line-height: 1.2;
    }

    .top-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .chapter-select {
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      color: var(--ink);
      padding: 0 36px 0 12px;
      font-weight: 700;
      max-width: 230px;
    }

    .icon-btn {
      width: 44px;
      display: grid;
      place-items: center;
      font-weight: 900;
      color: var(--muted);
    }

    .top-actions .icon-btn {
      width: auto;
      min-width: 44px;
      padding: 0 12px;
    }

    .workspace {
      min-height: 0;
      display: grid;
      grid-template-columns: 292px minmax(0, 1fr) 356px;
      gap: 12px;
      padding: 12px;
    }

    .panel {
      min-height: 0;
      background: rgba(255, 253, 247, 0.92);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: 0 12px 28px rgba(39, 61, 52, 0.08);
    }

    .roster, .guide {
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .panel-head {
      padding: 14px 14px 10px;
      border-bottom: 1px solid var(--line);
    }

    .eyebrow {
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0;
    }

    .panel-title {
      margin-top: 2px;
      font-size: 20px;
      font-weight: 900;
      line-height: 1.2;
    }

    .sheet-toggle {
      display: none;
    }

    .roster-controls {
      flex: 0 1 auto;
      min-height: 0;
      max-height: min(46vh, 430px);
      overflow-y: auto;
      overflow-x: hidden;
      overscroll-behavior: contain;
      scrollbar-gutter: stable;
      padding: 12px 14px;
      display: grid;
      gap: 10px;
      border-bottom: 1px solid var(--line);
    }

    .roster-controls::-webkit-scrollbar,
    .roster-list::-webkit-scrollbar,
    .guide-scroll::-webkit-scrollbar {
      width: 10px;
    }

    .roster-controls::-webkit-scrollbar-track,
    .roster-list::-webkit-scrollbar-track,
    .guide-scroll::-webkit-scrollbar-track {
      background: rgba(58,78,68,0.08);
      border-radius: 999px;
    }

    .roster-controls::-webkit-scrollbar-thumb,
    .roster-list::-webkit-scrollbar-thumb,
    .guide-scroll::-webkit-scrollbar-thumb {
      border: 2px solid rgba(255,253,247,0.94);
      border-radius: 999px;
      background: rgba(122,174,212,0.72);
    }

    .starter-panel {
      display: grid;
      gap: 10px;
      align-items: start;
      padding: 12px;
      border: 1px solid rgba(109,196,148,0.34);
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(184,232,202,0.32), rgba(255,255,255,0.82));
    }

    .starter-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .starter-head strong {
      display: block;
      font-size: 15px;
      font-weight: 900;
      line-height: 1.25;
    }

    .starter-head span {
      color: var(--muted);
      font-size: 13px;
      font-weight: 900;
      white-space: nowrap;
    }

    .starter-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .starter-person {
      min-height: 52px;
      display: grid;
      align-content: center;
      gap: 2px;
      text-align: left;
      padding: 8px 10px;
      border-radius: 16px;
      background: #fff;
      box-shadow: 0 8px 16px rgba(39, 61, 52, 0.06);
    }

    .starter-person.is-active {
      box-shadow: var(--focus);
      transform: translateY(-1px);
    }

    .starter-person strong {
      font-size: 16px;
      font-weight: 900;
      line-height: 1.1;
    }

    .starter-person small {
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
      line-height: 1.4;
    }

    .starter-person.camp-wei {
      border-color: var(--wei-border);
      background: linear-gradient(135deg, var(--wei-bg), #fff);
      color: var(--wei-text);
    }

    .starter-person.camp-shu {
      border-color: var(--shu-border);
      background: linear-gradient(135deg, var(--shu-bg), #fff);
      color: var(--shu-text);
    }

    .starter-person.camp-wu {
      border-color: var(--wu-border);
      background: linear-gradient(135deg, var(--wu-bg), #fff);
      color: var(--wu-text);
    }

    .starter-person.camp-lords, .starter-person.camp-mixed {
      border-color: var(--mixed-border);
      background: linear-gradient(135deg, var(--mixed-bg), #fff);
      color: var(--mixed-text);
    }

    .entry-switch {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .entry-switch button {
      min-height: 54px;
      padding: 9px 10px;
      text-align: left;
      background: #fff;
    }

    .entry-switch button.is-active {
      border-color: var(--wei-border);
      background: var(--wei-bg);
      color: var(--wei-text);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.8), 0 8px 18px rgba(122,174,212,0.18);
    }

    .entry-switch strong {
      display: block;
      font-size: 15px;
      line-height: 1.15;
    }

    .entry-switch span {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      line-height: 1.2;
    }

    .field-label, .filter-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 900;
    }

    .camp-filter-panel {
      display: none;
      gap: 8px;
      padding-top: 2px;
    }

    .camp-filter-panel.is-visible {
      display: grid;
    }

    .control-panel {
      display: grid;
      gap: 6px;
    }

    .path-builder-panel {
      display: none;
      gap: 10px;
      padding: 12px;
      border: 1px solid rgba(122,174,212,0.38);
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(189,215,240,0.34), rgba(255,255,255,0.9));
    }

    .path-builder-panel.is-visible {
      display: grid;
    }

    .path-builder-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .path-builder-head strong {
      font-size: 15px;
      font-weight: 900;
      line-height: 1.25;
    }

    .path-builder-head span {
      color: var(--muted);
      font-size: 13px;
      font-weight: 900;
      white-space: nowrap;
    }

    .path-input-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .path-input-grid label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
    }

    .path-input-grid input {
      width: 100%;
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      color: var(--ink);
      padding: 0 10px;
      font-weight: 800;
    }

    .quick-paths {
      display: grid;
      gap: 6px;
    }

    .quick-path-btn {
      min-height: 42px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 7px 10px;
      background: rgba(255,255,255,0.82);
      font-weight: 900;
      text-align: left;
    }

    .quick-path-btn small {
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
      white-space: nowrap;
    }

    .path-builder-actions {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 8px;
    }

    .search-wrap {
      position: relative;
    }

    .battle-search {
      margin-top: 10px;
      display: none;
      gap: 8px;
    }

    .battle-search.is-visible {
      display: grid;
    }

    .search-wrap input, .path-row input, .teacher-row input[type="range"], .thought-box textarea {
      width: 100%;
    }

    .search-wrap input, .path-row input, .thought-box textarea {
      min-height: 46px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      color: var(--ink);
      padding: 0 12px;
    }

    .thought-box textarea {
      min-height: 84px;
      padding: 10px 12px;
      resize: vertical;
    }

    .camp-filters, .category-filters, .density-filters, .relation-preset-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .relation-preset-filters {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 5px;
      width: 100%;
    }

    .chip {
      min-height: 30px;
      border-radius: 999px;
      padding: 0 10px;
      font-size: 13px;
      font-weight: 800;
      color: var(--muted);
      background: #fff;
    }

    .relation-preset-filters .chip {
      min-width: 0;
      min-height: 28px;
      padding: 0 4px;
      font-size: 12px;
      line-height: 1;
      text-align: center;
      border-radius: 12px;
    }

    .chip.is-active { color: var(--ink); border-color: var(--strong-line); }
    .chip.camp-wei.is-active { background: var(--wei-bg); color: var(--wei-text); border-color: var(--wei-border); }
    .chip.camp-shu.is-active { background: var(--shu-bg); color: var(--shu-text); border-color: var(--shu-border); }
    .chip.camp-wu.is-active { background: var(--wu-bg); color: var(--wu-text); border-color: var(--wu-border); }
    .chip.camp-lords.is-active { background: var(--lords-bg); color: var(--lords-text); border-color: var(--lords-border); }
    .chip.camp-others.is-active { background: var(--mixed-bg); color: var(--mixed-text); border-color: var(--mixed-border); }
    .chip.density-chip.is-active { background: var(--wei-bg); color: var(--wei-text); border-color: var(--wei-border); }
    .chip.preset-core.is-active { background: var(--neutral-bg); color: var(--neutral-text); border-color: var(--neutral-border); }
    .chip.preset-conflict.is-active { background: #FCE6E8; color: #7D1A26; border-color: var(--link-defeat); }
    .chip.preset-ally.is-active { background: #E7F4FC; color: #1A4A72; border-color: var(--link-ally); }
    .chip.preset-strategy.is-active { background: #FFF2CC; color: #6E4B00; border-color: var(--link-strategy); }
    .chip.preset-all.is-active { background: var(--mixed-bg); color: var(--mixed-text); border-color: var(--mixed-border); }

    .roster-list {
      overflow: auto;
      padding: 10px;
    }

    .group-block + .group-block { margin-top: 12px; }

    .group-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--muted);
      font-size: 13px;
      font-weight: 900;
      padding: 0 4px 6px;
    }

    .role-btn {
      width: 100%;
      min-height: 48px;
      display: grid;
      grid-template-columns: 12px minmax(0, 1fr) auto;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      margin-bottom: 6px;
      text-align: left;
      background: #fff;
    }

    .role-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--neutral-bg);
      border: 2px solid var(--neutral-border);
    }

    .camp-wei .role-dot { background: var(--wei-bg); border-color: var(--wei-border); }
    .camp-shu .role-dot { background: var(--shu-bg); border-color: var(--shu-border); }
    .camp-wu .role-dot { background: var(--wu-bg); border-color: var(--wu-border); }
    .camp-lords .role-dot { background: var(--lords-bg); border-color: var(--lords-border); }
    .camp-mixed .role-dot { background: var(--mixed-bg); border-color: var(--mixed-border); }

    .role-main {
      min-width: 0;
    }

    .role-name {
      display: block;
      font-size: 16px;
      font-weight: 900;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .role-meta {
      display: block;
      margin-top: 1px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .role-score {
      font-family: var(--font-title);
      font-weight: 800;
      color: var(--muted);
      font-size: 15px;
    }

    .role-btn.is-selected {
      border-color: var(--wei-border);
      box-shadow: var(--focus);
    }

    .map-zone {
      position: relative;
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      overflow: hidden;
      background:
        radial-gradient(circle at 18% 20%, rgba(184, 232, 202, 0.34), transparent 32%),
        radial-gradient(circle at 82% 26%, rgba(189, 215, 240, 0.46), transparent 30%),
        radial-gradient(circle at 72% 80%, rgba(244, 184, 193, 0.34), transparent 30%),
        var(--surface-2);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      contain: layout style paint;
    }

    .map-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 253, 247, 0.72);
      backdrop-filter: blur(10px);
      z-index: 3;
    }

    .map-title {
      min-width: 0;
    }

    .map-title strong {
      display: block;
      font-size: 19px;
      font-weight: 900;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .map-title span {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .map-tools {
      display: flex;
      gap: 8px;
    }

    .map-tools button {
      width: 42px;
      min-height: 42px;
      font-family: var(--font-title);
      font-size: 20px;
      font-weight: 900;
      padding: 0;
      background: rgba(255, 255, 255, 0.86);
    }

    .graph-wrap {
      position: relative;
      min-height: 0;
    }

    svg#graph {
      display: block;
      width: 100%;
      height: 100%;
    }

    .hint {
      position: absolute;
      left: 50%;
      top: 18px;
      transform: translateX(-50%);
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(36, 48, 43, 0.9);
      color: white;
      font-weight: 800;
      font-size: 14px;
      pointer-events: none;
      opacity: 0;
      animation: hintPulse 3.2s ease 0.4s 1;
      z-index: 5;
    }

    @keyframes hintPulse {
      0%, 100% { opacity: 0; transform: translateX(-50%) translateY(-8px); }
      16%, 82% { opacity: 1; transform: translateX(-50%) translateY(0); }
    }

    .link {
      fill: none;
      stroke: var(--link-story);
      stroke-opacity: 0.32;
      stroke-width: 1.7;
      transition: stroke-opacity 120ms ease, stroke-width 120ms ease;
    }

    .link.cat-ally { stroke: var(--link-ally); }
    .link.cat-enemy { stroke: var(--link-enemy); }
    .link.cat-defeat { stroke: var(--link-defeat); }
    .link.cat-strategy { stroke: var(--link-strategy); stroke-dasharray: 6 4; }
    .link.cat-command { stroke: var(--link-command); }
    .link.cat-family { stroke: var(--link-family); stroke-dasharray: 2 5; }
    .link.cat-place { stroke: var(--link-place); stroke-dasharray: 5 5; }
    .link.is-highlighted { stroke-opacity: 0.94; stroke-width: 3.4; }
    .link.is-dim { stroke-opacity: 0.08; }

    .node {
      cursor: pointer;
      will-change: transform;
    }

    .node-shape {
      stroke-width: 2.5px;
      filter: drop-shadow(0 8px 12px rgba(48, 61, 54, 0.14));
      transition: transform 150ms ease, stroke-width 150ms ease;
    }

    .node:hover .node-shape {
      stroke-width: 3.2px;
    }

    .node text {
      pointer-events: none;
      text-anchor: middle;
      dominant-baseline: middle;
      font-family: var(--font-body);
      font-weight: 900;
      letter-spacing: 0;
      paint-order: stroke;
      stroke: rgba(255, 253, 247, 0.94);
      stroke-width: 4px;
      stroke-linejoin: round;
      fill: #22342c;
    }

    .node.camp-wei .node-shape { fill: var(--wei-bg); stroke: var(--wei-border); }
    .node.camp-shu .node-shape { fill: var(--shu-bg); stroke: var(--shu-border); }
    .node.camp-wu .node-shape { fill: var(--wu-bg); stroke: var(--wu-border); }
    .node.camp-lords .node-shape { fill: var(--lords-bg); stroke: var(--lords-border); }
    .node.camp-mixed .node-shape { fill: var(--mixed-bg); stroke: var(--mixed-border); }
    .node.camp-neutral .node-shape { fill: var(--neutral-bg); stroke: var(--neutral-border); }
    .node.type-event .node-shape, .node.type-battle .node-shape {
      fill: rgba(255, 253, 247, 0.96);
      stroke: var(--neutral-border);
      stroke-dasharray: 6 4;
    }
    .node.is-selected .node-shape {
      stroke-width: 4px;
      filter: drop-shadow(0 0 0 rgba(0,0,0,0)) drop-shadow(0 10px 20px rgba(74, 129, 178, 0.26));
    }
    .node.is-dim {
      opacity: 0.24;
    }

    .guide-scroll {
      min-height: 0;
      overflow: auto;
      padding: 12px;
      display: grid;
      gap: 12px;
      align-content: start;
    }

    .info-card {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      padding: 14px;
    }

    .info-card h2, .info-card h3 {
      margin: 0;
      font-size: 18px;
      line-height: 1.25;
    }

    .info-card p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
    }

    .mission-list, .relation-groups, .event-list, .path-result {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }

    .mission {
      display: grid;
      grid-template-columns: 26px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      padding: 10px;
      border-radius: var(--radius);
      background: #F7FAFF;
      border: 1px solid rgba(122, 174, 212, 0.28);
    }

    .mission-num {
      width: 26px;
      height: 26px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: var(--wei-bg);
      color: var(--wei-text);
      font-family: var(--font-title);
      font-weight: 900;
    }

    .mission strong, .relation-name {
      display: block;
      font-size: 14px;
      font-weight: 900;
    }

    .mission span, .relation-desc, .event-meta {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .relation-section {
      --relation-bg: #F3F5F1;
      --relation-border: var(--strong-line);
      --relation-text: var(--ink);
      --relation-soft: rgba(58, 78, 68, 0.07);
      border: 1px solid var(--relation-border);
      border-left: 6px solid var(--relation-border);
      border-radius: var(--radius);
      overflow: hidden;
      background: #fff;
      box-shadow: 0 8px 18px rgba(39, 61, 52, 0.06);
    }

    .relation-section summary {
      min-height: 50px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      background: linear-gradient(135deg, var(--relation-bg), #fff);
      color: var(--relation-text);
      font-weight: 900;
      cursor: pointer;
      list-style: none;
    }

    .relation-section summary::-webkit-details-marker { display: none; }

    .relation-title {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
      line-height: 1.2;
    }

    .relation-title::before {
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--relation-border);
      box-shadow: 0 0 0 4px rgba(255,255,255,0.72);
    }

    .relation-count {
      min-width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      border: 1px solid var(--relation-border);
      background: rgba(255,255,255,0.82);
      color: var(--relation-text);
      font-family: var(--font-title);
      font-size: 14px;
      font-weight: 900;
    }

    .relation-items {
      display: grid;
      gap: 8px;
      padding: 10px;
      background: var(--relation-soft);
    }

    .relation-item, .event-item, .path-step {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #FFFDF7;
      padding: 9px 10px;
    }

    .relation-item button, .event-item button, .path-step button {
      min-height: auto;
      border: 0;
      background: transparent;
      padding: 0;
      text-align: left;
      font-weight: 900;
      color: var(--relation-text, var(--ink));
    }

    .relation-section.cat-defeat {
      --relation-bg: #FCE6E8;
      --relation-border: var(--link-defeat);
      --relation-text: #7D1A26;
      --relation-soft: rgba(185,80,82,0.08);
    }

    .relation-section.cat-enemy {
      --relation-bg: #FDECEF;
      --relation-border: var(--link-enemy);
      --relation-text: #7D1A26;
      --relation-soft: rgba(215,102,117,0.08);
    }

    .relation-section.cat-ally {
      --relation-bg: #E7F4FC;
      --relation-border: var(--link-ally);
      --relation-text: #1A4A72;
      --relation-soft: rgba(79,148,196,0.08);
    }

    .relation-section.cat-strategy {
      --relation-bg: #FFF2CC;
      --relation-border: var(--link-strategy);
      --relation-text: #6E4B00;
      --relation-soft: rgba(211,165,64,0.10);
    }

    .relation-section.cat-command {
      --relation-bg: #E7F3DD;
      --relation-border: var(--link-command);
      --relation-text: #345A2C;
      --relation-soft: rgba(124,157,111,0.10);
    }

    .relation-section.cat-family {
      --relation-bg: #F1E8F8;
      --relation-border: var(--link-family);
      --relation-text: #4A2D6B;
      --relation-soft: rgba(167,137,200,0.10);
    }

    .relation-section.cat-story {
      --relation-bg: #F1EEE6;
      --relation-border: var(--link-story);
      --relation-text: #5A4A3A;
      --relation-soft: rgba(156,146,127,0.10);
    }

    .relation-section.cat-place {
      --relation-bg: #E3F2F1;
      --relation-border: var(--link-place);
      --relation-text: #315F5E;
      --relation-soft: rgba(124,170,168,0.10);
    }

    .relation-section.cat-office, .relation-section.cat-object, .relation-section.cat-other {
      --relation-bg: #F3F5F1;
      --relation-border: var(--neutral-border);
      --relation-text: var(--neutral-text);
      --relation-soft: rgba(196,184,168,0.10);
    }

    .path-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }

    .path-actions {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      margin-top: 8px;
    }

    .path-result-card {
      display: none;
    }

    .path-result-card.is-visible {
      display: block;
    }

    .path-overview {
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid rgba(122,174,212,0.38);
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(189,215,240,0.34), rgba(255,255,255,0.96));
    }

    .path-overview strong {
      font-size: 16px;
      font-weight: 900;
      line-height: 1.25;
    }

    .path-overview span {
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      line-height: 1.45;
    }

    .path-route {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 7px;
    }

    .path-node-pill {
      min-height: 34px;
      border-radius: 999px;
      padding: 0 10px;
      font-size: 13px;
      font-weight: 900;
      background: #fff;
      border-color: var(--wei-border);
      color: var(--wei-text);
    }

    .path-arrow {
      color: var(--muted);
      font-weight: 900;
    }

    .path-evidence {
      --path-color: var(--link-story);
      display: grid;
      gap: 10px;
      border: 1px solid var(--line);
      border-left: 6px solid var(--path-color);
      border-radius: var(--radius);
      background: #FFFDF7;
      padding: 12px;
      box-shadow: 0 8px 18px rgba(39,61,52,0.06);
    }

    .path-evidence.cat-ally { --path-color: var(--link-ally); }
    .path-evidence.cat-enemy { --path-color: var(--link-enemy); }
    .path-evidence.cat-defeat { --path-color: var(--link-defeat); }
    .path-evidence.cat-strategy { --path-color: var(--link-strategy); }
    .path-evidence.cat-command { --path-color: var(--link-command); }
    .path-evidence.cat-family { --path-color: var(--link-family); }
    .path-evidence.cat-story { --path-color: var(--link-story); }

    .path-evidence-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }

    .path-evidence-title {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    .path-evidence-title strong {
      font-size: 15px;
      font-weight: 900;
      line-height: 1.25;
    }

    .path-evidence-title span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
      line-height: 1.35;
    }

    .path-badge {
      flex: 0 0 auto;
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 0 9px;
      color: #fff;
      background: var(--path-color);
      font-size: 12px;
      font-weight: 900;
      white-space: nowrap;
    }

    .path-desc {
      margin: 0;
      color: var(--ink);
      font-size: 14px;
      line-height: 1.55;
    }

    .path-evidence-group {
      display: grid;
      gap: 6px;
    }

    .path-evidence-group label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
    }

    .path-chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .path-chip {
      min-height: 30px;
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      padding: 0 9px;
      font-size: 12px;
      font-weight: 900;
    }

    .primary-btn {
      background: var(--shu-bg);
      border-color: var(--shu-border);
      color: var(--shu-text);
      font-weight: 900;
    }

    .secondary-btn {
      background: #fff;
      font-weight: 900;
    }

    .teacher-panel {
      display: none;
    }

    .teacher-panel.is-open {
      display: block;
    }

    .teacher-row {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }

    .teacher-row label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 900;
    }

    .check-list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }

    .check-list label {
      min-height: 38px;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 9px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      font-size: 13px;
      font-weight: 800;
    }

    .story-card {
      max-height: 236px;
      display: grid;
      grid-template-columns: 1.05fr 1fr;
      gap: 12px;
      padding: 12px;
      border-top: 1px solid var(--line);
      background: rgba(255, 253, 247, 0.96);
      box-shadow: 0 -18px 38px rgba(39, 61, 52, 0.1);
      z-index: 5;
      overflow: hidden;
    }

    .story-section {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      padding: 12px;
      overflow: auto;
    }

    .selected-head {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .selected-badge {
      width: 44px;
      height: 44px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      border: 2px solid var(--neutral-border);
      background: var(--neutral-bg);
      font-family: var(--font-title);
      font-size: 22px;
      font-weight: 900;
      flex: 0 0 auto;
    }

    .selected-badge.camp-wei { background: var(--wei-bg); border-color: var(--wei-border); color: var(--wei-text); }
    .selected-badge.camp-shu { background: var(--shu-bg); border-color: var(--shu-border); color: var(--shu-text); }
    .selected-badge.camp-wu { background: var(--wu-bg); border-color: var(--wu-border); color: var(--wu-text); }
    .selected-badge.camp-lords { background: var(--lords-bg); border-color: var(--lords-border); color: var(--lords-text); }
    .selected-badge.camp-mixed { background: var(--mixed-bg); border-color: var(--mixed-border); color: var(--mixed-text); }

    .selected-title {
      min-width: 0;
    }

    .selected-title h2 {
      margin: 0;
      font-size: 22px;
      line-height: 1.1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .selected-title span {
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
    }

    .intro {
      margin: 10px 0 0;
      font-size: 15px;
      line-height: 1.55;
    }

    .trait-list {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }

    .trait {
      display: grid;
      grid-template-columns: 58px 1fr auto;
      gap: 8px;
      align-items: center;
      font-size: 13px;
      font-weight: 900;
    }

    .trait-bar {
      height: 10px;
      border-radius: 999px;
      background: #edf2ef;
      overflow: hidden;
    }

    .trait-bar i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--shu-border), var(--wei-border));
    }

    .mini-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }

    .mini-tag {
      display: inline-flex;
      align-items: center;
      min-height: 32px;
      padding: 0 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      background: #fff;
    }

    .selected-actions {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      margin-top: 10px;
    }

    .thought-trigger {
      min-width: 108px;
      min-height: 42px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      padding: 0 12px;
      background: var(--mixed-bg);
      border-color: var(--mixed-border);
      color: var(--mixed-text);
      font-weight: 900;
      white-space: nowrap;
    }

    .thought-trigger svg {
      width: 18px;
      height: 18px;
      stroke: currentColor;
      fill: none;
      stroke-width: 2.3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .thinking-prompts {
      display: grid;
      gap: 8px;
    }

    .thinking-card {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      padding: 10px;
    }

    .thinking-card strong {
      display: block;
      font-size: 14px;
      font-weight: 900;
    }

    .thinking-card span {
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .drawer-scrim {
      position: fixed;
      inset: 0;
      background: rgba(36, 48, 43, 0.18);
      opacity: 0;
      pointer-events: none;
      transition: opacity 180ms ease;
      z-index: 30;
    }

    .drawer-scrim.is-open {
      opacity: 1;
      pointer-events: auto;
    }

    .thought-drawer,
    .settings-drawer {
      position: fixed;
      top: 0;
      right: 0;
      width: min(420px, calc(100vw - 28px));
      height: 100dvh;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      background: rgba(255, 253, 247, 0.98);
      border-left: 1px solid var(--line);
      box-shadow: -28px 0 58px rgba(39, 61, 52, 0.18);
      transform: translateX(105%);
      transition: transform 220ms ease;
      z-index: 31;
    }

    .thought-drawer.is-open,
    .settings-drawer.is-open {
      transform: translateX(0);
    }

    .settings-drawer {
      width: min(440px, calc(100vw - 28px));
    }

    .settings-section {
      display: grid;
      gap: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
    }

    .settings-section h3 {
      margin: 0;
      font-size: 17px;
      line-height: 1.2;
    }

    .settings-note {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      font-weight: 700;
    }

    .segmented-options {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .segmented-options.two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .segmented-options button {
      min-height: 46px;
      display: grid;
      place-items: center;
      padding: 6px 8px;
      font-weight: 900;
    }

    .segmented-options button.is-active {
      color: var(--wei-text);
      background: var(--wei-bg);
      border-color: var(--wei-border);
      box-shadow: var(--focus);
    }

    body.font-small .intro,
    body.font-small .relation-desc,
    body.font-small .event-meta,
    body.font-small .role-meta,
    body.font-small .thinking-card span,
    body.font-small .settings-note {
      font-size: 12px;
      line-height: 1.46;
    }

    body.font-small .role-name,
    body.font-small .relation-title,
    body.font-small .info-card h2,
    body.font-small .panel-title {
      font-size: 16px;
    }

    body.font-small .field-label,
    body.font-small .filter-label,
    body.font-small .starter-head strong,
    body.font-small .path-builder-head strong {
      font-size: 12px;
    }

    body.font-small .map-title strong,
    body.font-small .selected-title h2 {
      font-size: 18px;
    }

    body.font-large .intro,
    body.font-large .relation-desc,
    body.font-large .event-meta,
    body.font-large .role-meta,
    body.font-large .thinking-card span,
    body.font-large .settings-note {
      font-size: 18px;
      line-height: 1.7;
    }

    body.font-large .role-name,
    body.font-large .relation-title,
    body.font-large .info-card h2,
    body.font-large .panel-title {
      font-size: 22px;
    }

    body.font-large .field-label,
    body.font-large .filter-label,
    body.font-large .starter-head strong,
    body.font-large .path-builder-head strong {
      font-size: 16px;
    }

    body.font-large .map-title strong,
    body.font-large .selected-title h2 {
      font-size: 24px;
    }

    body.style-clean .hint {
      display: none;
    }

    body.style-clean .link {
      stroke-opacity: 0.22;
    }

    body.style-clean .link.is-highlighted {
      stroke-opacity: 0.88;
    }

    body.style-reading .map-zone {
      background: #F8FBFF;
    }

    body.style-reading .panel,
    body.style-reading .story-card,
    body.style-reading .info-card,
    body.style-reading .story-section {
      background: #FFFFFF;
    }

    body.style-reading .node text {
      stroke-width: 5px;
    }

    .share-toast {
      position: fixed;
      left: 50%;
      bottom: 18px;
      z-index: 40;
      max-width: min(360px, calc(100vw - 32px));
      padding: 11px 14px;
      border-radius: 999px;
      color: #fff;
      background: rgba(36, 48, 43, 0.92);
      font-size: 14px;
      font-weight: 900;
      box-shadow: 0 14px 34px rgba(39,61,52,0.2);
      opacity: 0;
      pointer-events: none;
      transform: translate(-50%, 12px);
      transition: opacity 180ms ease, transform 180ms ease;
    }

    .share-toast.is-visible {
      opacity: 1;
      transform: translate(-50%, 0);
    }

    .drawer-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 18px;
      border-bottom: 1px solid var(--line);
    }

    .drawer-head h2 {
      margin: 0;
      font-size: 22px;
      line-height: 1.2;
    }

    .drawer-body {
      display: grid;
      gap: 8px;
      align-content: start;
      padding: 18px;
      overflow: auto;
    }

    .thought-box {
      display: grid;
      gap: 12px;
    }

    .thought-box .mini-tags {
      margin-top: 0;
    }

    .empty-state {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
      padding: 10px;
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      background: rgba(255,255,255,0.6);
    }

    .mobile-mode-nav {
      display: none;
    }

    @media (max-width: 1180px) {
      .workspace { grid-template-columns: 250px minmax(0, 1fr); }
      .guide { display: none; }
      .story-card { grid-template-columns: 1fr 1fr; max-height: 260px; }
    }

    @media (max-width: 780px) {
      html, body {
        height: 100%;
        overflow: hidden;
      }

      button {
        min-height: 48px;
        touch-action: manipulation;
      }

      .app {
        height: 100dvh;
        min-height: 0;
        grid-template-rows: 128px minmax(0, 1fr) 0;
        width: 100vw;
        overflow: hidden;
      }

      .topbar {
        grid-template-columns: minmax(0, 1fr) auto;
        grid-template-areas:
          "brand actions"
          "modes modes";
        gap: 8px;
        padding: 7px 10px;
        width: 100vw;
        max-width: 100vw;
        overflow: hidden;
        align-content: center;
      }

      .brand {
        grid-area: brand;
        gap: 8px;
      }

      .brand-icon {
        width: 38px;
        height: 38px;
        border-radius: 13px;
      }

      .brand-icon svg {
        width: 24px;
        height: 24px;
      }

      .brand h1 {
        font-size: 23px;
      }

      .brand p {
        display: none;
      }

      .mode-tabs {
        grid-area: modes;
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 6px;
        width: min(calc(100vw - 20px), 370px);
        max-width: calc(100vw - 20px);
        justify-self: start;
        overflow: hidden;
      }

      .mode-tabs button {
        min-width: 0;
        min-height: 46px;
        display: grid;
        place-items: center;
        align-content: center;
        padding: 5px 4px;
        text-align: center;
        border-radius: 14px;
        box-shadow: 0 6px 14px rgba(39,61,52,0.045);
      }

      .mode-name {
        font-size: 14px;
        line-height: 1.08;
        text-align: center;
      }

      .mode-desc {
        margin-top: 2px;
        font-size: 10px;
        line-height: 1.08;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .top-actions {
        grid-area: actions;
        justify-content: flex-end;
        gap: 6px;
      }

      #shareView {
        display: none;
      }

      .chapter-select {
        max-width: 112px;
        min-height: 40px;
        padding-left: 10px;
        padding-right: 30px;
        font-size: 14px;
        font-weight: 900;
      }

      .icon-btn {
        width: 38px;
        min-height: 40px;
      }

      .top-actions .icon-btn {
        width: auto;
        min-width: 44px;
        padding: 0 8px;
        font-size: 13px;
      }

      .workspace {
        position: relative;
        display: block;
        height: calc(100dvh - 128px - 66px);
        min-height: 0;
        padding: 0;
        overflow: hidden;
      }

      .map-zone {
        height: 100%;
        min-height: 0;
        border-left: 0;
        border-right: 0;
        border-radius: 0;
      }

      .map-head {
        padding: 8px 10px;
        gap: 8px;
      }

      .map-title strong {
        font-size: 17px;
      }

      .map-tools {
        gap: 6px;
      }

      .map-tools button {
        width: 42px;
        min-height: 42px;
      }

      .graph-wrap {
        min-height: 0;
      }

      .hint {
        top: 10px;
        max-width: calc(100vw - 24px);
        padding: 8px 11px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 13px;
      }

      .mobile-mode-nav {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 30;
        max-width: 100vw;
        overflow: hidden;
        height: calc(66px + env(safe-area-inset-bottom));
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 4px;
        padding: 6px 6px calc(6px + env(safe-area-inset-bottom));
        border-top: 1px solid var(--line);
        background: rgba(255, 253, 247, 0.97);
        backdrop-filter: blur(14px);
        box-shadow: 0 -12px 30px rgba(39, 61, 52, 0.12);
      }

      .mobile-mode-nav button {
        min-width: 0;
        width: 100%;
        min-height: 52px;
        display: grid;
        place-items: center;
        align-content: center;
        gap: 0;
        padding: 4px 2px;
        border-radius: 14px;
        background: rgba(255,255,255,0.86);
        font-weight: 900;
      }

      .mobile-mode-nav span {
        font-size: 14px;
        line-height: 1.12;
      }

      .mobile-mode-nav small {
        margin-top: 2px;
        color: var(--muted);
        font-size: 10px;
        font-weight: 900;
        line-height: 1.05;
      }

      .mobile-mode-nav button.is-active {
        color: var(--wei-text);
        border-color: var(--wei-border);
        background: linear-gradient(135deg, #fff, var(--wei-bg));
        box-shadow: 0 8px 18px rgba(122,174,212,0.2);
      }

      .roster {
        position: fixed;
        left: 8px;
        right: 8px;
        bottom: calc(66px + env(safe-area-inset-bottom));
        height: 54dvh;
        max-height: none;
        z-index: 22;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        transform: translateY(calc(100% - 78px));
        transition: transform 220ms ease, height 220ms ease, opacity 160ms ease;
        box-shadow: 0 -18px 42px rgba(39, 61, 52, 0.18);
      }

      body.mobile-sheet-half .roster,
      body.mobile-sheet-full .roster {
        transform: translateY(0);
        height: min(76dvh, calc(100dvh - 158px));
      }

      body.mobile-notebook .roster {
        opacity: 0;
        pointer-events: none;
      }

      .roster .panel-head,
      .guide .panel-head {
        flex: 0 0 auto;
        position: relative;
        cursor: pointer;
        min-height: 76px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 22px 12px 10px;
      }

      .roster .panel-head::before,
      .guide .panel-head::before {
        content: "";
        position: absolute;
        top: 8px;
        left: 50%;
        width: 42px;
        height: 5px;
        border-radius: 999px;
        background: var(--strong-line);
        transform: translateX(-50%);
      }

      .roster .panel-head::after {
        content: "開啟篩選";
        position: absolute;
        right: 12px;
        top: 26px;
        min-height: 38px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        border: 1px solid rgba(122,174,212,0.38);
        background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(189,215,240,0.62));
        color: var(--wei-text);
        padding: 0 12px;
        font-size: 12px;
        font-weight: 900;
        box-shadow: 0 6px 14px rgba(39,61,52,0.08);
        pointer-events: none;
      }

      body.mobile-sheet-full .roster .panel-head::after {
        content: "收合";
      }

      .sheet-toggle {
        min-height: 38px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        position: absolute;
        right: 12px;
        top: 26px;
        z-index: 4;
        width: 88px;
        opacity: 0;
        border-radius: 999px;
        border: 1px solid rgba(122,174,212,0.38);
        background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(189,215,240,0.62));
        color: var(--wei-text);
        padding: 0 12px;
        font-size: 12px;
        font-weight: 900;
        box-shadow: 0 6px 14px rgba(39,61,52,0.08);
      }

      .panel-title {
        font-size: 18px;
      }

      .roster .panel-title {
        max-width: calc(100% - 112px);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .roster-controls {
        flex: 1 1 auto;
        min-height: 0;
        max-height: none;
        overflow-y: auto;
        overflow-x: hidden;
        overscroll-behavior: contain;
        -webkit-overflow-scrolling: touch;
        scrollbar-gutter: stable;
        padding: 10px 12px 84px 10px;
        gap: 10px;
        border-bottom: 0;
      }

      .roster-controls::-webkit-scrollbar,
      .roster-list::-webkit-scrollbar,
      .guide-scroll::-webkit-scrollbar {
        width: 9px;
      }

      .roster-controls::-webkit-scrollbar-track,
      .roster-list::-webkit-scrollbar-track,
      .guide-scroll::-webkit-scrollbar-track {
        background: rgba(58,78,68,0.08);
        border-radius: 999px;
      }

      .roster-controls::-webkit-scrollbar-thumb,
      .roster-list::-webkit-scrollbar-thumb,
      .guide-scroll::-webkit-scrollbar-thumb {
        border: 2px solid rgba(255,253,247,0.94);
        border-radius: 999px;
        background: rgba(122,174,212,0.72);
      }

      .starter-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 7px;
      }

      .starter-person {
        min-height: 50px;
        padding: 8px;
        border-radius: 14px;
      }

      .starter-person strong {
        font-size: 15px;
      }

      .starter-person small {
        font-size: 10px;
      }

      .path-input-grid {
        grid-template-columns: 1fr;
      }

      .path-builder-actions {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .camp-filters,
      .density-filters {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 6px;
      }

      .relation-preset-filters {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 5px;
      }

      .camp-filters {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .chip {
        min-height: 34px;
        padding: 0 6px;
        font-size: 12px;
        border-radius: 14px;
      }

      .relation-preset-filters .chip {
        min-height: 30px;
        padding: 0 2px;
        font-size: 11px;
        border-radius: 11px;
      }

      .search-wrap input,
      .path-input-grid input {
        min-height: 48px;
      }

      .roster-list {
        flex: 0 0 auto;
        max-height: 30dvh;
        overflow-y: auto;
        overscroll-behavior: contain;
        -webkit-overflow-scrolling: touch;
        scrollbar-gutter: stable;
        padding: 8px 12px 18px 8px;
        border-top: 1px solid var(--line);
      }

      .roster-list:empty {
        display: none;
      }

      body.mobile-sheet-full .roster-list {
        max-height: 34dvh;
      }

      .role-btn {
        min-height: 54px;
        margin-bottom: 7px;
      }

      .role-meta {
        white-space: normal;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
      }

      .guide {
        display: none;
      }

      body.mobile-notebook .guide {
        position: fixed;
        left: 8px;
        right: 8px;
        bottom: calc(66px + env(safe-area-inset-bottom));
        height: 82dvh;
        z-index: 24;
        display: flex;
        max-height: none;
        overflow: hidden;
        box-shadow: 0 -18px 42px rgba(39, 61, 52, 0.18);
      }

      body.mobile-notebook .guide-scroll {
        padding: 10px;
        gap: 10px;
      }

      .info-card {
        padding: 12px;
      }

      .relation-title {
        font-size: 15px;
      }

      .relation-item,
      .event-item,
      .path-step {
        padding: 10px;
      }

      .story-card {
        display: none;
      }

      .thought-drawer {
        width: 100vw;
      }

      .settings-drawer {
        width: 100vw;
      }

      .share-toast {
        bottom: calc(78px + env(safe-area-inset-bottom));
      }
    }

    @media (max-width: 780px) and (orientation: landscape) {
      .app {
        grid-template-rows: 112px minmax(0, 1fr) 0;
      }

      .mode-tabs button {
        min-height: 40px;
      }

      .workspace {
        height: calc(100dvh - 112px - 60px);
      }

      .mobile-mode-nav {
        height: calc(60px + env(safe-area-inset-bottom));
      }

      .roster,
      body.mobile-notebook .guide {
        bottom: calc(60px + env(safe-area-inset-bottom));
      }

      .roster {
        height: 68dvh;
      }

      body.mobile-sheet-full .roster,
      body.mobile-notebook .guide {
        height: 86dvh;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <div class="brand-icon" aria-hidden="true">
          <svg viewBox="0 0 32 32">
            <path d="M7 16h18M16 7v18M10 10l12 12M22 10L10 22"></path>
            <circle cx="7" cy="16" r="3.2"></circle>
            <circle cx="16" cy="7" r="3.2"></circle>
            <circle cx="25" cy="16" r="3.2"></circle>
            <circle cx="16" cy="25" r="3.2"></circle>
          </svg>
        </div>
        <div>
          <h1>GraphRAG</h1>
          <p>三國演義探險地圖｜人物、戰役、陣營與關係</p>
        </div>
      </div>
      <nav class="mode-tabs" aria-label="探索模式">
        <button type="button" class="is-active" data-mode="person"><span class="mode-name">人物探險</span><span class="mode-desc">從角色看身邊的人</span></button>
        <button type="button" data-mode="battle"><span class="mode-name">戰役現場</span><span class="mode-desc">選事件看參與者</span></button>
        <button type="button" data-mode="relation"><span class="mode-name">關係路徑</span><span class="mode-desc">找兩人怎麼連上</span></button>
      </nav>
      <div class="top-actions">
        <select id="chapterSelect" class="chapter-select" aria-label="全部章節"></select>
        <button type="button" id="shareView" class="icon-btn" aria-label="複製目前視角連結">分享</button>
        <button type="button" id="teacherToggle" class="icon-btn" aria-label="顯示設定">設定</button>
      </div>
    </header>

    <main class="workspace">
      <aside class="panel roster">
        <div class="panel-head">
          <div class="panel-title" id="rosterTitle">人物探險</div>
          <button type="button" id="mobileSheetToggle" class="sheet-toggle" aria-expanded="false">開啟篩選</button>
        </div>
        <div class="roster-controls">
          <div class="starter-panel" id="starterPanel">
            <div class="starter-head">
              <strong>從頭開始</strong>
              <span>選一位主角</span>
            </div>
            <div class="starter-grid" id="starterPeople"></div>
          </div>
          <div class="path-builder-panel" id="pathBuilderPanel">
            <div class="path-builder-head">
              <strong>建立一條關係路徑</strong>
              <span>選兩端</span>
            </div>
            <div class="path-input-grid">
              <label for="pathFrom"><span>從誰</span><input id="pathFrom" value="劉備" autocomplete="off"></label>
              <label for="pathTo"><span>到誰</span><input id="pathTo" value="曹操" autocomplete="off"></label>
            </div>
            <div class="quick-paths" id="quickPathPairs"></div>
            <div class="path-builder-actions">
              <button type="button" id="findPath" class="primary-btn">尋找路徑</button>
              <button type="button" id="swapPath" class="secondary-btn">交換</button>
              <button type="button" id="clearPath" class="secondary-btn">清除</button>
            </div>
          </div>
          <div class="control-panel" id="densityControl">
            <div class="filter-label"><span>顯示人數</span><span>先少後多</span></div>
            <div class="density-filters" id="densityFilters"></div>
          </div>
          <div class="control-panel" id="relationPresetControl">
            <div class="filter-label"><span>關係重點</span><span>選一種看法</span></div>
            <div class="relation-preset-filters" id="relationPresetFilters"></div>
          </div>
          <label class="field-label" id="searchLabel" for="searchInput">直接搜尋人物</label>
          <div class="search-wrap">
            <input id="searchInput" type="search" placeholder="搜尋：劉備、關羽、曹操" autocomplete="off">
          </div>
          <div class="camp-filter-panel is-visible" id="campFilterPanel">
            <div class="filter-label"><span>縮小關係圖</span><span>只看某一方</span></div>
            <div class="camp-filters" id="campFilters"></div>
          </div>
        </div>
        <div class="roster-list" id="rosterList"></div>
      </aside>

      <section class="map-zone" aria-label="互動關係地圖">
        <div class="map-head">
          <div class="map-title">
            <strong id="mapTitle">劉備：人物關係</strong>
          </div>
          <div class="map-tools" aria-label="地圖工具">
            <button type="button" id="zoomIn" aria-label="放大">+</button>
            <button type="button" id="zoomOut" aria-label="縮小">-</button>
            <button type="button" id="zoomReset" aria-label="回到全圖">□</button>
          </div>
        </div>
        <div class="graph-wrap">
          <svg id="graph" role="img" aria-label="三國演義人物與故事關係圖"></svg>
          <div class="hint">點一個人名，看看他的朋友、對手與故事線。</div>
        </div>
      </section>

      <aside class="panel guide">
        <div class="panel-head">
          <div class="panel-title">重點事件簿</div>
        </div>
        <div class="guide-scroll">
          <section class="info-card path-result-card" id="pathResultCard">
            <h2>路徑結果</h2>
            <p>選兩個人物後，這裡會列出中間經過的人、事件與關係證據。</p>
            <div class="path-result" id="pathResult"></div>
          </section>
          <section class="info-card">
            <h2 id="eventBookTitle">關係分類</h2>
            <div class="relation-groups" id="relationGroups"></div>
          </section>
          <section class="info-card battle-search" id="battleSearchCard">
            <h2>找戰役或事件</h2>
            <div class="search-wrap">
              <input id="battleSearchInput" type="search" placeholder="搜尋：赤壁、官渡、長坂、三英" autocomplete="off">
            </div>
          </section>
        </div>
      </aside>
    </main>

    <nav class="mobile-mode-nav" id="mobileModeNav" aria-label="手機探索模式">
      <button type="button" class="is-active" data-mobile-mode="person"><span>人物</span><small>看關係</small></button>
      <button type="button" data-mobile-mode="battle"><span>戰役</span><small>看事件</small></button>
      <button type="button" data-mobile-mode="relation"><span>路徑</span><small>找連線</small></button>
      <button type="button" data-mobile-mode="notebook"><span>事件簿</span><small>讀重點</small></button>
    </nav>

    <section class="story-card" aria-label="故事卡片">
      <div class="story-section">
        <div class="selected-head">
          <div id="selectedBadge" class="selected-badge camp-shu">劉</div>
          <div class="selected-title">
            <h2 id="selectedName">劉備</h2>
            <span id="selectedMeta">劉蜀・人物</span>
          </div>
        </div>
        <p class="intro" id="selectedIntro"></p>
        <div class="selected-actions">
          <button type="button" id="openThought" class="thought-trigger" aria-label="想一想">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a7 7 0 0 0-4 12.74V18h8v-2.26A7 7 0 0 0 12 3Z"></path><path d="M9 21h6"></path><path d="M10 18h4"></path></svg>
            <span>想一想</span>
          </button>
        </div>
        <div class="trait-list" id="traitList"></div>
      </div>
      <div class="story-section">
        <h3>重要時刻</h3>
        <div class="event-list" id="eventList"></div>
      </div>
    </section>
    <div id="drawerScrim" class="drawer-scrim" aria-hidden="true"></div>
    <div id="shareToast" class="share-toast" role="status" aria-live="polite">已複製目前視角連結</div>
    <aside id="settingsDrawer" class="settings-drawer" aria-label="顯示設定" aria-hidden="true">
      <div class="drawer-head">
        <h2>顯示設定</h2>
        <button type="button" id="closeSettings" class="icon-btn" aria-label="關閉顯示設定">×</button>
      </div>
      <div class="drawer-body">
        <section class="settings-section">
          <h3>顯示風格</h3>
          <p class="settings-note">清爽會減少干擾線條；閱讀會讓卡片與文字更像讀故事。</p>
          <div class="segmented-options" id="styleOptions">
            <button type="button" data-style="balanced" class="is-active">平衡</button>
            <button type="button" data-style="clean">清爽</button>
            <button type="button" data-style="reading">閱讀</button>
          </div>
        </section>
        <section class="settings-section">
          <h3>字體大小</h3>
          <p class="settings-note">小字適合看更多資訊；大字適合投影、平板共讀或低年級閱讀。</p>
          <div class="segmented-options" id="fontScaleOptions">
            <button type="button" data-font-scale="small">小字</button>
            <button type="button" data-font-scale="normal" class="is-active">中字</button>
            <button type="button" data-font-scale="large">大字</button>
          </div>
        </section>
        <section class="settings-section">
          <h3>地圖密度</h3>
          <p class="settings-note">節點越少越適合初學者，節點越多越適合討論細節。</p>
          <div class="teacher-row">
            <label for="nodeLimit">節點上限 <span id="nodeLimitValue">20</span></label>
            <input id="nodeLimit" type="range" min="12" max="30" step="1" value="20">
          </div>
        </section>
        <section class="settings-section">
          <h3>關係類型</h3>
          <p class="settings-note">取消不想看的關係，地圖會更清楚。</p>
          <div class="check-list" id="categoryChecks"></div>
        </section>
      </div>
    </aside>
    <aside id="thoughtDrawer" class="thought-drawer" aria-label="想一想" aria-hidden="true">
      <div class="drawer-head">
        <h2>想一想</h2>
        <button type="button" id="closeThought" class="icon-btn" aria-label="關閉想一想">×</button>
      </div>
      <div class="drawer-body">
        <div class="thought-box">
          <p id="thinkingPrompt" class="intro"></p>
          <div class="thinking-prompts" id="thinkingPromptList"></div>
          <textarea id="thinkingNote" placeholder="寫下你的想法，這只會留在這台電腦上。"></textarea>
          <div>
            <h3>可用證據</h3>
            <div class="mini-tags" id="evidenceTags"></div>
          </div>
        </div>
      </div>
    </aside>
  </div>

  <script id="graph-data" type="application/json">__GRAPH_DATA_JSON__</script>
  <script>
  (() => {
    "use strict";

    const DATA = JSON.parse(document.getElementById("graph-data").textContent);
    const nodes = DATA.nodes;
    const relationships = DATA.relationships;
    const nodeById = new Map(nodes.map(node => [node.id, node]));
    const nameIndex = new Map();
    const relsByNode = new Map();
    const posCache = new Map();
    const savedNotes = JSON.parse(localStorage.getItem("sanguo-v11-notes") || "{}");
    const savedSettings = JSON.parse(localStorage.getItem("sanguo-v11-settings") || "{}");

    const CORE_CAMPS = new Set(["wei", "shu", "wu"]);
    const CAMP_ORDER = ["wei", "shu", "wu", "others"];
    const CAMP_FILTERS = [
      { id: "all", label: "全部" },
      { id: "wei", label: "魏" },
      { id: "shu", label: "蜀" },
      { id: "wu", label: "吳" },
      { id: "others", label: "其他群雄" },
    ];
    const CAMP_LABELS = {
      wei: "魏",
      shu: "蜀",
      wu: "吳",
      lords: "群雄",
      mixed: "多方",
      neutral: "其他",
      han: "漢室",
      others: "其他群雄",
    };
    const DEFAULT_CATEGORIES = new Set(["story", "enemy", "defeat", "ally", "strategy", "command", "family"]);
    const DEFAULT_NODE_LIMIT = 20;
    const DEFAULT_RELATION_PRESET = "core";
    const DENSITY_LEVELS = [
      { id: "light", label: "12人", value: 12 },
      { id: "clear", label: "20人", value: 20 },
      { id: "rich", label: "30人", value: 30 },
    ];
    const RELATION_PRESETS = [
      { id: "core", label: "主幹", categories: ["story", "command", "ally", "family"] },
      { id: "conflict", label: "衝突", categories: ["enemy", "defeat"] },
      { id: "ally", label: "合作", categories: ["ally", "command", "family"] },
      { id: "strategy", label: "計策", categories: ["strategy", "command", "story"] },
      { id: "all", label: "全部", categories: [...DEFAULT_CATEGORIES] },
    ];
    const QUICK_PATH_PAIRS = [
      { from: "劉備", to: "曹操", label: "劉備 → 曹操", hint: "仁義與霸業" },
      { from: "劉備", to: "孫權", label: "劉備 → 孫權", hint: "孫劉合作" },
      { from: "曹操", to: "周瑜", label: "曹操 → 周瑜", hint: "赤壁對手" },
      { from: "關羽", to: "曹操", label: "關羽 → 曹操", hint: "義與知遇" },
    ];
    const DEFAULT_PERSON = "劉備";
    const STARTER_PEOPLE = ["劉備", "曹操", "孫權"];
    const THINKING_PROMPTS = {
      all: "如果你是故事導覽員，你會先介紹哪三個人物，讓同學最快懂三國局勢？",
      ch001_010: "呂布武力很強，但他改變陣營好幾次。你覺得選擇夥伴時，最重要的是什麼？",
      ch011_020: "如果你是劉備，遇到曹操、呂布、袁術都在拉扯，你會先保護什麼？",
      ch021_030: "官渡前後，曹操和袁紹誰比較會使用身邊的人？請找兩條關係線支持你的想法。",
      ch031_040: "如果你是諸葛亮，要怎麼讓劉備相信你的計畫值得嘗試？",
      ch041_050: "赤壁之前，孫權要不要出兵很難決定。你會用哪三個理由說服他？",
      ch051_060: "三方勢力變清楚後，哪一方最需要新的盟友？為什麼？",
    };

    const state = {
      mode: "person",
      mobileMode: "person",
      mobileSheetSnap: "peek",
      chapterPreset: "all",
      campFilter: "all",
      query: "",
      battleQuery: "",
      selectedId: findNodeId(DEFAULT_PERSON) || nodes[0].id,
      pathIds: [],
      nodeLimit: DEFAULT_NODE_LIMIT,
      relationPreset: DEFAULT_RELATION_PRESET,
      visualStyle: ["balanced", "clean", "reading"].includes(savedSettings.visualStyle) ? savedSettings.visualStyle : "balanced",
      fontScale: ["small", "normal", "large"].includes(savedSettings.fontScale) ? savedSettings.fontScale : "normal",
      enabledCategories: new Set(RELATION_PRESETS.find(preset => preset.id === DEFAULT_RELATION_PRESET)?.categories || DEFAULT_CATEGORIES),
    };

    let svg;
    let viewport;
    let linkSel;
    let nodeSel;
    let simulation;
    let zoomBehavior;
    let currentGraph = { nodes: [], links: [] };
    let hasCompletedInit = false;
    let isApplyingHash = false;
    let shareToastTimer = 0;

    const dom = {
      chapterSelect: document.getElementById("chapterSelect"),
      campFilters: document.getElementById("campFilters"),
      campFilterPanel: document.getElementById("campFilterPanel"),
      densityControl: document.getElementById("densityControl"),
      densityFilters: document.getElementById("densityFilters"),
      relationPresetControl: document.getElementById("relationPresetControl"),
      relationPresetFilters: document.getElementById("relationPresetFilters"),
      pathBuilderPanel: document.getElementById("pathBuilderPanel"),
      quickPathPairs: document.getElementById("quickPathPairs"),
      starterPanel: document.getElementById("starterPanel"),
      starterPeople: document.getElementById("starterPeople"),
      rosterList: document.getElementById("rosterList"),
      rosterTitle: document.getElementById("rosterTitle"),
      mobileSheetToggle: document.getElementById("mobileSheetToggle"),
      searchLabel: document.getElementById("searchLabel"),
      searchInput: document.getElementById("searchInput"),
      battleSearchCard: document.getElementById("battleSearchCard"),
      battleSearchInput: document.getElementById("battleSearchInput"),
      mapTitle: document.getElementById("mapTitle"),
      relationGroups: document.getElementById("relationGroups"),
      eventBookTitle: document.getElementById("eventBookTitle"),
      selectedBadge: document.getElementById("selectedBadge"),
      selectedName: document.getElementById("selectedName"),
      selectedMeta: document.getElementById("selectedMeta"),
      selectedIntro: document.getElementById("selectedIntro"),
      traitList: document.getElementById("traitList"),
      eventList: document.getElementById("eventList"),
      thinkingPrompt: document.getElementById("thinkingPrompt"),
      thinkingPromptList: document.getElementById("thinkingPromptList"),
      thinkingNote: document.getElementById("thinkingNote"),
      evidenceTags: document.getElementById("evidenceTags"),
      teacherToggle: document.getElementById("teacherToggle"),
      shareView: document.getElementById("shareView"),
      shareToast: document.getElementById("shareToast"),
      settingsDrawer: document.getElementById("settingsDrawer"),
      closeSettings: document.getElementById("closeSettings"),
      styleOptions: document.getElementById("styleOptions"),
      fontScaleOptions: document.getElementById("fontScaleOptions"),
      nodeLimit: document.getElementById("nodeLimit"),
      nodeLimitValue: document.getElementById("nodeLimitValue"),
      categoryChecks: document.getElementById("categoryChecks"),
      pathResultCard: document.getElementById("pathResultCard"),
      pathFrom: document.getElementById("pathFrom"),
      pathTo: document.getElementById("pathTo"),
      findPath: document.getElementById("findPath"),
      swapPath: document.getElementById("swapPath"),
      clearPath: document.getElementById("clearPath"),
      pathResult: document.getElementById("pathResult"),
      mobileModeNav: document.getElementById("mobileModeNav"),
      zoomIn: document.getElementById("zoomIn"),
      zoomOut: document.getElementById("zoomOut"),
      zoomReset: document.getElementById("zoomReset"),
      openThought: document.getElementById("openThought"),
      closeThought: document.getElementById("closeThought"),
      thoughtDrawer: document.getElementById("thoughtDrawer"),
      drawerScrim: document.getElementById("drawerScrim"),
    };

    nodes.forEach(node => {
      addNameKey(node.name, node.id);
      (node.aliases || []).forEach(alias => addNameKey(alias, node.id));
    });

    relationships.forEach(rel => {
      if (!nodeById.has(rel.source) || !nodeById.has(rel.target)) return;
      if (!relsByNode.has(rel.source)) relsByNode.set(rel.source, []);
      if (!relsByNode.has(rel.target)) relsByNode.set(rel.target, []);
      relsByNode.get(rel.source).push(rel);
      relsByNode.get(rel.target).push(rel);
    });

    init();

    function init() {
      svg = d3.select("#graph");
      zoomBehavior = d3.zoom()
        .scaleExtent([0.3, 3.2])
        .on("zoom", event => viewport.attr("transform", event.transform));
      svg.call(zoomBehavior);
      viewport = svg.append("g").attr("class", "viewport");
      viewport.append("g").attr("class", "links");
      viewport.append("g").attr("class", "nodes");

      renderStaticControls();
      applyDisplaySettings(false);
      setMobileSheetSnap("peek");
      applyHashState();
      syncMobileModeNav();
      updateScenarioChrome();
      bindEvents();
      rebuildGraph("init");
      updatePanels();
      hasCompletedInit = true;
    }

    function renderStaticControls() {
      dom.chapterSelect.replaceChildren(...DATA.chapterPresets.map(preset => {
        const option = document.createElement("option");
        option.value = preset.id;
        option.textContent = preset.id === "all" ? "全部章節" : `${preset.shortLabel} ${preset.label}`;
        return option;
      }));

      dom.campFilters.replaceChildren(...CAMP_FILTERS.map(item => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `chip camp-${item.id}${item.id === "all" ? " is-active" : ""}`;
        button.dataset.camp = item.id;
        button.textContent = item.label;
        return button;
      }));

      dom.densityFilters.replaceChildren(...DENSITY_LEVELS.map(level => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `chip density-chip${level.value === state.nodeLimit ? " is-active" : ""}`;
        button.dataset.limit = String(level.value);
        button.textContent = level.label;
        return button;
      }));

      dom.relationPresetFilters.replaceChildren(...RELATION_PRESETS.map(preset => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `chip preset-${preset.id}${preset.id === state.relationPreset ? " is-active" : ""}`;
        button.dataset.preset = preset.id;
        button.textContent = preset.label;
        return button;
      }));

      dom.quickPathPairs.replaceChildren(...QUICK_PATH_PAIRS.map(pair => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "quick-path-btn";
        button.dataset.from = pair.from;
        button.dataset.to = pair.to;
        const label = document.createElement("span");
        label.textContent = pair.label;
        const hint = document.createElement("small");
        hint.textContent = pair.hint;
        button.append(label, hint);
        return button;
      }));

      dom.starterPeople.replaceChildren(...STARTER_PEOPLE.map(name => {
        const node = nodeById.get(findNodeId(name));
        const button = document.createElement("button");
        button.type = "button";
        button.className = `starter-person camp-${node?.camp || "neutral"}${node?.id === state.selectedId ? " is-active" : ""}`;
        button.dataset.person = name;
        const title = document.createElement("strong");
        title.textContent = name;
        const meta = document.createElement("small");
        meta.textContent = node?.campLabel ? `${node.campLabel}起點` : "故事起點";
        button.append(title, meta);
        return button;
      }));

      dom.categoryChecks.replaceChildren(...DATA.kidCategories.map(cat => {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = cat.id;
        input.checked = state.enabledCategories.has(cat.id);
        const span = document.createElement("span");
        span.textContent = cat.label;
        label.append(input, span);
        return label;
      }));
    }

    function bindEvents() {
      document.querySelectorAll("[data-mode]").forEach(button => {
        button.addEventListener("click", () => {
          setMode(button.dataset.mode);
          state.pathIds = [];
          rebuildGraph("mode");
          updatePanels();
        });
      });

      if (dom.mobileModeNav) {
        dom.mobileModeNav.addEventListener("click", event => {
          const button = event.target.closest("button[data-mobile-mode]");
          if (!button) return;
          setMobileMode(button.dataset.mobileMode);
        });
      }

      const rosterHandle = document.querySelector(".roster .panel-head");
      const guideHandle = document.querySelector(".guide .panel-head");
      dom.mobileSheetToggle?.addEventListener("click", event => {
        event.stopPropagation();
        if (isMobileLayout()) toggleMobileFilterSheet();
      });
      rosterHandle?.addEventListener("click", event => {
        if (!isMobileLayout()) return;
        if (event.target.closest("button")) return;
        if (state.mobileSheetSnap === "peek") setMobileSheetSnap("full");
      });
      guideHandle?.addEventListener("click", () => {
        if (isMobileLayout()) setMobileMode(state.mode || "person");
      });

      dom.chapterSelect.addEventListener("change", () => {
        state.chapterPreset = dom.chapterSelect.value;
        state.pathIds = [];
        persistNote();
        rebuildGraph("chapter");
        updatePanels();
      });

      dom.campFilters.addEventListener("click", event => {
        const button = event.target.closest("button[data-camp]");
        if (!button) return;
        state.campFilter = button.dataset.camp;
        [...dom.campFilters.children].forEach(child => child.classList.toggle("is-active", child === button));
        renderRoster();
        rebuildGraph("campFilter");
      });

      dom.densityFilters.addEventListener("click", event => {
        const button = event.target.closest("button[data-limit]");
        if (!button) return;
        state.nodeLimit = Number(button.dataset.limit);
        dom.nodeLimit.value = String(state.nodeLimit);
        dom.nodeLimitValue.textContent = String(state.nodeLimit);
        syncDensityButtons();
        rebuildGraph("limit");
        updatePanels();
      });

      dom.relationPresetFilters.addEventListener("click", event => {
        const button = event.target.closest("button[data-preset]");
        if (!button) return;
        applyRelationPreset(button.dataset.preset);
        rebuildGraph("categories");
        updatePanels();
      });

      dom.searchInput.addEventListener("input", debounce(() => {
        state.query = dom.searchInput.value.trim();
        if (state.mode === "battle" && isMobileLayout()) {
          state.battleQuery = state.query;
          dom.battleSearchInput.value = state.query;
          renderRelationGroups(nodeById.get(state.selectedId) || nodes[0], currentPreset());
        }
        renderRoster();
      }, 120));

      dom.starterPeople.addEventListener("click", event => {
        const button = event.target.closest("button[data-person]");
        if (!button) return;
        startFromPerson(button.dataset.person);
      });

      dom.battleSearchInput.addEventListener("input", debounce(() => {
        state.battleQuery = dom.battleSearchInput.value.trim();
        if (isMobileLayout() && state.mode === "battle") {
          state.query = state.battleQuery;
          dom.searchInput.value = state.battleQuery;
          renderRoster();
        }
        renderRelationGroups(nodeById.get(state.selectedId) || nodes[0], currentPreset());
      }, 120));

      dom.quickPathPairs.addEventListener("click", event => {
        const button = event.target.closest("button[data-from][data-to]");
        if (!button) return;
        dom.pathFrom.value = button.dataset.from;
        dom.pathTo.value = button.dataset.to;
        runPathSearch();
      });

      dom.teacherToggle.addEventListener("click", () => {
        openSettingsDrawer();
      });

      dom.shareView.addEventListener("click", () => copyCurrentViewLink());

      dom.closeSettings.addEventListener("click", () => closeSettingsDrawer());

      dom.styleOptions.addEventListener("click", event => {
        const button = event.target.closest("button[data-style]");
        if (!button) return;
        state.visualStyle = button.dataset.style;
        applyDisplaySettings();
        rebuildGraph("style");
        updatePanels();
      });

      dom.fontScaleOptions.addEventListener("click", event => {
        const button = event.target.closest("button[data-font-scale]");
        if (!button) return;
        state.fontScale = button.dataset.fontScale;
        applyDisplaySettings();
      });

      dom.nodeLimit.addEventListener("input", debounce(() => {
        state.nodeLimit = Number(dom.nodeLimit.value);
        dom.nodeLimitValue.textContent = String(state.nodeLimit);
        syncDensityButtons();
        rebuildGraph("limit");
        updatePanels();
      }, 180));

      dom.categoryChecks.addEventListener("change", () => {
        state.enabledCategories = new Set(
          [...dom.categoryChecks.querySelectorAll("input:checked")].map(input => input.value)
        );
        state.relationPreset = "custom";
        syncRelationPresetButtons();
        rebuildGraph("categories");
        updatePanels();
      });

      dom.findPath.addEventListener("click", () => runPathSearch());

      dom.swapPath.addEventListener("click", () => {
        const from = dom.pathFrom.value;
        dom.pathFrom.value = dom.pathTo.value;
        dom.pathTo.value = from;
      });

      dom.clearPath.addEventListener("click", () => {
        state.pathIds = [];
        rebuildGraph("clearPath");
        updatePanels();
      });

      dom.thinkingNote.addEventListener("input", debounce(persistNote, 200));
      dom.openThought.addEventListener("click", () => openThoughtDrawer());
      dom.closeThought.addEventListener("click", () => closeThoughtDrawer());
      dom.drawerScrim.addEventListener("click", () => closeAllDrawers());
      document.addEventListener("keydown", event => {
        if (event.key === "Escape") closeAllDrawers();
      });
      dom.zoomIn.addEventListener("click", () => svg.transition().duration(180).call(zoomBehavior.scaleBy, 1.2));
      dom.zoomOut.addEventListener("click", () => svg.transition().duration(180).call(zoomBehavior.scaleBy, 0.82));
      dom.zoomReset.addEventListener("click", () => resetZoom());
      window.addEventListener("hashchange", () => {
        applyHashState();
        updateScenarioChrome();
        rebuildGraph("hash");
        updatePanels();
      });
      window.addEventListener("resize", debounce(() => rebuildGraph("resize"), 120));
    }

    function isMobileLayout() {
      return window.matchMedia("(max-width: 780px)").matches;
    }

    function setMobileMode(mode) {
      state.mobileMode = mode;
      syncMobileModeNav();
      if (mode === "notebook") {
        document.body.classList.add("mobile-notebook");
        setMobileSheetSnap("full");
        updatePanels();
        return;
      }

      document.body.classList.remove("mobile-notebook");
      if (mode !== "relation") state.pathIds = [];
      setMode(mode);
      if (mode === "battle") {
        state.query = state.battleQuery;
        dom.searchInput.value = state.battleQuery;
      }
      setMobileSheetSnap("peek");
      rebuildGraph("mobileMode");
      updatePanels();
    }

    function setMobileSheetSnap(snap) {
      const normalized = snap === "half" ? "full" : snap;
      state.mobileSheetSnap = normalized;
      document.body.classList.toggle("mobile-sheet-peek", normalized === "peek");
      document.body.classList.toggle("mobile-sheet-half", false);
      document.body.classList.toggle("mobile-sheet-full", normalized === "full");
      if (dom.mobileSheetToggle) {
        const expanded = normalized === "full";
        dom.mobileSheetToggle.textContent = expanded ? "收合" : "開啟篩選";
        dom.mobileSheetToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
      }
    }

    function toggleMobileFilterSheet() {
      if (document.body.classList.contains("mobile-notebook")) return;
      setMobileSheetSnap(state.mobileSheetSnap === "full" ? "peek" : "full");
    }

    function syncMobileModeNav() {
      if (!dom.mobileModeNav) return;
      [...dom.mobileModeNav.querySelectorAll("button[data-mobile-mode]")].forEach(button => {
        button.classList.toggle("is-active", button.dataset.mobileMode === state.mobileMode);
      });
    }

    function validMode(mode) {
      return ["person", "battle", "relation"].includes(mode) ? mode : null;
    }

    function validChapterPreset(id) {
      return DATA.chapterPresets.some(preset => preset.id === id);
    }

    function validCampFilter(id) {
      return CAMP_FILTERS.some(item => item.id === id);
    }

    function syncCampButtons() {
      [...dom.campFilters.children].forEach(child => {
        child.classList.toggle("is-active", child.dataset.camp === state.campFilter);
      });
    }

    function syncStateControls() {
      dom.chapterSelect.value = state.chapterPreset;
      dom.nodeLimit.value = String(state.nodeLimit);
      dom.nodeLimitValue.textContent = String(state.nodeLimit);
      syncDensityButtons();
      syncRelationPresetButtons();
      syncCategoryChecks();
      syncCampButtons();
      setActiveModeButtons();
      syncMobileModeNav();
    }

    function applyHashState() {
      if (!location.hash || location.hash.length <= 1) return false;
      const params = new URLSearchParams(location.hash.slice(1));
      isApplyingHash = true;
      try {
        const chapter = params.get("chapter");
        if (chapter && validChapterPreset(chapter)) state.chapterPreset = chapter;

        const limit = Number(params.get("limit"));
        if (Number.isFinite(limit)) state.nodeLimit = Math.max(12, Math.min(30, Math.round(limit)));

        const preset = params.get("preset");
        if (preset && RELATION_PRESETS.some(item => item.id === preset)) {
          applyRelationPreset(preset);
        }

        const mode = validMode(params.get("mode")) || "person";
        const panel = params.get("panel");
        state.mode = mode;
        state.mobileMode = panel === "notebook" ? "notebook" : mode;
        state.query = "";
        state.battleQuery = "";
        state.pathIds = [];

        const camp = params.get("camp");
        state.campFilter = mode === "person" && camp && validCampFilter(camp) ? camp : "all";

        if (mode === "relation") {
          const fromName = params.get("from") || "劉備";
          const toName = params.get("to") || "曹操";
          dom.pathFrom.value = fromName;
          dom.pathTo.value = toName;
          const from = findNodeId(fromName);
          const to = findNodeId(toName);
          if (from && to) {
            state.pathIds = shortestPath(from, to);
            state.selectedId = from;
          }
        } else if (mode === "battle") {
          const eventName = params.get("event") || params.get("person");
          const id = eventName ? findNodeId(eventName) : "";
          const eventNode = id ? nodeById.get(id) : null;
          state.selectedId = eventNode && isStoryNode(eventNode) ? id : (topEventForPreset(currentPreset())?.id || state.selectedId);
        } else {
          const personName = params.get("person") || DEFAULT_PERSON;
          const id = findNodeId(personName);
          const node = id ? nodeById.get(id) : null;
          state.selectedId = node && !isStoryNode(node) ? id : (findNodeId(DEFAULT_PERSON) || state.selectedId);
        }

        dom.searchInput.value = "";
        dom.battleSearchInput.value = "";
        document.body.classList.toggle("mobile-notebook", state.mobileMode === "notebook");
        if (state.mobileMode === "notebook") {
          setMobileSheetSnap("full");
        } else if (panel === "full" || panel === "half") {
          setMobileSheetSnap(panel);
        } else {
          setMobileSheetSnap("peek");
        }
        syncStateControls();
        return true;
      } finally {
        isApplyingHash = false;
      }
    }

    function updateHashState() {
      if (isApplyingHash || !hasCompletedInit) return;
      const params = new URLSearchParams();
      params.set("mode", state.mode);
      params.set("chapter", state.chapterPreset);
      const selected = nodeById.get(state.selectedId);
      if (state.mode === "relation") {
        const fromName = dom.pathFrom.value.trim() || selected?.name || DEFAULT_PERSON;
        const toName = dom.pathTo.value.trim() || "曹操";
        params.set("from", fromName);
        params.set("to", toName);
      } else if (state.mode === "battle") {
        params.set("event", selected?.name || "");
      } else {
        params.set("person", selected?.name || DEFAULT_PERSON);
        if (state.campFilter !== "all") params.set("camp", state.campFilter);
      }
      if (state.nodeLimit !== DEFAULT_NODE_LIMIT) params.set("limit", String(state.nodeLimit));
      if (state.relationPreset !== DEFAULT_RELATION_PRESET) params.set("preset", state.relationPreset);
      if (document.body.classList.contains("mobile-notebook")) {
        params.set("panel", "notebook");
      } else if (state.mobileSheetSnap === "full" || state.mobileSheetSnap === "half") {
        params.set("panel", state.mobileSheetSnap);
      }
      const nextHash = params.toString();
      if (location.hash.slice(1) === nextHash) return;
      history.replaceState(null, "", `${location.href.split("#")[0]}#${nextHash}`);
    }

    async function copyCurrentViewLink() {
      updateHashState();
      const url = location.href;
      try {
        await navigator.clipboard.writeText(url);
        showShareToast("已複製目前視角連結");
      } catch (error) {
        showShareToast("可從網址列複製目前視角連結");
      }
    }

    function showShareToast(message) {
      dom.shareToast.textContent = message;
      dom.shareToast.classList.add("is-visible");
      clearTimeout(shareToastTimer);
      shareToastTimer = setTimeout(() => dom.shareToast.classList.remove("is-visible"), 1800);
    }

    function openMobileNotebook() {
      state.mobileMode = "notebook";
      document.body.classList.add("mobile-notebook");
      setMobileSheetSnap("full");
      syncMobileModeNav();
      updateHashState();
    }

    function setMode(mode) {
      state.mode = mode;
      if (state.mobileMode !== "notebook") state.mobileMode = mode;
      if (mode !== "person") {
        state.campFilter = "all";
        [...dom.campFilters.children].forEach(child => child.classList.toggle("is-active", child.dataset.camp === "all"));
      }
      if (mode === "battle") {
        const event = topEventForPreset(currentPreset());
        if (event) state.selectedId = event.id;
      }
      if (mode === "person" && isStoryNode(nodeById.get(state.selectedId) || {})) {
        state.selectedId = findNodeId(DEFAULT_PERSON) || state.selectedId;
      }
      setActiveModeButtons();
      syncMobileModeNav();
      updateScenarioChrome();
    }

    function setActiveModeButtons() {
      document.querySelectorAll("[data-mode]").forEach(btn => {
        btn.classList.toggle("is-active", btn.dataset.mode === state.mode);
      });
    }

    function syncDensityButtons() {
      [...dom.densityFilters.children].forEach(child => {
        child.classList.toggle("is-active", Number(child.dataset.limit) === state.nodeLimit);
      });
    }

    function syncRelationPresetButtons() {
      [...dom.relationPresetFilters.children].forEach(child => {
        child.classList.toggle("is-active", child.dataset.preset === state.relationPreset);
      });
    }

    function syncCategoryChecks() {
      dom.categoryChecks.querySelectorAll("input").forEach(input => {
        input.checked = state.enabledCategories.has(input.value);
      });
    }

    function applyRelationPreset(id) {
      const preset = RELATION_PRESETS.find(item => item.id === id) || RELATION_PRESETS[0];
      state.relationPreset = preset.id;
      state.enabledCategories = new Set(preset.categories);
      syncRelationPresetButtons();
      syncCategoryChecks();
    }

    function applyDisplaySettings(shouldPersist = true) {
      document.body.classList.toggle("style-clean", state.visualStyle === "clean");
      document.body.classList.toggle("style-reading", state.visualStyle === "reading");
      document.body.classList.toggle("font-small", state.fontScale === "small");
      document.body.classList.toggle("font-large", state.fontScale === "large");
      syncDisplaySettingButtons();
      if (shouldPersist) persistDisplaySettings();
    }

    function syncDisplaySettingButtons() {
      if (dom.styleOptions) {
        [...dom.styleOptions.querySelectorAll("button[data-style]")].forEach(button => {
          button.classList.toggle("is-active", button.dataset.style === state.visualStyle);
        });
      }
      if (dom.fontScaleOptions) {
        [...dom.fontScaleOptions.querySelectorAll("button[data-font-scale]")].forEach(button => {
          button.classList.toggle("is-active", button.dataset.fontScale === state.fontScale);
        });
      }
    }

    function persistDisplaySettings() {
      localStorage.setItem("sanguo-v11-settings", JSON.stringify({
        visualStyle: state.visualStyle,
        fontScale: state.fontScale,
      }));
    }

    function runPathSearch() {
      const from = findNodeId(dom.pathFrom.value.trim());
      const to = findNodeId(dom.pathTo.value.trim());
      if (!from || !to) {
        state.pathIds = [];
        setMode("relation");
        renderPathResult([], "找不到其中一個名字，請試試完整人物名。");
        return;
      }
      const path = shortestPath(from, to);
      if (!path.length) {
        state.pathIds = [];
        setMode("relation");
        renderPathResult([], "這個章回範圍內找不到可讀的路徑。");
        return;
      }
      setMode("relation");
      state.pathIds = path;
      state.selectedId = from;
      rebuildGraph("path");
      updatePanels();
      if (isMobileLayout()) openMobileNotebook();
    }

    function startFromPerson(name) {
      const id = findNodeId(name);
      if (!id) return;
      persistNote();
      state.query = "";
      state.battleQuery = "";
      state.campFilter = "all";
      state.pathIds = [];
      state.selectedId = id;
      dom.searchInput.value = "";
      dom.battleSearchInput.value = "";
      [...dom.campFilters.children].forEach(child => child.classList.toggle("is-active", child.dataset.camp === "all"));
      setMode("person");
      rebuildGraph("starter");
      updatePanels();
    }

    function campGroupKey(camp) {
      return CORE_CAMPS.has(camp) ? camp : "others";
    }

    function campMatchesFilter(camp, filter = state.campFilter) {
      if (filter === "all") return true;
      if (filter === "others") return !CORE_CAMPS.has(camp);
      return camp === filter;
    }

    function updateScenarioChrome() {
      const copy = rosterCopy();
      dom.rosterTitle.textContent = copy.panelTitle;
      dom.searchLabel.textContent = copy.searchLabel;
      dom.searchInput.placeholder = copy.placeholder;
      dom.campFilterPanel.classList.toggle("is-visible", state.mode === "person");
      dom.pathBuilderPanel.classList.toggle("is-visible", state.mode === "relation");
      dom.pathResultCard.classList.toggle("is-visible", state.mode === "relation" || state.pathIds.length > 0);
      dom.starterPanel.style.display = state.mode === "person" ? "" : "none";
      dom.densityControl.style.display = state.mode === "relation" ? "none" : "";
      dom.relationPresetControl.style.display = state.mode === "battle" ? "none" : "";
      const hideMainSearch = state.mode === "battle" && !isMobileLayout();
      dom.searchLabel.style.display = hideMainSearch ? "none" : "";
      dom.searchInput.parentElement.style.display = hideMainSearch ? "none" : "";
      dom.battleSearchCard.classList.toggle("is-visible", state.mode === "battle");
      dom.eventBookTitle.textContent = state.mode === "battle" ? "推薦故事與戰役" : (state.mode === "relation" ? "路徑中的關係" : "關係分類");
      [...dom.starterPeople.children].forEach(child => {
        const id = findNodeId(child.dataset.person);
        child.classList.toggle("is-active", id === state.selectedId && state.mode === "person");
      });
      syncMobileModeNav();
    }

    function openThoughtDrawer() {
      closeSettingsDrawer(false);
      dom.thoughtDrawer.classList.add("is-open");
      dom.drawerScrim.classList.add("is-open");
      dom.thoughtDrawer.setAttribute("aria-hidden", "false");
      dom.thinkingNote.focus();
    }

    function closeThoughtDrawer(closeScrim = true) {
      dom.thoughtDrawer.classList.remove("is-open");
      dom.thoughtDrawer.setAttribute("aria-hidden", "true");
      if (closeScrim) dom.drawerScrim.classList.remove("is-open");
    }

    function openSettingsDrawer() {
      closeThoughtDrawer(false);
      dom.settingsDrawer.classList.add("is-open");
      dom.drawerScrim.classList.add("is-open");
      dom.settingsDrawer.setAttribute("aria-hidden", "false");
    }

    function closeSettingsDrawer(closeScrim = true) {
      dom.settingsDrawer.classList.remove("is-open");
      dom.settingsDrawer.setAttribute("aria-hidden", "true");
      if (closeScrim) dom.drawerScrim.classList.remove("is-open");
    }

    function closeAllDrawers() {
      closeThoughtDrawer(false);
      closeSettingsDrawer(false);
      dom.drawerScrim.classList.remove("is-open");
    }

    function rebuildGraph(reason) {
      const graph = buildGraph();
      currentGraph = graph;
      const { width, height } = graphSize();
      if (simulation) simulation.stop();

      const center = campCenter("neutral", width, height);
      const simNodes = graph.nodes.map(node => {
        const cached = posCache.get(node.id);
        const [cx, cy] = campCenter(node.camp, width, height);
        const radius = nodeRadius(node);
        return {
          ...node,
          r: radius,
          x: cached?.x ?? cx + (Math.random() - 0.5) * 96,
          y: cached?.y ?? cy + (Math.random() - 0.5) * 96,
        };
      });
      const simNodeById = new Map(simNodes.map(node => [node.id, node]));
      const simLinks = graph.links
        .filter(link => simNodeById.has(link.source) && simNodeById.has(link.target))
        .map(link => ({ ...link }));

      linkSel = viewport.select(".links").selectAll("line")
        .data(simLinks, d => d.id)
        .join(
          enter => enter.append("line")
            .attr("class", d => `link cat-${d.kidCategory}`)
            .attr("stroke-width", d => Math.min(4.5, 1.4 + Math.sqrt(d.weight || 1) * 0.75)),
          update => update.attr("class", d => `link cat-${d.kidCategory}`),
          exit => exit.remove()
        );

      nodeSel = viewport.select(".nodes").selectAll("g.node")
        .data(simNodes, d => d.id)
        .join(
          enter => {
            const g = enter.append("g")
              .attr("class", d => nodeClass(d))
              .on("click", (event, d) => selectNode(d.id))
              .call(dragBehavior());
            g.append("circle").attr("class", "node-shape circle-shape");
            g.append("rect").attr("class", "node-shape rect-shape");
            g.append("text").attr("class", "node-label");
            g.append("title");
            return g;
          },
          update => update.attr("class", d => nodeClass(d)),
          exit => exit.remove()
        );

      nodeSel.select("circle")
        .style("display", d => isStoryNode(d) ? "none" : null)
        .attr("r", d => d.r);
      nodeSel.select("rect")
        .style("display", d => isStoryNode(d) ? null : "none")
        .attr("x", d => -Math.min(66, Math.max(42, d.name.length * 13)) / 2)
        .attr("y", d => -18)
        .attr("width", d => Math.min(66, Math.max(42, d.name.length * 13)))
        .attr("height", 36)
        .attr("rx", 12);
      nodeSel.select("text")
        .text(d => labelForNode(d))
        .attr("font-size", d => labelSize(d))
        .attr("dy", d => isStoryNode(d) ? 0 : 1);
      nodeSel.select("title")
        .text(d => `${d.name}｜${d.campLabel}｜${d.typeLabel}\\n${d.kidIntro || d.description || ""}`);

      simulation = d3.forceSimulation(simNodes)
        .force("link", d3.forceLink(simLinks).id(d => d.id).distance(linkDistance).strength(0.42))
        .force("charge", d3.forceManyBody().strength(d => isStoryNode(d) ? -250 : -380))
        .force("center", d3.forceCenter(center[0], center[1]))
        .force("x", d3.forceX(d => campCenter(d.camp, width, height)[0]).strength(0.035))
        .force("y", d3.forceY(d => campCenter(d.camp, width, height)[1]).strength(0.035))
        .force("collision", d3.forceCollide().radius(d => d.r + 12).iterations(1))
        .alpha(reason === "init" || reason === "chapter" || reason === "mode" ? 0.82 : 0.34)
        .alphaDecay(reason === "limit" || reason === "categories" ? 0.062 : 0.044)
        .on("tick", () => {
          linkSel
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
          nodeSel.attr("transform", d => `translate(${d.x},${d.y})`);
        })
        .on("end", () => {
          simNodes.forEach(node => posCache.set(node.id, { x: node.x, y: node.y }));
        });

      updateVisualState();
      renderRoster();
      renderPathResult(state.pathIds);
    }

    function buildGraph() {
      const preset = currentPreset();
      const inRangeNodes = nodes.filter(node => overlaps(node, preset));
      const inRangeRels = relationships.filter(rel =>
        state.enabledCategories.has(rel.kidCategory) &&
        overlaps(rel, preset) &&
        nodeById.has(rel.source) &&
        nodeById.has(rel.target)
      );

      if (state.pathIds.length) {
        const pathSet = new Set(state.pathIds);
        const pathLinks = [];
        const supportLinks = [];
        for (let i = 0; i < state.pathIds.length - 1; i += 1) {
          const rel = bestRelBetween(state.pathIds[i], state.pathIds[i + 1], inRangeRels);
          if (rel) pathLinks.push(rel);
          pathSupportBetween(state.pathIds[i], state.pathIds[i + 1], inRangeRels, preset, 2).forEach(item => {
            pathSet.add(item.node.id);
            supportLinks.push(...item.rels);
          });
        }
        const linkedMore = inRangeRels.filter(rel => pathSet.has(rel.source) && pathSet.has(rel.target));
        return dedupeGraph([...pathSet].map(id => nodeById.get(id)).filter(Boolean), [...pathLinks, ...linkedMore, ...supportLinks]);
      }

      if (state.mode === "battle") {
        const selected = nodeById.get(state.selectedId);
        const eventId = selected && isStoryNode(selected) ? selected.id : topEventForPreset(preset)?.id;
        if (eventId) return localGraph(eventId, inRangeRels, state.nodeLimit, true);
      }

      if (state.mode === "relation" && !state.selectedId) {
        const links = inRangeRels
          .filter(rel => ["defeat", "enemy", "ally", "strategy", "family"].includes(rel.kidCategory))
          .sort(relImportance)
          .slice(0, state.nodeLimit + 12);
        const ids = new Set();
        links.forEach(rel => { ids.add(rel.source); ids.add(rel.target); });
        return dedupeGraph([...ids].map(id => nodeById.get(id)).filter(Boolean).slice(0, state.nodeLimit), links);
      }

      return localGraph(state.selectedId, inRangeRels, state.nodeLimit, state.mode === "relation");
    }

    function storyGraph(preset, inRangeNodes, inRangeRels) {
      const eventNodes = inRangeNodes
        .filter(node => isStoryNode(node))
        .sort(nodeImportance)
        .slice(0, Math.max(10, Math.floor(state.nodeLimit * 0.45)));
      const eventIds = new Set(eventNodes.map(node => node.id));
      const storyLinks = inRangeRels
        .filter(rel => eventIds.has(rel.source) || eventIds.has(rel.target))
        .sort((a, b) => relImportance(b) - relImportance(a));
      const ids = new Set(eventIds);
      for (const rel of storyLinks) {
        const source = nodeById.get(rel.source);
        const target = nodeById.get(rel.target);
        const otherId = eventIds.has(rel.source) ? rel.target : rel.source;
        const other = nodeById.get(otherId);
        if (!other || isStoryNode(other)) continue;
        if (!["character", "faction", "army", "location", "strategy"].includes(other.type)) continue;
        if (ids.size < state.nodeLimit) ids.add(otherId);
      }
      const links = inRangeRels
        .filter(rel => ids.has(rel.source) && ids.has(rel.target))
        .sort((a, b) => relImportance(b) - relImportance(a))
        .slice(0, state.nodeLimit * 2);
      return dedupeGraph([...ids].map(id => nodeById.get(id)).filter(Boolean), links);
    }

    function localGraph(centerId, rels, limit, relationFirst = false) {
      const centerNode = nodeById.get(centerId);
      if (!centerNode) return { nodes: [], links: [] };
      const activeCampFilter = state.mode === "person" && state.campFilter !== "all";
      const adjacent = rels
        .filter(rel => rel.source === centerId || rel.target === centerId)
        .sort((a, b) => {
          const ac = categoryWeight(a.kidCategory);
          const bc = categoryWeight(b.kidCategory);
          if (relationFirst && ac !== bc) return bc - ac;
          return relImportance(b) - relImportance(a);
        });
      const ids = new Set([centerId]);
      const links = [];
      for (const rel of adjacent) {
        const otherId = rel.source === centerId ? rel.target : rel.source;
        const other = nodeById.get(otherId);
        if (!other) continue;
        if (activeCampFilter && !isStoryNode(other) && !campMatchesFilter(other.camp)) continue;
        if (ids.size < limit) ids.add(otherId);
        if (ids.has(otherId)) links.push(rel);
      }
      const closedLinks = rels
        .filter(rel => ids.has(rel.source) && ids.has(rel.target))
        .sort(relImportance)
        .slice(0, Math.max(limit * 2, 80));
      return dedupeGraph([...ids].map(id => nodeById.get(id)).filter(Boolean), [...links, ...closedLinks]);
    }

    function dedupeGraph(inputNodes, inputLinks) {
      const nodeMap = new Map();
      inputNodes.forEach(node => { if (node) nodeMap.set(node.id, node); });
      const linkMap = new Map();
      inputLinks.forEach(rel => {
        if (!nodeMap.has(rel.source) || !nodeMap.has(rel.target)) return;
        const key = [rel.source, rel.target, rel.kidCategory, rel.relationType].sort().join("|");
        const previous = linkMap.get(key);
        if (!previous || relImportance(rel) > relImportance(previous)) linkMap.set(key, rel);
      });
      const finalNodes = [...nodeMap.values()].sort(nodeImportance);
      const finalLinks = [...linkMap.values()].sort((a, b) => relImportance(b) - relImportance(a));
      return { nodes: finalNodes, links: finalLinks };
    }

    function updatePanels() {
      const selected = nodeById.get(state.selectedId) || nodes[0];
      const preset = currentPreset();
      dom.selectedName.textContent = selected.name;
      dom.selectedMeta.textContent = `${selected.campLabel || "未分類"}・${selected.typeLabel || selected.type}`;
      dom.selectedIntro.textContent = selected.kidIntro || selected.description || "點選圖上的節點，就能看到它的故事線。";
      dom.selectedBadge.textContent = selected.name.slice(0, 1);
      dom.selectedBadge.className = `selected-badge camp-${selected.camp || "neutral"}`;
      dom.thinkingPrompt.textContent = THINKING_PROMPTS[preset.id] || THINKING_PROMPTS.all;
      dom.thinkingNote.value = savedNotes[preset.id] || "";

      renderThinkingPromptList(selected, preset);
      renderRelationGroups(selected, preset);
      renderEvents(selected, preset);
      renderTraits(selected);
      renderEvidenceTags(selected, preset);
      updateMapTitle(selected, preset);
      renderPathResult(state.pathIds);
      updateHashState();
    }

    function updateMapTitle(selected, preset) {
      const modeLabel = {
        person: "人物關係",
        battle: "事件人物",
        relation: "關係路徑",
      }[state.mode];
      if (state.pathIds.length) {
        dom.mapTitle.textContent = `關係路徑：${state.pathIds.map(id => nodeById.get(id)?.name).filter(Boolean).join(" → ")}`;
      } else if (state.mode === "battle") {
        dom.mapTitle.textContent = `${selected.name}：${modeLabel}`;
      } else {
        dom.mapTitle.textContent = `${selected.name}：${modeLabel}`;
      }
    }

    function renderMissions(selected, preset) {
      const missions = buildMissions(selected, preset);
      dom.missionList.replaceChildren(...missions.map((mission, index) => {
        const row = document.createElement("div");
        row.className = "mission";
        const num = document.createElement("div");
        num.className = "mission-num";
        num.textContent = String(index + 1);
        const text = document.createElement("div");
        const strong = document.createElement("strong");
        strong.textContent = mission.title;
        const span = document.createElement("span");
        span.textContent = mission.desc;
        text.append(strong, span);
        row.append(num, text);
        return row;
      }));
    }

    function buildMissions(selected, preset) {
      if (state.mode === "battle" || (selected && isStoryNode(selected))) {
        return [
          { title: "找出參與者", desc: "先點戰役或故事旁邊的人物，看看哪些陣營同時出現。" },
          { title: "標出轉折", desc: "找一條計策或交戰線，說說它讓故事往哪裡轉。" },
          { title: "提出判斷", desc: "這場事件中誰的決定最重要？用一條關係作證據。" },
        ];
      }
      if (state.mode === "relation") {
        return [
          { title: "分類關係", desc: "把線分成合作、對手、計策、主從，再說明差別。" },
          { title: "找最短路徑", desc: "用右側路徑工具找兩個人物中間隔了哪些人。" },
          { title: "用證據說話", desc: "點一條關係附近的人物，讀出它的章回描述。" },
        ];
      }
      return [
        { title: `認識${selected.name}`, desc: "先看他被哪些人包圍，再挑一條線讀描述。" },
        { title: "用陣營縮小範圍", desc: "只看魏、蜀、吳或群雄，觀察不同角色和他的距離。" },
        { title: "連到一場事件", desc: "找出他參加或影響過的戰役，說說那件事的重要性。" },
      ];
    }

    function renderThinkingPromptList(selected, preset) {
      const prompts = thinkingPromptsFor(selected, preset);
      dom.thinkingPromptList.replaceChildren(...prompts.map(item => {
        const card = document.createElement("div");
        card.className = "thinking-card";
        const title = document.createElement("strong");
        title.textContent = item.title;
        const body = document.createElement("span");
        body.textContent = item.body;
        card.append(title, body);
        return card;
      }));
    }

    function thinkingPromptsFor(selected, preset) {
      if (state.mode === "battle" || isStoryNode(selected)) {
        return [
          { title: "誰在現場", body: "列出這場事件中的三個重要人物，分別屬於哪一方？" },
          { title: "誰改變局勢", body: "找一條計策、合作或交戰線，說明它讓局勢怎麼變。" },
          { title: "你會怎麼做", body: "如果你在這場事件中，你會先保護人、城池，還是盟友？" },
        ];
      }
      if (state.mode === "relation") {
        return [
          { title: "看中間的人", body: "兩個人物之間隔著誰？這個中間人是朋友、對手，還是主從關係？" },
          { title: "判斷遠近", body: "這條路徑越短，代表故事裡互動越直接。你同意嗎？" },
          { title: "換一組比較", body: "再找另一組人物，比較哪一組關係更複雜。" },
        ];
      }
      return [
        { title: "先觀察", body: `${selected.name} 身邊最多的是合作、對手，還是主從關係？` },
        { title: "找證據", body: "點右側的關係分類，挑一條你看得懂的描述當證據。" },
        { title: "做判斷", body: `你覺得 ${selected.name} 的選擇讓他更安全，還是更危險？` },
      ];
    }

    function renderRelationGroups(selected, preset) {
      if (state.mode === "battle") {
        renderBattleEventBook(preset);
        return;
      }
      const groups = relationGroupsFor(selected.id, preset);
      if (!groups.length) {
        dom.relationGroups.replaceChildren(emptyState("這個範圍內沒有足夠的可分類關係，可以先切換章節。"));
        return;
      }
      dom.relationGroups.replaceChildren(...groups.map(group => {
        const details = document.createElement("details");
        details.className = `relation-section cat-${group.id}`;
        details.open = true;
        const summary = document.createElement("summary");
        const label = document.createElement("span");
        label.className = "relation-title";
        label.textContent = group.label;
        const count = document.createElement("span");
        count.className = "relation-count";
        count.textContent = String(group.items.length);
        summary.append(label, count);
        const items = document.createElement("div");
        items.className = "relation-items";
        group.items.slice(0, 7).forEach(item => {
          const row = document.createElement("div");
          row.className = "relation-item";
          const btn = document.createElement("button");
          btn.type = "button";
          btn.textContent = item.name;
          btn.addEventListener("click", () => selectNode(item.id));
          const desc = document.createElement("span");
          desc.className = "relation-desc";
          desc.textContent = `${item.relationType}，第 ${chapterLabel(item.rel)} 回。${item.description}`;
          row.append(btn, desc);
          items.append(row);
        });
        details.append(summary, items);
        return details;
      }));
    }

    function renderBattleEventBook(preset) {
      const query = state.battleQuery.trim().toLowerCase();
      const events = nodes
        .filter(node => isStoryNode(node) && overlaps(node, preset))
        .filter(node => !query || searchText(node).toLowerCase().includes(query) || (node.description || "").toLowerCase().includes(query))
        .sort(nodeImportance)
        .slice(0, 14);
      if (!events.length) {
        dom.relationGroups.replaceChildren(emptyState("找不到符合的戰役或事件，試試輸入赤壁、官渡、長坂。"));
        return;
      }
      dom.relationGroups.replaceChildren(...events.map(eventNode => {
        const row = document.createElement("div");
        row.className = "event-item";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = eventNode.name;
        btn.addEventListener("click", () => selectNode(eventNode.id));
        const meta = document.createElement("span");
        meta.className = "event-meta";
        meta.textContent = `第 ${chapterLabel(eventNode)} 回｜${eventNode.kidIntro || eventNode.description || ""}`;
        row.append(btn, meta);
        return row;
      }));
    }

    function relationGroupsFor(nodeId, preset) {
      const rels = (relsByNode.get(nodeId) || [])
        .filter(rel => state.enabledCategories.has(rel.kidCategory) && overlaps(rel, preset))
        .sort((a, b) => relImportance(b) - relImportance(a));
      const bucket = new Map();
      rels.forEach(rel => {
        const otherId = rel.source === nodeId ? rel.target : rel.source;
        const other = nodeById.get(otherId);
        if (!other) return;
        const key = directionalGroup(nodeId, rel);
        if (!bucket.has(key.id)) bucket.set(key.id, { id: key.id, label: key.label, items: [] });
        bucket.get(key.id).items.push({
          id: other.id,
          name: other.name,
          rel,
          relationType: rel.relationType,
          description: rel.description || rel.kidLabel,
        });
      });
      return [...bucket.values()].sort((a, b) => categoryWeight(b.id) - categoryWeight(a.id));
    }

    function directionalGroup(nodeId, rel) {
      if (rel.kidCategory === "defeat") {
        if (rel.source === nodeId) return { id: "defeat", label: "勝負/轉折的關聯性" };
        return { id: "defeated-by", label: "讓他受挫的人" };
      }
      if (rel.kidCategory === "enemy") return { id: "enemy", label: "對手與交戰" };
      if (rel.kidCategory === "ally") return { id: "ally", label: "合作與援助" };
      if (rel.kidCategory === "strategy") return { id: "strategy", label: "計策與說服" };
      if (rel.kidCategory === "command") return { id: "command", label: "主從與陣營" };
      if (rel.kidCategory === "family") return { id: "family", label: "親族與結義" };
      if (rel.kidCategory === "story") return { id: "story", label: "一起出現的故事" };
      if (rel.kidCategory === "place") return { id: "place", label: "地點線索" };
      return { id: rel.kidCategory, label: rel.kidLabel || "其他關係" };
    }

    function renderEvents(selected, preset) {
      const events = connectedEvents(selected.id, preset).slice(0, 8);
      if (!events.length) {
        dom.eventList.replaceChildren(emptyState("還沒有找到明確的事件連線。可以切換全局或戰役模式。"));
        return;
      }
      dom.eventList.replaceChildren(...events.map(item => {
        const row = document.createElement("div");
        row.className = "event-item";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = item.node.name;
        btn.addEventListener("click", () => {
          setMode("battle");
          selectNode(item.node.id);
        });
        const meta = document.createElement("span");
        meta.className = "event-meta";
        meta.textContent = `第 ${chapterLabel(item.rel || item.node)} 回｜${item.node.kidIntro || item.node.description || ""}`;
        row.append(btn, meta);
        return row;
      }));
    }

    function connectedEvents(nodeId, preset) {
      const direct = (relsByNode.get(nodeId) || [])
        .filter(rel => overlaps(rel, preset))
        .map(rel => {
          const otherId = rel.source === nodeId ? rel.target : rel.source;
          const node = nodeById.get(otherId);
          return node && isStoryNode(node) ? { node, rel, score: relImportance(rel) + (node.score || 0) } : null;
        })
        .filter(Boolean);
      if (direct.length) return direct.sort((a, b) => b.score - a.score);

      const rels = (relsByNode.get(nodeId) || []).filter(rel => overlaps(rel, preset));
      const eventCandidates = nodes.filter(node => isStoryNode(node) && overlaps(node, preset));
      const scored = eventCandidates.map(eventNode => {
        let score = 0;
        rels.forEach(rel => {
          const otherId = rel.source === nodeId ? rel.target : rel.source;
          if ((eventNode.description || "").includes(nodeById.get(otherId)?.name || "")) score += 2;
          if ((eventNode.description || "").includes(nodeById.get(nodeId)?.name || "")) score += 3;
        });
        return score > 0 ? { node: eventNode, rel: null, score: score + (eventNode.score || 0) / 100 } : null;
      }).filter(Boolean);
      return scored.sort((a, b) => b.score - a.score);
    }

    function renderTraits(node) {
      const entries = Object.entries(node.traits || {});
      if (!entries.length) {
        dom.traitList.replaceChildren(emptyState("這個人物還沒有手動設定能力標籤，先用關係線觀察他的行動。"));
        return;
      }
      dom.traitList.replaceChildren(...entries.map(([label, value]) => {
        const row = document.createElement("div");
        row.className = "trait";
        const name = document.createElement("span");
        name.textContent = label;
        const bar = document.createElement("span");
        bar.className = "trait-bar";
        const fill = document.createElement("i");
        fill.style.width = `${Math.max(8, Math.min(100, Number(value) * 20))}%`;
        bar.append(fill);
        const score = document.createElement("span");
        score.textContent = `${value}/5`;
        row.append(name, bar, score);
        return row;
      }));
    }

    function renderEvidenceTags(node, preset) {
      const rels = (relsByNode.get(node.id) || [])
        .filter(rel => overlaps(rel, preset))
        .sort((a, b) => relImportance(b) - relImportance(a))
        .slice(0, 5);
      dom.evidenceTags.replaceChildren(...rels.map(rel => {
        const tag = document.createElement("span");
        tag.className = "mini-tag";
        tag.textContent = `${rel.kidLabel}｜第 ${chapterLabel(rel)} 回`;
        return tag;
      }));
    }

    function renderRoster() {
      const preset = currentPreset();
      const query = state.query.toLowerCase();
      updateScenarioChrome();

      if (state.mode === "battle") {
        if (isMobileLayout()) {
          renderMobileBattleRoster(preset);
          return;
        }
        dom.rosterList.replaceChildren(emptyState("從右側「重點事件簿」選一場戰役或事件開始。"));
        return;
      }

      if (state.mode === "person" && !query && state.campFilter === "all") {
        if (isMobileLayout()) {
          dom.rosterList.replaceChildren();
          return;
        }
        dom.rosterList.replaceChildren(emptyState("上方先選劉備、曹操、孫權，或直接輸入人物名字。"));
        return;
      }

      const rosterItems = nodes
        .filter(node => rosterModeFilter(node))
        .filter(node => overlaps(node, preset))
        .filter(node => campMatchesFilter(node.camp) || isStoryNode(node))
        .filter(node => !query || searchText(node).toLowerCase().includes(query))
        .sort(nodeImportance)
        .slice(0, query ? 72 : (state.mode === "battle" ? 34 : 30));

      const groups = new Map();
      rosterItems.forEach(node => {
        const key = rosterGroupKey(node);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(node);
      });

      const orderedKeys = rosterGroupOrder().filter(key => groups.has(key));
      const blocks = orderedKeys.map(key => {
        const block = document.createElement("div");
        block.className = "group-block";
        const title = document.createElement("div");
        title.className = "group-title";
        const left = document.createElement("span");
        left.textContent = rosterGroupLabel(key);
        const right = document.createElement("span");
        right.textContent = String(groups.get(key).length);
        title.append(left, right);
        block.append(title);
        groups.get(key).forEach(node => block.append(roleButton(node)));
        return block;
      });

      dom.rosterList.replaceChildren(...(blocks.length ? blocks : [emptyState("找不到符合條件的角色或故事。")]));
    }

    function renderMobileBattleRoster(preset) {
      const query = (state.battleQuery || state.query).trim().toLowerCase();
      const events = nodes
        .filter(node => isStoryNode(node) && overlaps(node, preset))
        .filter(node => !query || searchText(node).toLowerCase().includes(query) || (node.description || "").toLowerCase().includes(query))
        .sort(nodeImportance)
        .slice(0, 12);
      if (!events.length) {
        dom.rosterList.replaceChildren(emptyState("找不到符合的戰役或事件，可以試試赤壁、官渡、長坂。"));
        return;
      }
      const block = document.createElement("div");
      block.className = "group-block";
      const title = document.createElement("div");
      title.className = "group-title";
      const left = document.createElement("span");
      left.textContent = "推薦故事與戰役";
      const right = document.createElement("span");
      right.textContent = String(events.length);
      title.append(left, right);
      block.append(title);
      events.forEach(eventNode => block.append(roleButton(eventNode)));
      dom.rosterList.replaceChildren(block);
    }

    function rosterCopy() {
      return {
        person: {
          panelTitle: "人物探險",
          searchLabel: "直接搜尋人物",
          placeholder: "搜尋：劉備、關羽、曹操",
        },
        battle: {
          panelTitle: "戰役現場",
          searchLabel: "找戰役或事件",
          placeholder: "搜尋：赤壁、官渡、長坂、三英",
        },
        relation: {
          panelTitle: "關係路徑",
          searchLabel: "直接搜尋人物",
          placeholder: "搜尋：曹操、周瑜、劉備",
        },
      }[state.mode] || {
        panelTitle: "人物探險",
        searchLabel: "直接搜尋人物",
        placeholder: "搜尋：劉備、關羽",
      };
    }

    function rosterModeFilter(node) {
      if (state.mode === "battle") return isStoryNode(node);
      if (state.mode === "relation") return node.type === "character";
      return node.type === "character";
    }

    function rosterGroupKey(node) {
      if (state.mode === "battle") return "story";
      if (state.mode === "relation") return "focus";
      return campGroupKey(node.camp);
    }

    function rosterGroupOrder() {
      if (state.mode === "battle") return ["story"];
      if (state.mode === "relation") return ["focus"];
      return CAMP_ORDER;
    }

    function rosterGroupLabel(key) {
      if (key === "story") return "推薦故事與戰役";
      if (key === "focus") return "推薦關係焦點";
      return CAMP_LABELS[key] || key;
    }

    function roleButton(node) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `role-btn camp-${node.camp || "neutral"}${node.id === state.selectedId ? " is-selected" : ""}`;
      const dot = document.createElement("span");
      dot.className = "role-dot";
      const main = document.createElement("span");
      main.className = "role-main";
      const name = document.createElement("span");
      name.className = "role-name";
      name.textContent = node.name;
      const meta = document.createElement("span");
      meta.className = "role-meta";
      if (isStoryNode(node)) {
        meta.textContent = `${node.typeLabel || "故事"}・第 ${chapterLabel(node)} 回・${node.kidIntro || node.description || ""}`;
      } else if (state.mode === "relation") {
        meta.textContent = `${node.campLabel || "未分類"}・${node.typeLabel || ""}・${(relsByNode.get(node.id) || []).length} 條關係`;
      } else {
        meta.textContent = `${node.campLabel || "未分類"}・${node.typeLabel || ""}・第 ${chapterLabel(node)} 回`;
      }
      main.append(name, meta);
      const score = document.createElement("span");
      score.className = "role-score";
      score.textContent = isStoryNode(node) ? String(node.chapterStart || "") : String(node.degree || node.score || "");
      button.append(dot, main, score);
      button.addEventListener("click", () => {
        if (isStoryNode(node)) {
          setMode("battle");
        }
        if (state.mode === "relation" && !isStoryNode(node)) {
          fillPathEndpoint(node.name);
          return;
        }
        selectNode(node.id);
      });
      return button;
    }

    function fillPathEndpoint(name) {
      if (document.activeElement === dom.pathFrom) {
        dom.pathFrom.value = name;
        dom.pathTo.focus();
        return;
      }
      if (document.activeElement === dom.pathTo) {
        dom.pathTo.value = name;
        return;
      }
      if (!dom.pathFrom.value.trim()) {
        dom.pathFrom.value = name;
        dom.pathTo.focus();
        return;
      }
      dom.pathTo.value = name;
    }

    function selectNode(id) {
      if (!nodeById.has(id)) return;
      persistNote();
      state.selectedId = id;
      state.pathIds = [];
      if (isMobileLayout()) {
        document.body.classList.remove("mobile-notebook");
        setMobileSheetSnap("peek");
      }
      rebuildGraph("select");
      updatePanels();
    }

    function updateVisualState() {
      const selected = state.selectedId;
      const selectedNeighbors = new Set();
      currentGraph.links.forEach(link => {
        if (link.source === selected) selectedNeighbors.add(link.target);
        if (link.target === selected) selectedNeighbors.add(link.source);
      });
      if (nodeSel) {
        nodeSel
          .classed("is-selected", d => d.id === selected)
          .classed("is-dim", d => selected && d.id !== selected && !selectedNeighbors.has(d.id) && state.mode !== "camp" && !state.pathIds.includes(d.id));
      }
      if (linkSel) {
        linkSel
          .classed("is-highlighted", d => d.source.id === selected || d.target.id === selected || state.pathIds.includes(d.source.id) && state.pathIds.includes(d.target.id))
          .classed("is-dim", d => selected && !(d.source.id === selected || d.target.id === selected) && state.mode !== "camp" && !state.pathIds.includes(d.source.id));
      }
    }

    function shortestPath(fromId, toId) {
      const preset = currentPreset();
      const usableRels = relationships.filter(rel =>
        state.enabledCategories.has(rel.kidCategory) &&
        overlaps(rel, preset) &&
        nodeById.has(rel.source) &&
        nodeById.has(rel.target)
      );
      const adjacency = new Map();
      usableRels.forEach(rel => {
        if (!adjacency.has(rel.source)) adjacency.set(rel.source, []);
        if (!adjacency.has(rel.target)) adjacency.set(rel.target, []);
        adjacency.get(rel.source).push(rel.target);
        adjacency.get(rel.target).push(rel.source);
      });
      const queue = [fromId];
      const prev = new Map([[fromId, null]]);
      while (queue.length) {
        const id = queue.shift();
        if (id === toId) break;
        for (const next of adjacency.get(id) || []) {
          if (prev.has(next)) continue;
          prev.set(next, id);
          queue.push(next);
        }
      }
      if (!prev.has(toId)) return [];
      const path = [];
      let cursor = toId;
      while (cursor) {
        path.push(cursor);
        cursor = prev.get(cursor);
      }
      return path.reverse().slice(0, 9);
    }

    function renderPathResult(pathIds, message = "") {
      if (message) {
        dom.pathResult.replaceChildren(emptyState(message));
        return;
      }
      if (!pathIds || !pathIds.length) {
        dom.pathResult.replaceChildren(emptyState("可以試試「劉備 → 曹操」、「曹操 → 周瑜」、「劉備 → 孫權」，看他們中間經過哪些人物與事件。"));
        return;
      }
      const preset = currentPreset();
      const evidence = pathEvidence(pathIds, preset);
      const start = nodeById.get(pathIds[0]);
      const end = nodeById.get(pathIds[pathIds.length - 1]);
      const overview = document.createElement("div");
      overview.className = "path-overview";
      const headline = document.createElement("strong");
      headline.textContent = `${start?.name || "起點"} 和 ${end?.name || "終點"} 的關係是這樣串起來的`;
      const summary = document.createElement("span");
      const eventCount = evidence.reduce((sum, item) => sum + item.events.length, 0);
      const bridgeCount = evidence.reduce((sum, item) => sum + item.bridges.length, 0);
      const middleNodes = pathIds.slice(1, -1).map(id => nodeById.get(id)).filter(Boolean);
      const middlePeople = middleNodes.filter(node => node.type === "character").length;
      const middleEvents = middleNodes.filter(node => isStoryNode(node)).length;
      summary.textContent = `路徑包含 ${evidence.length} 段關係線，中間經過 ${middlePeople} 位人物與 ${middleEvents} 個事件；另外找到 ${eventCount} 個共同事件、${bridgeCount} 位可比較的橋接人物。`;
      const route = document.createElement("div");
      route.className = "path-route";
      pathIds.forEach((id, index) => {
        const node = nodeById.get(id);
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "path-node-pill";
        btn.textContent = node?.name || id;
        btn.addEventListener("click", () => selectNode(id));
        route.append(btn);
        if (index < pathIds.length - 1) {
          const arrow = document.createElement("span");
          arrow.className = "path-arrow";
          arrow.textContent = "→";
          route.append(arrow);
        }
      });
      overview.append(headline, summary, route);

      const cards = evidence.map((item, index) => {
        const from = nodeById.get(item.from);
        const to = nodeById.get(item.to);
        const card = document.createElement("div");
        card.className = `path-evidence cat-${item.rel?.kidCategory || "story"}`;
        const head = document.createElement("div");
        head.className = "path-evidence-head";
        const title = document.createElement("div");
        title.className = "path-evidence-title";
        const strong = document.createElement("strong");
        strong.textContent = `第 ${index + 1} 段：${from?.name || item.from} → ${to?.name || item.to}`;
        const chapter = document.createElement("span");
        chapter.textContent = item.rel ? `第 ${chapterLabel(item.rel)} 回｜${item.rel.relationType}` : "GraphRAG 找到兩者相鄰";
        title.append(strong, chapter);
        const badge = document.createElement("span");
        badge.className = "path-badge";
        badge.textContent = item.rel?.kidLabel || "關係線索";
        head.append(title, badge);
        const desc = document.createElement("p");
        desc.className = "path-desc";
        desc.textContent = item.rel?.description || `${from?.name || "這個人物"} 與 ${to?.name || "另一個人物"} 在這個章節範圍內有共同線索。`;
        card.append(head, desc);

        if (item.events.length) {
          card.append(pathEvidenceGroup("共同事件", item.events.map(event => ({
            id: event.node.id,
            label: `${event.node.name}｜第 ${chapterLabel(event.node)} 回`,
          }))));
        }
        if (item.bridges.length) {
          card.append(pathEvidenceGroup("可比較的中間人", item.bridges.map(bridge => ({
            id: bridge.node.id,
            label: `${bridge.node.name}｜${bridge.node.campLabel || "未分類"}`,
          }))));
        }
        return card;
      });
      dom.pathResult.replaceChildren(overview, ...cards);
    }

    function pathEvidenceGroup(labelText, items) {
      const group = document.createElement("div");
      group.className = "path-evidence-group";
      const label = document.createElement("label");
      label.textContent = labelText;
      const row = document.createElement("div");
      row.className = "path-chip-row";
      items.slice(0, 4).forEach(item => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "path-chip";
        chip.textContent = item.label;
        chip.addEventListener("click", () => selectNode(item.id));
        row.append(chip);
      });
      group.append(label, row);
      return group;
    }

    function pathEvidence(pathIds, preset) {
      const inRangeRels = relationships.filter(rel => overlaps(rel, preset));
      const items = [];
      for (let i = 0; i < pathIds.length - 1; i += 1) {
        const from = pathIds[i];
        const to = pathIds[i + 1];
        items.push({
          from,
          to,
          rel: bestRelBetween(from, to, inRangeRels),
          events: pathSupportBetween(from, to, inRangeRels, preset, 4),
          bridges: pathBridgePeopleBetween(from, to, inRangeRels, preset, 4),
        });
      }
      return items;
    }

    function pathSupportBetween(a, b, rels, preset, limit = 3) {
      const aEvents = new Map();
      const bEvents = new Map();
      rels.forEach(rel => {
        if (!overlaps(rel, preset)) return;
        const otherForA = rel.source === a ? rel.target : (rel.target === a ? rel.source : null);
        const otherForB = rel.source === b ? rel.target : (rel.target === b ? rel.source : null);
        if (otherForA && isStoryNode(nodeById.get(otherForA))) aEvents.set(otherForA, rel);
        if (otherForB && isStoryNode(nodeById.get(otherForB))) bEvents.set(otherForB, rel);
      });
      return [...aEvents.keys()]
        .filter(id => bEvents.has(id))
        .map(id => ({ node: nodeById.get(id), rels: [aEvents.get(id), bEvents.get(id)].filter(Boolean) }))
        .filter(item => item.node)
        .sort((x, y) => nodeImportance(y.node) - nodeImportance(x.node))
        .slice(0, limit);
    }

    function pathBridgePeopleBetween(a, b, rels, preset, limit = 3) {
      const aPeople = new Map();
      const bPeople = new Map();
      rels.forEach(rel => {
        if (!overlaps(rel, preset)) return;
        const otherForA = rel.source === a ? rel.target : (rel.target === a ? rel.source : null);
        const otherForB = rel.source === b ? rel.target : (rel.target === b ? rel.source : null);
        const aNode = otherForA ? nodeById.get(otherForA) : null;
        const bNode = otherForB ? nodeById.get(otherForB) : null;
        if (aNode && aNode.type === "character" && aNode.id !== b) aPeople.set(aNode.id, rel);
        if (bNode && bNode.type === "character" && bNode.id !== a) bPeople.set(bNode.id, rel);
      });
      return [...aPeople.keys()]
        .filter(id => bPeople.has(id))
        .map(id => ({ node: nodeById.get(id), rels: [aPeople.get(id), bPeople.get(id)].filter(Boolean) }))
        .filter(item => item.node)
        .sort((x, y) => nodeImportance(y.node) - nodeImportance(x.node))
        .slice(0, limit);
    }

    function bestRelBetween(a, b, rels) {
      return rels
        .filter(rel => (rel.source === a && rel.target === b) || (rel.source === b && rel.target === a))
        .sort((x, y) => relImportance(y) - relImportance(x))[0];
    }

    function currentPreset() {
      return DATA.chapterPresets.find(preset => preset.id === state.chapterPreset) || DATA.chapterPresets[0];
    }

    function topEventForPreset(preset) {
      return nodes
        .filter(node => isStoryNode(node) && overlaps(node, preset))
        .sort(nodeImportance)[0];
    }

    function overlaps(item, preset) {
      const start = item.chapterStart || (item.chapters && item.chapters[0]) || 1;
      const end = item.chapterEnd || start;
      return end >= preset.start && start <= preset.end;
    }

    function chapterLabel(item) {
      const start = item.chapterStart || (item.chapters && item.chapters[0]) || "";
      const end = item.chapterEnd || start;
      return start === end ? `${start}` : `${start}-${end}`;
    }

    function isStoryNode(node) {
      return node.kind === "story" || node.type === "event" || node.type === "battle";
    }

    function nodeImportance(a, b) {
      if (b) return nodeImportanceScore(b) - nodeImportanceScore(a);
      return node => nodeImportanceScore(node);
    }

    function nodeImportanceScore(node) {
      let score = (node.score || 0) + (node.degree || 0) * 5;
      if (node.isTrunk) score += 180;
      if (["曹操", "劉備", "關羽", "張飛", "呂布", "諸葛亮", "孫權", "周瑜", "趙雲"].includes(node.name)) score += 420;
      if (isStoryNode(node)) score += 60;
      return score;
    }

    function relImportance(rel) {
      return (rel.weight || 1) * 12 + categoryWeight(rel.kidCategory) + (rel.confidence || 0) * 10;
    }

    function categoryWeight(cat) {
      return {
        defeat: 95,
        enemy: 88,
        ally: 82,
        strategy: 78,
        command: 72,
        family: 70,
        story: 66,
        place: 42,
        office: 38,
        object: 34,
        other: 20,
        "defeated-by": 94,
      }[cat] || 10;
    }

    function nodeRadius(node) {
      const scale = isMobileLayout() ? 0.86 : 1;
      if (state.selectedId === node.id) return (isStoryNode(node) ? 28 : 34) * scale;
      if (["曹操", "劉備", "孫權", "諸葛亮"].includes(node.name)) return 32 * scale;
      if (node.degree >= 150) return 29 * scale;
      if (node.degree >= 60) return 25 * scale;
      if (node.degree >= 20) return 21 * scale;
      return (isStoryNode(node) ? 18 : 17) * scale;
    }

    function labelForNode(node) {
      if (state.visualStyle === "clean" && state.selectedId !== node.id && !state.pathIds.includes(node.id)) {
        if (isStoryNode(node)) return "";
        if (node.degree < 60) return "";
      }
      if (isStoryNode(node) && node.name.length > 6) return node.name.slice(0, 6);
      if (node.name.length > 5) return node.name.slice(0, 5);
      return node.name;
    }

    function labelSize(node) {
      const scale = isMobileLayout() ? 0.9 : 1;
      const fontScale = state.fontScale === "large" ? 1.28 : (state.fontScale === "small" ? 0.86 : 1);
      if (state.selectedId === node.id) return 16 * fontScale;
      if (node.degree >= 100) return 15 * scale * fontScale;
      if (isStoryNode(node)) return 12 * scale * fontScale;
      return 13 * scale * fontScale;
    }

    function nodeClass(node) {
      return `node camp-${node.camp || "neutral"} type-${node.type}${node.id === state.selectedId ? " is-selected" : ""}`;
    }

    function linkDistance(link) {
      if (link.kidCategory === "story") return 92;
      if (link.kidCategory === "family") return 86;
      if (link.kidCategory === "enemy" || link.kidCategory === "defeat") return 116;
      return 104;
    }

    function campCenter(camp, width, height) {
      const centers = {
        wei: [width * 0.35, height * 0.34],
        shu: [width * 0.34, height * 0.68],
        wu: [width * 0.72, height * 0.65],
        lords: [width * 0.65, height * 0.32],
        mixed: [width * 0.52, height * 0.50],
        neutral: [width * 0.50, height * 0.54],
      };
      return centers[camp] || centers.neutral;
    }

    function graphSize() {
      const rect = document.getElementById("graph").getBoundingClientRect();
      if (isMobileLayout()) {
        return { width: Math.max(320, rect.width), height: Math.max(420, rect.height) };
      }
      return { width: Math.max(640, rect.width), height: Math.max(480, rect.height) };
    }

    function dragBehavior() {
      return d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.25).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
          posCache.set(d.id, { x: d.x, y: d.y });
        });
    }

    function resetZoom() {
      svg.transition().duration(220).call(zoomBehavior.transform, d3.zoomIdentity);
    }

    function addNameKey(name, id) {
      if (!name) return;
      const key = normalizeName(name);
      if (!nameIndex.has(key)) nameIndex.set(key, []);
      nameIndex.get(key).push(id);
    }

    function normalizeName(name) {
      return String(name || "").trim().replace(/臺/g, "台").replace(/佈/g, "布").toLowerCase();
    }

    function findNodeId(name) {
      const key = normalizeName(name);
      const ids = nameIndex.get(key);
      if (ids && ids.length) return ids[0];
      const fuzzy = nodes
        .filter(node => searchText(node).includes(name))
        .sort(nodeImportance)[0];
      return fuzzy?.id;
    }

    function searchText(node) {
      return [node.name, node.typeLabel, node.campLabel, ...(node.aliases || [])].join(" ");
    }

    function persistNote() {
      const preset = currentPreset();
      savedNotes[preset.id] = dom.thinkingNote.value;
      localStorage.setItem("sanguo-v11-notes", JSON.stringify(savedNotes));
    }

    function emptyState(text) {
      const div = document.createElement("div");
      div.className = "empty-state";
      div.textContent = text;
      return div;
    }

    function debounce(fn, wait) {
      let timer = 0;
      return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), wait);
      };
    }
  })();
  </script>
</body>
</html>
"""


def write_html(payload: dict[str, Any], output: Path) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__GRAPH_DATA_JSON__", payload_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Sanguo Adventure Map v11 HTML.")
    parser.add_argument("--nodes", type=Path, default=DEFAULT_NODES_CSV)
    parser.add_argument("--relationships", type=Path, default=DEFAULT_RELS_CSV)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_payload(args.nodes, args.relationships, args.metadata)
    write_html(payload, args.output)
    print(json.dumps({
        "output": str(args.output.relative_to(REPO_ROOT)),
        "nodes": payload["summary"]["nodes"],
        "relationships": payload["summary"]["relationships"],
        "version": payload["version"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
