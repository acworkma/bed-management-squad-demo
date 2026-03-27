#!/usr/bin/env python3
"""Model comparison evaluation script for the Bed Management API.

Runs scenarios against the live API, collects per-agent metrics, and produces
comparison reports across multiple models.

Two modes:
  Run mode (default):
    python scripts/model_eval.py --model gpt-5.2 --runs 3
    Runs the scenario N times, saves results to eval-results-{model}-{timestamp}.json

  Compare mode:
    python scripts/model_eval.py --compare eval-results-*.json
    Reads multiple result files and prints a comparison table.

The script swaps models at runtime via PUT /api/config — no container
restart needed between model evaluations.
"""

from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ── HTTP helpers (stdlib only) ──────────────────────────────────────

def _request(method: str, url: str, body: dict | None = None, timeout: int = 30) -> dict:
    """Make an HTTP request and return parsed JSON."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get(url: str, timeout: int = 30) -> dict:
    return _request("GET", url, timeout=timeout)


def _post(url: str, body: dict | None = None, timeout: int = 30) -> dict:
    return _request("POST", url, body=body, timeout=timeout)


def _put(url: str, body: dict | None = None, timeout: int = 30) -> dict:
    return _request("PUT", url, body=body, timeout=timeout)


def _set_model(base: str, model: str) -> None:
    """Set the runtime model deployment via PUT /api/config."""
    _put(f"{base}/api/config", body={"model_deployment": model})


def _reset_config(base: str) -> None:
    """Reset runtime config back to env var defaults."""
    _post(f"{base}/api/config/reset")


# ── Run mode ────────────────────────────────────────────────────────

def run_eval(base_url: str, model: str, scenario: str, runs: int, output: str | None) -> dict:
    """Run a scenario N times and collect metrics."""
    base = base_url.rstrip("/")
    all_runs: list[dict] = []

    # Set the model via runtime config endpoint
    print(f"  Setting model to {model} via /api/config ...")
    _set_model(base, model)

    for i in range(1, runs + 1):
        print(f"  Run {i}/{runs} ...", end=" ", flush=True)

        # 1. Seed state
        _post(f"{base}/api/scenario/seed")

        # 2. Record metrics history length before triggering
        pre_history = _get(f"{base}/api/metrics/history?limit=100")
        pre_count = 0 if isinstance(pre_history, dict) and "message" in pre_history else len(pre_history)

        # 3. Trigger scenario (returns 202)
        _post(f"{base}/api/scenario/{scenario}")

        # 4. Poll /api/metrics/history until a new entry appears
        metrics_entry = _poll_for_new_metrics(base, pre_count, timeout_s=300)
        if metrics_entry is None:
            print("TIMEOUT (no new metrics after 300s)")
            continue

        all_runs.append(metrics_entry)
        latency = metrics_entry.get("total_latency_seconds", 0)
        print(f"done  ({latency:.1f}s)")

    if not all_runs:
        print("ERROR: No successful runs collected.", file=sys.stderr)
        sys.exit(1)

    result = _build_result(model, scenario, runs, all_runs)

    # Save to file
    if output is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_model = model.replace("/", "-").replace("\\", "-")
        output = f"eval-results-{safe_model}-{ts}.json"

    Path(output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\nResults saved to {output}")
    _print_single_report(result)
    return result


def _poll_for_new_metrics(base: str, pre_count: int, timeout_s: int = 300) -> dict | None:
    """Poll metrics history until a new entry appears or timeout."""
    deadline = time.monotonic() + timeout_s
    interval = 2.0
    while time.monotonic() < deadline:
        time.sleep(interval)
        history = _get(f"{base}/api/metrics/history?limit=100")
        if isinstance(history, dict) and "message" in history:
            continue
        if len(history) > pre_count:
            return history[0]  # most recent first
        # Back off slightly, cap at 5s
        interval = min(interval * 1.2, 5.0)
    return None


def _build_result(model: str, scenario: str, runs: int, all_runs: list[dict]) -> dict:
    """Build the JSON result structure from raw run data."""
    total_latencies = [r["total_latency_seconds"] for r in all_runs]
    total_in_tokens = [r["total_input_tokens"] for r in all_runs]
    total_out_tokens = [r["total_output_tokens"] for r in all_runs]
    total_rounds = [sum(a["rounds"] for a in r.get("agents", [])) for r in all_runs]

    # Per-agent aggregation
    agent_data: dict[str, dict[str, list]] = {}
    for run in all_runs:
        for agent in run.get("agents", []):
            name = agent["agent_name"]
            if name not in agent_data:
                agent_data[name] = {
                    "latency": [], "input_tokens": [], "output_tokens": [], "rounds": [],
                }
            agent_data[name]["latency"].append(agent["latency_seconds"])
            agent_data[name]["input_tokens"].append(agent["input_tokens"])
            agent_data[name]["output_tokens"].append(agent["output_tokens"])
            agent_data[name]["rounds"].append(agent["rounds"])

    per_agent = {}
    for name, data in agent_data.items():
        per_agent[name] = {
            "avg_latency_seconds": round(statistics.mean(data["latency"]), 3),
            "avg_input_tokens": round(statistics.mean(data["input_tokens"])),
            "avg_output_tokens": round(statistics.mean(data["output_tokens"])),
            "avg_rounds": round(statistics.mean(data["rounds"]), 1),
        }

    return {
        "model": model,
        "scenario": scenario,
        "runs": len(all_runs),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "avg_latency_seconds": round(statistics.mean(total_latencies), 3),
            "avg_input_tokens": round(statistics.mean(total_in_tokens)),
            "avg_output_tokens": round(statistics.mean(total_out_tokens)),
            "avg_rounds": round(statistics.mean(total_rounds), 1),
        },
        "per_agent": per_agent,
        "raw_runs": all_runs,
    }


# ── Compare mode ────────────────────────────────────────────────────

def compare(file_patterns: list[str]) -> None:
    """Read multiple result files and print a comparison table."""
    paths: list[str] = []
    for pattern in file_patterns:
        paths.extend(glob.glob(pattern))


    if not paths:
        print("ERROR: No result files found matching the given patterns.", file=sys.stderr)
        sys.exit(1)

    results: list[dict] = []
    for p in sorted(set(paths)):
        with open(p, encoding="utf-8") as f:
            results.append(json.load(f))

    if not results:
        print("ERROR: No valid result files loaded.", file=sys.stderr)
        sys.exit(1)

    scenario = results[0].get("scenario", "unknown")
    _print_comparison_table(results, scenario)

    for r in results:
        _print_agent_breakdown(r)


def _print_comparison_table(results: list[dict], scenario: str) -> None:
    """Print the summary comparison table."""
    print(f"\nModel Eval Results — {scenario} scenario")
    print("=" * 75)
    print(
        f"{'Model':<20} {'Runs':>5} {'Avg Latency':>13} "
        f"{'Avg In Tokens':>15} {'Avg Out Tokens':>16} {'Avg Rounds':>11}"
    )
    print("-" * 75)
    for r in results:
        s = r["summary"]
        print(
            f"{r['model']:<20} {r['runs']:>5} "
            f"{s['avg_latency_seconds']:>12.1f}s "
            f"{s['avg_input_tokens']:>15,} "
            f"{s['avg_output_tokens']:>16,} "
            f"{s['avg_rounds']:>11.0f}"
        )
    print("=" * 75)


def _print_agent_breakdown(result: dict) -> None:
    """Print per-agent breakdown for a single model result."""
    model = result["model"]
    runs = result["runs"]
    per_agent = result.get("per_agent", {})
    if not per_agent:
        return

    print(f"\nPer-Agent Breakdown — {model} (avg of {runs} runs)")
    print("-" * 65)
    print(f"{'Agent':<25} {'Latency':>9} {'In Tok':>9} {'Out Tok':>9} {'Rounds':>8}")
    print("-" * 65)
    for name, data in per_agent.items():
        print(
            f"{name:<25} "
            f"{data['avg_latency_seconds']:>8.1f}s "
            f"{data['avg_input_tokens']:>9,} "
            f"{data['avg_output_tokens']:>9,} "
            f"{data['avg_rounds']:>8.1f}"
        )
    print()


# ── Single-run report (printed after run mode) ─────────────────────

def _print_single_report(result: dict) -> None:
    """Print a summary for a single model's evaluation."""
    _print_comparison_table([result], result["scenario"])
    _print_agent_breakdown(result)


# ── CLI ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Model comparison evaluation for the Bed Management API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Run mode — execute scenario 3 times against the live API\n"
            "  python scripts/model_eval.py --model gpt-5.2 --runs 3\n\n"
            "  # Compare mode — compare results across models\n"
            "  python scripts/model_eval.py --compare eval-results-*.json\n"
        ),
    )

    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="FILE",
        help="Compare mode: read result JSON files and print comparison table.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.2",
        help="Model name label for this run (default: gpt-5.2).",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per model (default: 3).",
    )
    parser.add_argument(
        "--scenario",
        default="er-admission",
        help="Scenario to run (default: er-admission).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: eval-results-{model}-{timestamp}.json).",
    )

    args = parser.parse_args()

    if args.compare:
        compare(args.compare)
    else:
        print(f"Model Eval — model={args.model}, scenario={args.scenario}, runs={args.runs}")
        print(f"API: {args.base_url}\n")
        run_eval(args.base_url, args.model, args.scenario, args.runs, args.output)


if __name__ == "__main__":
    main()
