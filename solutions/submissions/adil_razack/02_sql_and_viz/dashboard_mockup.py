"""Generate a dependency-free annotated PDF dashboard mockup."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT_DIR = ROOT / "outputs" / "results" / "adil_razack" / "02_sql_and_viz"
OUTPUT_PATH = INPUT_DIR / "dashboard_mockup.pdf"


def load_csv(name: str) -> list[dict[str, str]]:
    with (INPUT_DIR / name).open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def money(value: float) -> str:
    return f"AED {value:,.0f}"


def pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_dashboard() -> None:
    projects = load_csv("projects_clean.csv")
    transactions = load_csv("transactions_clean.csv")
    total_budget = sum(float(row["budget"] or 0) for row in projects)
    total_actual = sum(float(row["actual_cost"] or 0) for row in projects)
    over_budget = sum(row["is_over_budget"] == "True" for row in projects)
    department_budget: dict[str, float] = defaultdict(float)
    department_actual: dict[str, float] = defaultdict(float)
    vendor_spend: dict[str, float] = defaultdict(float)
    for row in projects:
        department_budget[row["department"]] += float(row["budget"] or 0)
        department_actual[row["department"]] += float(row["actual_cost"] or 0)
    for row in transactions:
        vendor_spend[row["vendor_name"]] += float(row["amount_aed"] or 0)

    commands: list[str] = [
        "0.96 0.97 0.98 rg",
        "BT /F1 20 Tf 40 750 Td (Presight Project Spend Performance) Tj ET",
        "BT /F1 9 Tf 40 732 Td (Executive dashboard mockup | Actual assessment data) Tj ET",
    ]
    kpis = [
        ("Total budget", money(total_budget)),
        ("Actual spend", money(total_actual)),
        ("Over-budget projects", f"{100 * over_budget / len(projects):.1f}%"),
        ("Transactions", f"{len(transactions):,}"),
    ]
    for index, (label, value) in enumerate(kpis):
        x = 40 + index * 135
        commands.extend(
            [
                f"0.86 0.91 0.94 rg {x} 675 120 42 re f",
                f"0.08 0.19 0.28 rg BT /F1 8 Tf {x + 8} 700 Td ({pdf_text(label)}) Tj ET",
                f"BT /F1 12 Tf {x + 8} 684 Td ({pdf_text(value)}) Tj ET",
            ]
        )

    commands.extend(
        [
            "0.08 0.19 0.28 rg BT /F1 12 Tf 40 635 Td (Actual spend vs budget by department) Tj ET",
            "0.08 0.19 0.28 rg BT /F1 12 Tf 400 635 Td (Vendor concentration: top 5 + Other) Tj ET",
            "0.08 0.19 0.28 rg BT /F1 12 Tf 40 390 Td (Monthly transaction spend trend by category) Tj ET",
            "0.08 0.19 0.28 rg BT /F1 12 Tf 400 390 Td (Top 10 projects by budget variance) Tj ET",
            "0.37 0.42 0.48 rg BT /F1 9 Tf 40 615 Td (Department | Budget | Actual) Tj ET",
        ]
    )
    y = 598
    for department in sorted(department_budget, key=department_actual.get, reverse=True)[:8]:
        label = f"{department[:18]} | {money(department_budget[department])} | {money(department_actual[department])}"
        commands.append(f"BT /F1 8 Tf 40 {y} Td ({pdf_text(label)}) Tj ET")
        y -= 16

    commands.append("0.37 0.42 0.48 rg BT /F1 9 Tf 400 615 Td (Vendor | Spend) Tj ET")
    y = 598
    for vendor, spend in sorted(vendor_spend.items(), key=lambda item: item[1], reverse=True)[:5]:
        commands.append(f"BT /F1 8 Tf 400 {y} Td ({pdf_text(vendor[:24])} | {money(spend)}) Tj ET")
        y -= 16
    commands.append("BT /F1 8 Tf 400 510 Td (Other | Remaining vendors) Tj ET")

    commands.extend(
        [
            "0.37 0.42 0.48 rg BT /F1 9 Tf 40 370 Td (Use Q5 SQL for category lines and running totals.) Tj ET",
            "BT /F1 9 Tf 400 370 Td (Use projects_clean.csv for variance ranking.) Tj ET",
            "0.08 0.19 0.28 rg BT /F1 10 Tf 40 80 Td (Slicers: Region | Project status | Year) Tj ET",
            "0.37 0.42 0.48 rg BT /F1 8 Tf 40 60 Td (Bars compare planned and actual spend; vendor view highlights concentration risk.) Tj ET",
        ]
    )

    content = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    OUTPUT_PATH.write_bytes(pdf)


if __name__ == "__main__":
    make_dashboard()
