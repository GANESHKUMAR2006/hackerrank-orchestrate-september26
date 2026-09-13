"""
Buy or Wait? - Financial Safety Decision Engine Demo Server
Serves the clean local demonstration UI for HackerRank Orchestrate judges.

Architectural Rule:
- READ ONLY presentation layer.
- NEVER recalculates financial decisions.
- output.csv is the authoritative source of truth.
"""

import csv
from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import os
import sys
import socket
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(CODE_DIR)

DATASET_DIR = os.path.join(REPO_ROOT, "dataset")
OUTPUT_CSV_PATH = os.path.join(REPO_ROOT, "output.csv")
REQUESTS_CSV_PATH = os.path.join(DATASET_DIR, "requests.csv")
SAMPLE_CSV_PATH = os.path.join(DATASET_DIR, "sample_requests.csv")
PROFILES_CSV_PATH = os.path.join(DATASET_DIR, "financial_profiles.csv")


def load_dataset():
    """Load and merge data from output.csv, requests.csv, sample_requests.csv, and financial_profiles.csv."""
    profiles = {}
    if os.path.exists(PROFILES_CSV_PATH):
        with open(PROFILES_CSV_PATH, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r.get("user_id", "").strip()
                profiles[uid] = {
                    "user_id": uid,
                    "home_currency": r.get("home_currency", "").strip().upper(),
                    "current_available_balance": float(r.get("current_available_balance", 0)),
                    "minimum_balance_to_keep": float(r.get("minimum_balance_to_keep", 0)),
                    "financial_priorities": r.get("financial_priorities", "").strip(),
                    "expense_categories_to_protect": r.get("expense_categories_to_protect", "").strip(),
                    "expense_categories_user_is_willing_to_reduce": r.get("expense_categories_user_is_willing_to_reduce", "").strip(),
                    "expense_categories_user_is_willing_to_stop": r.get("expense_categories_user_is_willing_to_stop", "").strip(),
                    "payment_methods_user_will_consider": r.get("payment_methods_user_will_consider", "").strip(),
                    "max_installment_months": r.get("max_installment_months", "").strip(),
                }

    eval_requests_meta = {}
    if os.path.exists(REQUESTS_CSV_PATH):
        with open(REQUESTS_CSV_PATH, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rid = r.get("request_id", "").strip()
                eval_requests_meta[rid] = {
                    "request_id": rid,
                    "user_id": r.get("user_id", "").strip(),
                    "request_date": r.get("request_date", "").strip(),
                    "request_type": r.get("request_type", "").strip(),
                    "requested_amount": float(r.get("requested_amount", 0)),
                    "desired_completion_date": r.get("desired_completion_date", "").strip(),
                    "allows_partial_payment": r.get("allows_partial_payment", "").strip().lower() == "true",
                    "request_text": r.get("request_text", "").strip(),
                }

    output_decisions = {}
    if os.path.exists(OUTPUT_CSV_PATH):
        with open(OUTPUT_CSV_PATH, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rid = r.get("request_id", "").strip()
                output_decisions[rid] = {
                    "request_id": rid,
                    "amount_safe_to_pay": r.get("amount_safe_to_pay", "").strip(),
                    "affordability_status": r.get("affordability_status", "").strip(),
                    "recommended_payment_method": r.get("recommended_payment_method", "").strip(),
                    "payment_plan": r.get("payment_plan", "").strip(),
                    "earliest_date_for_full_payment": r.get("earliest_date_for_full_payment", "").strip(),
                    "spending_changes_needed": r.get("spending_changes_needed", "").strip(),
                    "decision_explanation": r.get("decision_explanation", "").strip(),
                }

    sample_requests_data = []
    if os.path.exists(SAMPLE_CSV_PATH):
        with open(SAMPLE_CSV_PATH, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rid = r.get("request_id", "").strip()
                uid = r.get("user_id", "").strip()
                prof = profiles.get(uid, {})
                sample_item = {
                    "request_id": rid,
                    "user_id": uid,
                    "dataset_type": "SAMPLE / REFERENCE",
                    "request_date": r.get("request_date", "").strip(),
                    "request_type": r.get("request_type", "").strip(),
                    "requested_amount": float(r.get("requested_amount", 0)),
                    "desired_completion_date": r.get("desired_completion_date", "").strip(),
                    "allows_partial_payment": r.get("allows_partial_payment", "").strip().lower() == "true",
                    "request_text": r.get("request_text", "").strip(),
                    "amount_safe_to_pay": r.get("amount_safe_to_pay", "").strip(),
                    "affordability_status": r.get("affordability_status", "").strip(),
                    "recommended_payment_method": r.get("recommended_payment_method", "").strip(),
                    "payment_plan": r.get("payment_plan", "").strip(),
                    "earliest_date_for_full_payment": r.get("earliest_date_for_full_payment", "").strip(),
                    "spending_changes_needed": r.get("spending_changes_needed", "").strip(),
                    "decision_explanation": r.get("decision_explanation", "").strip(),
                    "profile": prof,
                }
                sample_requests_data.append(sample_item)

    evaluation_requests_data = []
    for rid, dec in output_decisions.items():
        meta = eval_requests_meta.get(rid, {})
        uid = meta.get("user_id", "")
        prof = profiles.get(uid, {})
        merged = {
            "request_id": rid,
            "user_id": uid,
            "dataset_type": "EVALUATION",
            "request_date": meta.get("request_date", ""),
            "request_type": meta.get("request_type", "purchase"),
            "requested_amount": meta.get("requested_amount", 0.0),
            "desired_completion_date": meta.get("desired_completion_date", ""),
            "allows_partial_payment": meta.get("allows_partial_payment", False),
            "request_text": meta.get("request_text", ""),
            "amount_safe_to_pay": dec.get("amount_safe_to_pay", "0.00"),
            "affordability_status": dec.get("affordability_status", "not_affordable"),
            "recommended_payment_method": dec.get("recommended_payment_method", "not_recommended"),
            "payment_plan": dec.get("payment_plan", "none"),
            "earliest_date_for_full_payment": dec.get("earliest_date_for_full_payment", ""),
            "spending_changes_needed": dec.get("spending_changes_needed", "none"),
            "decision_explanation": dec.get("decision_explanation", ""),
            "profile": prof,
        }
        evaluation_requests_data.append(merged)

    # Sort evaluation requests by ID naturally (request_26 .. request_275)
    evaluation_requests_data.sort(key=lambda x: (len(x["request_id"]), x["request_id"]))
    sample_requests_data.sort(key=lambda x: (len(x["request_id"]), x["request_id"]))

    # Summary metrics dynamically derived from output.csv
    status_counts = {"affordable_now": 0, "affordable_with_plan": 0, "affordable_later": 0, "not_affordable": 0}
    method_counts = {}
    spending_change_counts = {"none": 0, "active": 0}
    total_eval = len(evaluation_requests_data)

    for item in evaluation_requests_data:
        st = item["affordability_status"]
        status_counts[st] = status_counts.get(st, 0) + 1
        pm = item["recommended_payment_method"]
        method_counts[pm] = method_counts.get(pm, 0) + 1
        if item["spending_changes_needed"] == "none":
            spending_change_counts["none"] += 1
        else:
            spending_change_counts["active"] += 1

    summary = {
        "total_evaluation_requests": total_eval,
        "status_counts": status_counts,
        "method_counts": method_counts,
        "spending_change_counts": spending_change_counts,
        "affordable_now_count": status_counts.get("affordable_now", 0),
        "affordable_with_plan_count": status_counts.get("affordable_with_plan", 0),
        "affordable_later_count": status_counts.get("affordable_later", 0),
        "not_affordable_count": status_counts.get("not_affordable", 0),
    }

    return {
        "summary": summary,
        "evaluation_requests": evaluation_requests_data,
        "sample_requests": sample_requests_data,
    }


class DemoUIRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the static UI and read-only JSON API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/data":
            data = load_dataset()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "Buy or Wait? UI", "version": "1.0.0"}).encode("utf-8"))
            return

        # Fallback to standard static file serving from SCRIPT_DIR
        return super().do_GET()


def find_free_port(preferred_port=8080):
    """Check if preferred_port is available; if not, find an open port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", preferred_port))
            return preferred_port
        except OSError:
            s.bind(("", 0))
            return s.getsockname()[1]


def run_server(port=8080):
    actual_port = find_free_port(port)
    server_address = ("", actual_port)
    httpd = HTTPServer(server_address, DemoUIRequestHandler)
    print("=" * 65)
    print("Buy or Wait? - Financial Safety Decision Engine Demo UI")
    print("=" * 65)
    print(f"Reading from: {OUTPUT_CSV_PATH}")
    print(f"Server running at: http://localhost:{actual_port}/")
    print(f"Local network URL: http://127.0.0.1:{actual_port}/")
    print("Press Ctrl+C to stop.")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down demo server.")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    run_server(port_arg)
