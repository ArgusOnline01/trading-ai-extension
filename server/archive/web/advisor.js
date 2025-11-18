// Minimal helper to call the chat advisor endpoint from UI.
export async function evaluateAdvisor(input) {
  const params = new URLSearchParams({
    remaining_drawdown: input.remaining_drawdown ?? 500,
    risk_cap_pct: input.risk_cap_pct ?? 0.1,
    require_grade: input.require_grade ?? "A+",
    require_micro: input.require_micro ?? false,
  });

  const resp = await fetch(`/chat/advisor/evaluate?${params.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input.payload),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Advisor request failed: ${resp.status} ${text}`);
  }
  return resp.json();
}
