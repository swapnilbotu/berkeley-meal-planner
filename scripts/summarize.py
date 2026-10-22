"""Keep summaries compact; never print tokens, private task content, or API responses."""
import json
from pathlib import Path

p = Path('out/plan.json')
if not p.exists():
    print('No verified plan was generated. Inspect the failed step; no success is claimed.')
else:
    for task in json.loads(p.read_text()):
        total = next(line for line in task['notes'].splitlines() if line.startswith('Total:'))
        print(f"- {task['title']}: {total}; due {task['due'][:10]}.")
    print('\nPlan generation alone does not verify task writes. The application log must report successful read-back of exactly two meal tasks.')
