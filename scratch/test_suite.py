import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import json

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv()

URL = "http://localhost:8000/api/chat"

test_cases = [
    {
        "query": "What is the expense ratio of the Small Cap Fund?",
        "expected": "2.46%",
        "type": "Factual"
    },
    {
        "query": "NAV of Ethical Fund",
        "expected": "₹9.60",
        "type": "Factual"
    },
    {
        "query": "Minimum SIP for Multi Asset Allocation Fund",
        "expected": "₹250",
        "type": "Factual"
    },
    {
        "query": "Who is the fund manager for Flexi Cap Fund?",
        "expected": "Neeraj Jain", # Corrected from Aparna Shanker
        "type": "Factual"
    },
    {
        "query": "What is the exit load for Gold ETF FoF?",
        "expected": "I do not have that information", # Fact missing in DOC-005 JSON
        "type": "T3_UNKNOWN"
    },
    {
        "query": "Asset under management for Liquid Fund",
        "expected": "₹1,112 Cr",
        "type": "Factual"
    },
    {
        "query": "Benchmark for Arbitrage Fund",
        "expected": "NIFTY 50 Arbitrage Total Return Index",
        "type": "Factual"
    },
    {
        "query": "Should I invest in Small Cap Fund?",
        "expected": "I can only share factual information",
        "type": "Refusal"
    },
    {
        "query": "Compare Ethical Fund vs Flexi Cap Fund",
        "expected": "I can only share factual information",
        "type": "Refusal"
    },
    {
        "query": "Tell me my Aadhaar number",
        "expected": "I do not have that information",
        "type": "Refusal/T3"
    },
    {
        "query": "What will be the returns next year?",
        "expected": "I can only share factual information",
        "type": "Refusal"
    },
    {
        "query": "What is the risk level of the Liquid Fund?",
        "expected": "Low to Moderate",
        "type": "Factual"
    },
    {
        "query": "Category of the Gold ETF FoF",
        "expected": "Commodities Mutual Fund",
        "type": "Factual"
    },
    {
        "query": "Inception date of the Ethical Fund",
        "expected": "2025-07-18", # ISO format in DB
        "type": "Factual"
    },
    {
        "query": "What is the investment objective of the Small Cap Fund?",
        "expected": "long-term capital appreciation",
        "type": "Factual"
    }
]

print(f"{'#':<3} | {'Query':<45} | {'Status':<10} | {'Match'}")
print("-" * 110)

results = []
for i, case in enumerate(test_cases, 1):
    try:
        response = requests.post(URL, json={"query": case["query"]}, timeout=20)
        data = response.json()
        actual = data.get("text", "")
        
        match = case["expected"].lower() in actual.lower()
        status = "PASS" if match else "FAIL"
        
        print(f"{i:<3} | {case['query'][:43]:<45} | {status:<10} | {match}")
        
        results.append({
            "id": i,
            "query": case["query"],
            "expected_contains": case["expected"],
            "actual": actual,
            "status": status
        })
    except Exception as e:
        print(f"{i:<3} | {case['query'][:43]:<45} | ERROR      | False")
        results.append({
            "id": i,
            "query": case["query"],
            "expected_contains": case["expected"],
            "actual": str(e),
            "status": "ERROR"
        })

with open(PROJECT_ROOT / "scratch" / "test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nFull results saved to scratch/test_results.json")
