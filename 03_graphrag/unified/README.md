# 三國演義 001-060 Half-Book Global Merge

- Blocks: `6`
- Chapters: `1` to `60`
- Block entities: `3465`
- Global entities: `2663`
- Merged entity delta: `802`
- Block relationships: `5181`
- Global relationships: `5049`
- Deduped relationship delta: `87`
- Dropped relationships: `45`
- Cross-type name candidates: `16`

## Files

- `unified_entities.jsonl`
- `unified_relationships.jsonl`
- `block_entity_to_global.jsonl`
- `merge_decisions.jsonl`
- `merge_reasons.jsonl`
- `cross_type_name_candidates.jsonl`
- `dropped_relationships.jsonl`
- `merge_summary.json`

## Notes

- Global merge uses block-level unified entities as the source rows.
- Entity merge is still conservative and only merges within the same entity type.
- Relationship dedupe groups by global source, global target, and relationship type.
