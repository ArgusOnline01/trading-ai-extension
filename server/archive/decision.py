from typing import Dict, Any

# Minimal chat prompt context builder for Phase 3 advisor integration.
# Vision analysis has been removed; this now just provides a small helper
# to build instructions and include structured setup data plus recent turns.


def build_chat_prompt(
    system_instructions: str,
    setup: Dict[str, Any] | None = None,
    recent_turns: list[dict] | None = None,
    advisor_result: Dict[str, Any] | None = None,
) -> list[dict]:
    """
    Build a minimal message list for the chat model:
      - system instructions
      - structured setup data (if provided)
      - advisor result (if provided)
      - recent turns (user/assistant messages)
    """
    messages: list[dict] = []
    messages.append({"role": "system", "content": system_instructions.strip()})

    setup_lines = []
    if setup:
        for k in [
            "trade_id",
            "symbol",
            "direction",
            "session",
            "poi_low",
            "poi_high",
            "fractal_target",
            "micro_shift",
            "ifvg_present",
            "entry_method",
            "contracts",
            "entry_price",
            "sl",
            "tp",
        ]:
            if k in setup and setup[k] is not None:
                setup_lines.append(f"{k}: {setup[k]}")
    if setup_lines:
        messages.append({"role": "system", "content": "Setup context:\n" + "\n".join(setup_lines)})

    if advisor_result:
        messages.append(
            {
                "role": "system",
                "content": f"Advisor result: decision={advisor_result.get('decision')}, "
                f"grade={advisor_result.get('grade')}, score={advisor_result.get('score')}, "
                f"rule={advisor_result.get('rule')}, risk={advisor_result.get('risk')}",
            }
        )

    if recent_turns:
        messages.extend(recent_turns)

    return messages
