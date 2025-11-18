# Entry Lab Overview

**Purpose:** Build a data-driven entry enhancement system that can recommend, explain, and verify higher-probability entries for your Smart Money Concepts trading setups.

## Guiding Principles
- **Document everything:** Every detour task still follows Plan → Implement → Test so we keep traceability.
- **Data before models:** Use reliable funded-account trades to measure heuristics before involving large models.
- **Explainability:** Entry suggestions must cite the setups/confluences they rely on.
- **Measurable impact:** Each experiment reports whether it improves win rate, R-multiple, or drawdown protection.

## Workstreams
1. **Data Intake & Cleansing** – Finalize the funded CSV structure, validate fields, and catalog existing render scripts.
2. **Strategy Definition** – Capture POI/BOS/IFVG rules in a shared document until both of us can identify setups consistently.
3. **Entry Evaluator** – Prototype deterministic heuristics (e.g., 50% limits, confirmation stacks) and score them across historical trades.
4. **Advisor Integration** – Surface the evaluator inside the extension/chat with clear reasoning and outcome logging.
5. **Learning Loop** – Once deterministic baselines work, explore AI-enhanced detection or RAG contexts using the same metrics.

## Current Status
- Entry Lab docs scaffold created (plan/implementation/test folders).
- Plan template refreshed to capture context, decisions, and validation steps.
- Strategy document stub ready for collaborative editing.

_Update this overview as scopes or priorities change._
