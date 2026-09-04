import io
import os
import tempfile
from pathlib import Path

import pandas as pd

from finance_tools import budget_alerts, build_report_pdf, parse_statement

with tempfile.TemporaryDirectory() as tmp:
    csv = io.BytesIO(b"Date,Amount,Type,Category,Description\n2026-09-01,1000,Credit,Salary,Salary\n2026-09-02,800,Debit,Food,Lunch\n")
    csv.name = "statement.csv"
    parsed = parse_statement(csv)
    assert len(parsed) == 2
    assert list(parsed["Type"]) == ["Income", "Expense"]
    alerts = budget_alerts([("Food", 1000.0)], [(1, "2026-09-02", "Expense", "Food", 800.0, "Lunch")])
    assert alerts[0]["level"] == "warning"
    pdf = build_report_pdf("test-user", [], [], [], {"score": None}, {"status": "insufficient"}, alerts)
    assert pdf.startswith(b"%PDF")

print("finance tools tests passed")
