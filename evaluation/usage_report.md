# LLM Usage and Cost Report

## Summary

- **Primary Provider:** Deterministic Fallback
- **Primary Model:** deterministic-rule-engine
- **Total Requests Processed:** 250
- **Successful External LLM API Calls:** 0
- **Fallback Explanations Used:** 250
- **Total Input Tokens:** 14,670 (estimated)
- **Total Output Tokens:** 6,523 (estimated)
- **Total Tokens:** 21,193 (estimated)
- **Average Tokens / Request:** 84.8 (estimated)
- **Total Estimated Cost:** $0.000000 USD
- **Average Cost / Request:** $0.000000 USD

## Architectural Boundary Note

- The deterministic financial engine is solely responsible for all financial decisions: `amount_safe_to_pay`, `affordability_status`, `recommended_payment_method`, `payment_plan`, `earliest_date_for_full_payment`, and `spending_changes_needed`.
- The LLM is strictly constrained to generating natural-language explanations from the precomputed decision facts.
- In the absence of an API key or during network unavailability, the deterministic fallback explanation generator creates fully grounded, consistent explanations with 0 external API cost.
- When running in deterministic fallback mode, exactly 0 external API calls occur and external API cost is $0.000000 USD. Reported token counts represent estimated token equivalents (approx. 4 characters/token) for computational footprint analysis.

## Detailed Breakdown by Status

| Provider | Model | Requests | Input Tokens (est.) | Output Tokens (est.) | Total Tokens (est.) | Estimated Cost (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| fallback | deterministic-fallback | 250 | 14,670 | 6,523 | 21,193 | $0.000000 |

## Cost Rates Applied

- **Gemini 1.5 Flash:** $0.075 / 1M input tokens, $0.30 / 1M output tokens.
- **Deterministic Fallback:** $0.00 / 1M tokens (local evaluation).

*Report generated at 2026-09-13 06:52:27 UTC*