"""
Main executable entrypoint for HackerRank Orchestrate September 2026 "Buy or Wait?" challenge.

Usage:
    python3 code/main.py
    python code/main.py

Pipeline:
1. Evidence Resolution & Normalization (Phase 2)
2. Recurrence Detection & 90-Day Timeline Reconstruction (Phase 3)
3. 90-Day Cash-Flow Affordability Simulation (Phase 4 / 4.1)
4. Payment Plan Generation & Strategy Ranking (Phase 5)
5. Spending Changes Optimization (Phase 6 / 6.1)
6. Grounded Decision Explanations & Token Accounting (Phase 7)
7. Final Output Schema Validation (Phase 7)
8. output.csv & evaluation/usage_report.md Generation
"""

import argparse
import csv
from datetime import datetime
from decimal import Decimal
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure code directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from evidence import EvidenceResolver
from financial_engine import TimelineBuilder
from affordability import AffordabilitySimulator
from spending_optimizer import SpendingChangeOptimizer
from planner import PaymentPlanner, format_money
from explanation import ExplanationGenerator, TokenAccountant
from validator import OutputValidator, REQUIRED_COLUMNS


def run_pipeline(
    dataset_dir: Optional[str] = None,
    output_path: Optional[str] = None,
    report_path: Optional[str] = None,
    requests_subset: Optional[List[str]] = None,
) -> int:
    """Execute end-to-end evaluation pipeline."""
    start_time = time.time()
    print("=" * 65)
    print("HackerRank Orchestrate September 2026: Buy or Wait? Engine")
    print("=" * 65)

    # 1. Resolve filesystem paths
    actual_dataset_dir = dataset_dir or os.path.join(REPO_ROOT, "dataset")
    actual_output_path = output_path or os.path.join(REPO_ROOT, "output.csv")
    actual_report_path = report_path or os.path.join(REPO_ROOT, "evaluation", "usage_report.md")

    print(f"Dataset directory: {actual_dataset_dir}")
    print(f"Output target:     {actual_output_path}")
    print(f"Usage report:      {actual_report_path}")
    print("-" * 65)

    # 2. Initialize pipeline components
    print("Initializing financial components and evidence resolver...")
    resolver = EvidenceResolver(dataset_dir=actual_dataset_dir)
    builder = TimelineBuilder(resolver)
    simulator = AffordabilitySimulator(resolver, builder)
    spending_optimizer = SpendingChangeOptimizer(resolver, builder, simulator)
    planner = PaymentPlanner(resolver, builder, simulator, spending_optimizer)
    
    accountant = TokenAccountant()
    explanation_gen = ExplanationGenerator(accountant=accountant)

    # Determine requests to evaluate
    if requests_subset is not None:
        all_request_ids = requests_subset
    else:
        # Default: evaluation requests from dataset/requests.csv as specified in problem_statement.md
        requests_csv_path = os.path.join(actual_dataset_dir, "requests.csv")
        if os.path.exists(requests_csv_path):
            with open(requests_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                all_request_ids = [r["request_id"].strip() for r in reader if r.get("request_id")]
        else:
            all_request_ids = list(resolver.requests.keys())
            all_request_ids.sort(key=lambda x: (len(x), x))
    total_reqs = len(all_request_ids)
    print(f"Total requests to process: {total_reqs}")

    output_rows: List[Dict[str, Any]] = []
    decisions_map: Dict[str, Any] = {}
    status_counts: Dict[str, int] = {}
    method_counts: Dict[str, int] = {}
    sc_counts: Dict[str, int] = {"none": 0, "active": 0}
    success_count = 0
    failure_count = 0

    print("Evaluating financial requests and generating explanations...")
    for idx, rid in enumerate(all_request_ids, 1):
        try:
            req = resolver.requests[rid]
            prof = resolver.profiles[req.user_id]
            state = resolver.build_normalized_state(req.user_id, rid)
            events_map = {e.event_id: e for e in state.events}

            # Deterministic decision from planner
            decision = planner.evaluate_request(req.user_id, rid)
            decisions_map[rid] = decision

            # AI / Fallback explanation
            explanation = explanation_gen.generate_explanation(decision, prof, req, events_map)

            # Assemble validated row
            row = {
                "request_id": rid,
                "amount_safe_to_pay": format_money(decision.amount_safe_to_pay),
                "affordability_status": decision.affordability_status,
                "recommended_payment_method": decision.recommended_payment_method,
                "payment_plan": decision.payment_plan,
                "earliest_date_for_full_payment": decision.earliest_date_for_full_payment or "",
                "spending_changes_needed": decision.spending_changes_needed,
                "decision_explanation": explanation,
            }
            output_rows.append(row)
            success_count += 1

            # Tally stats
            status_counts[decision.affordability_status] = status_counts.get(decision.affordability_status, 0) + 1
            method_counts[decision.recommended_payment_method] = method_counts.get(decision.recommended_payment_method, 0) + 1
            if decision.spending_changes_needed == "none":
                sc_counts["none"] += 1
            else:
                sc_counts["active"] += 1

            if idx % 50 == 0 or idx == total_reqs:
                print(f"  Processed {idx}/{total_reqs} requests ({idx / total_reqs * 100:.1f}%)")

        except Exception as e:
            print(f"  ERROR processing {rid}: {e}")
            failure_count += 1

    elapsed = time.time() - start_time
    throughput = total_reqs / elapsed if elapsed > 0 else 0.0

    print("-" * 65)
    print("Running final validation checks...")
    eval_requests_dict = {rid: resolver.requests[rid] for rid in all_request_ids if rid in resolver.requests}
    is_valid, validation_errors = OutputValidator.validate_dataset(
        output_rows,
        requests=eval_requests_dict,
        decisions=decisions_map,
        expected_count=total_reqs,
    )

    if not is_valid:
        print(f"CRITICAL VALIDATION ERROR: Found {len(validation_errors)} validation errors!")
        for err in validation_errors[:10]:
            print(f"  - {err}")
        return 1

    print("All validation checks PASSED (100% schema & integrity compliance).")

    # 3. Write output.csv
    print(f"Writing {len(output_rows)} rows to {actual_output_path}...")
    os.makedirs(os.path.dirname(os.path.abspath(actual_output_path)), exist_ok=True)
    with open(actual_output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    # 4. Generate usage report
    report_content = accountant.generate_report_markdown()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(actual_report_path)), exist_ok=True)
        with open(actual_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Saved usage report to {actual_report_path}")
    except Exception as e:
        print(f"Warning: Could not save usage report to {actual_report_path}: {e}")

    # 5. Output summary metrics
    print("=" * 65)
    print("EXECUTION SUMMARY")
    print("=" * 65)
    print(f"Total Requests:       {total_reqs}")
    print(f"Successful:           {success_count}")
    print(f"Failed:               {failure_count}")
    print(f"Total Time:           {elapsed:.2f} seconds")
    print(f"Throughput:           {throughput:.2f} requests/second")
    print()
    print("Affordability Status Distribution:")
    for st, count in sorted(status_counts.items()):
        print(f"  {st:25s}: {count:4d} ({count / total_reqs * 100:.1f}%)")
    print()
    print("Recommended Payment Method Distribution:")
    for pm, count in sorted(method_counts.items()):
        print(f"  {pm:25s}: {count:4d} ({count / total_reqs * 100:.1f}%)")
    print()
    print("Spending Changes Distribution:")
    print(f"  None (no changes)        : {sc_counts['none']:4d} ({sc_counts['none'] / total_reqs * 100:.1f}%)")
    print(f"  Active Spending Changes  : {sc_counts['active']:4d} ({sc_counts['active'] / total_reqs * 100:.1f}%)")
    print()
    print("LLM & Token Accounting Summary:")
    print(f"  Total Calls:             {accountant.total_calls}")
    print(f"  Fallback Explanations:   {accountant.fallback_calls}")
    print(f"  Total Input Tokens:      {accountant.total_input_tokens:,}")
    print(f"  Total Output Tokens:     {accountant.total_output_tokens:,}")
    print(f"  Total Tokens:            {accountant.total_tokens:,}")
    print(f"  Avg Tokens / Request:    {accountant.avg_tokens_per_request:.1f}")
    print(f"  Estimated Cost:          ${accountant.total_estimated_cost:.6f} USD")
    print("=" * 65)
    return 0


def main():
    parser = argparse.ArgumentParser(description="HackerRank Buy or Wait Financial Engine")
    parser.add_argument("--dataset-dir", default=None, help="Path to dataset directory")
    parser.add_argument("--output", default=None, help="Path to output CSV")
    parser.add_argument("--report", default=None, help="Path to usage report MD")
    parser.add_argument("--sample-only", action="store_true", help="Process only 25 sample requests")
    parser.add_argument("--eval-only", action="store_true", help="Process only 250 evaluation requests from requests.csv (default)")
    parser.add_argument("--all", action="store_true", help="Process all 275 requests (samples + evaluation)")
    args = parser.parse_args()

    subset = None
    if args.sample_only:
        subset = [f"request_{i:02d}" for i in range(1, 26)]
    elif args.all:
        subset = [f"request_{i:02d}" for i in range(1, 26)] + [
            f"request_{i:02d}" if i < 100 else f"request_{i}" for i in range(26, 276)
        ]
    elif args.eval_only:
        subset = [f"request_{i:02d}" if i < 100 else f"request_{i}" for i in range(26, 276)]

    sys.exit(run_pipeline(
        dataset_dir=args.dataset_dir,
        output_path=args.output,
        report_path=args.report,
        requests_subset=subset,
    ))


if __name__ == "__main__":
    main()
