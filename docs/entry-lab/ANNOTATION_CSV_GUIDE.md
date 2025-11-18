# Annotation CSV Guide

File: `server/data/entry_lab_annotations_template.csv`

Columns (all optional except `trade_id`):
- `trade_id`: unique id for the trade.
- `symbol`: e.g., 6EZ5, MNQZ5, MCLZ5, SILZ5, MGCZ5.
- `direction`: long|short.
- `entry_time`: ISO timestamp (prefer tz-aware, e.g., 2025-10-23T01:40:06-05:00).
- `session`: e.g., London, Asia, New York.
- `entry_method`: e.g., poi50, ifvg, micro, other (use poi50 as base if unsure).
- `poi_low`,`poi_high`: POI bounds.
- `bos_level`: BOS price for the structure.
- `fractal_range_low`,`fractal_range_high`: initial trading range bounds (optional).
- `fractal_target`: next target fractal (where the BOS would be).
- `ifvg_low`,`ifvg_high`: IFVG bounds if present (leave blank if not used).
- `micro_shift`: true|false if 1m structure flipped inside POI (manual tag if on 1m).
- `micro_entry_price`,`micro_sl`,`micro_tp`: optional micro-based entry/SL/TP if you want to simulate micro trigger.
- `outcome`: win|loss|unknown (manual label if you can’t simulate).
- `exit_price`: fill if you know the exit/target hit; else leave blank.
- `contracts`: number of contracts you intend to trade (optional, for risk calc).
- `size_hint`: freeform (e.g., “risk $100”, “auto-size to cap”).
- `note`: any free text (discipline/session quirks).
- `micro_shift` is a key gate for A+ setups; use true/false if you review 1m. If unknown, leave blank (advisor will treat as lower grade until tagged).

Usage:
- Add one row per trade. Blank cells are allowed. Focus on POI/BOS/fractal target, `micro_shift`, and entry_time/symbol/direction as minimums.
- Save/append your rows and we’ll merge into `server/analytics/entry_lab_annotations.json` when ready.
- To dry-run a single row locally: save it as JSON and run `python server/analytics/run_advisor.py --row-json row.json` (activate venv first). Adjust `--remaining-drawdown` if needed.
