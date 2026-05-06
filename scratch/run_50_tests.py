import requests
import json
import time
from typing import List, Dict

URL = "http://localhost:8000/api/chat"

queries_factual = [
    "What is the expense ratio of the Small Cap Fund?",
    "NAV of Ethical Fund?",
    "Minimum SIP for Multi Asset Allocation Fund?",
    "Who is the fund manager for Flexi Cap Fund?",
    "What is the exit load for Arbitrage Fund?",
    "Benchmark for Liquid Fund?",
    "What is the risk level of the Gold ETF FoF?",
    "Category of the Small Cap Fund?",
    "Inception date of the Ethical Fund?",
    "Asset under management for Multi Asset Allocation Fund?",
    "What is the investment objective of the Flexi Cap Fund?",
    "Minimum lumpsum for Gold ETF FoF?",
    "Fund house of the Arbitrage Fund?",
    "Expense ratio of the Liquid Fund?",
    "Latest NAV of the Small Cap Fund?",
    "What is the minimum SIP for the Ethical Fund?",
    "Who manages the Multi Asset Allocation Fund?",
    "Exit load of the Flexi Cap Fund?",
    "Benchmark of the Gold ETF FoF?",
    "Risk level of the Arbitrage Fund?",
    "Category of the Liquid Fund?",
    "When was the Small Cap Fund launched?",
    "AUM of the Ethical Fund?",
    "Tell me the investment objective of the Multi Asset Allocation Fund.",
    "Minimum lumpsum investment for Flexi Cap Fund?",
    "Who is the fund house for Gold ETF FoF?",
    "What are the charges for Arbitrage Fund?",
    "NAV of Liquid Fund today?",
    "Minimum SIP amount for Small Cap Fund?",
    "Fund manager details for Ethical Fund?"
]

queries_partial = [
    "What are the tax implications for Arbitrage Fund?",
    "What is the portfolio strategy of the Ethical Fund?",
    "How does the Liquid Fund manage liquidity?",
    "What are the key holdings of the Small Cap Fund?",
    "Tell me about the historical performance of Flexi Cap.",
    "What is the redemption process for Multi Asset?",
    "Who are the secondary fund managers for Gold ETF?",
    "What is the stamp duty on Liquid Fund?",
    "Does the Ethical Fund invest in tobacco?",
    "What is the lock-in period for Arbitrage Fund?"
]

queries_irrelevant = [
    "Which is the best fund to double my money in 1 year?",
    "Compare Small Cap vs Ethical Fund.",
    "Which is better: Liquid or Arbitrage?",
    "Give me a recommendation for a low risk fund.",
    "Is it safe to invest in Flexi Cap now?",
    "What is the current stock price of Google?",
    "How do I start a SIP in any fund?",
    "What is your name?",
    "Tell me a joke about finance.",
    "What is the weather in Delhi?"
]

def run_tests(category_name: str, queries: List[str]) -> List[Dict]:
    results = []
    print(f"\nRunning Category: {category_name}")
    print("-" * 50)
    for i, q in enumerate(queries, 1):
        try:
            start_time = time.time()
            response = requests.post(URL, json={"query": q}, timeout=30)
            elapsed = time.time() - start_time
            if response.status_code == 200:
                data = response.json()
                results.append({
                    "query": q,
                    "response": data.get("text", ""),
                    "source": data.get("source_url", "N/A"),
                    "state": data.get("terminal_state", "UNKNOWN"),
                    "time": round(elapsed, 2)
                })
                print(f"[{i:02d}] Success: {q[:40]}...")
            else:
                print(f"[{i:02d}] Failed: {response.status_code}")
        except Exception as e:
            print(f"[{i:02d}] Error: {str(e)}")
    return results

# Execute all
all_results = {
    "Factual (30)": run_tests("Factual (Valid entire response)", queries_factual),
    "Partial (10)": run_tests("Partial (Synthesized/Text-based)", queries_partial),
    "Irrelevant (10)": run_tests("Irrelevant (Refusals/Out-of-scope)", queries_irrelevant)
}

# Save to file
with open("scratch/fifty_case_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

# Format a summary markdown table for the user
with open("scratch/fifty_case_report.md", "w", encoding="utf-8") as f:
    f.write("# 50-Case Test Report\n\n")
    for cat, results in all_results.items():
        f.write(f"## {cat}\n\n")
        f.write("| # | Query | Response Snippet | Source | State |\n")
        f.write("|---|---|---|---|---|\n")
        for i, r in enumerate(results, 1):
            snippet = r['response'].replace('\n', ' ')[:100] + "..."
            f.write(f"| {i} | {r['query']} | {snippet} | {r['source']} | {r['state']} |\n")
        f.write("\n")

print("\nTesting complete. Results saved to scratch/fifty_case_report.md")
