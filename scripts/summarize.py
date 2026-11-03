"""Report job status without exposing meal data."""
import os

status = os.environ.get("PLANNER_JOB_STATUS", "unknown")
print("Meal planner job: " + (status if status in {"success", "failure", "cancelled"} else "unknown"))
