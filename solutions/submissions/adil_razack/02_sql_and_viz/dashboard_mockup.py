"""Generate a data-backed, dependency-free PDF dashboard from cleaned CSVs."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
INPUT_DIR = ROOT / "outputs" / "results" / "adil_razack" / "02_sql_and_viz"
OUTPUT_PATH = INPUT_DIR / "dashboard_mockup.pdf"
PAGE_W, PAGE_H = 842, 595

INK = (0.09, 0.18, 0.23)
MUTED = (0.36, 0.44, 0.48)
GRID = (0.84, 0.88, 0.89)
PANEL = (0.98, 0.99, 0.99)
PALETTE = [
    (0.08, 0.42, 0.47),
    (0.82, 0.35, 0.19),
    (0.28, 0.48, 0.68),
    (0.55, 0.43, 0.18),
    (0.42, 0.54, 0.36),
    (0.49, 0.39, 0.57),
]


def load_csv(name: str) -> list[dict[str, str]]:
    with (INPUT_DIR / name).open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def number(value: str | None) -> float:
    try:
        return float(value) if value else 0.0
    except (TypeError, ValueError):
        return 0.0


def pdf_text(value: object) -> str:
    text = str(value).encode("latin-1", errors="replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def color(rgb: tuple[float, float, float], stroke: bool = False) -> str:
    operator = "RG" if stroke else "rg"
    return f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} {operator}"


class Canvas:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def text(self, x: float, y: float, value: object, size: float = 8,
             fill: tuple[float, float, float] = INK, font: str = "F1") -> None:
        self.commands.append(
            f"{color(fill)} BT /{font} {size:.1f} Tf {x:.1f} {y:.1f} Td ({pdf_text(value)}) Tj ET"
        )

    def rect(self, x: float, y: float, width: float, height: float,
             fill: tuple[float, float, float] | None = None,
             stroke: tuple[float, float, float] | None = None) -> None:
        if fill:
            self.commands.append(color(fill))
        if stroke:
            self.commands.append(color(stroke, stroke=True))
        operator = "B" if fill and stroke else "f" if fill else "S"
        self.commands.append(f"{x:.1f} {y:.1f} {width:.1f} {height:.1f} re {operator}")

    def line(self, x1: float, y1: float, x2: float, y2: float,
             stroke: tuple[float, float, float] = GRID, width: float = 0.6) -> None:
        self.commands.append(
            f"{color(stroke, stroke=True)} {width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S"
        )

    def circle(self, cx: float, cy: float, radius: float,
               fill: tuple[float, float, float]) -> None:
        k = radius * 0.55228475
        self.commands.extend([
            color(fill), f"{cx + radius:.2f} {cy:.2f} m",
            f"{cx + radius:.2f} {cy + k:.2f} {cx + k:.2f} {cy + radius:.2f} {cx:.2f} {cy + radius:.2f} c",
            f"{cx - k:.2f} {cy + radius:.2f} {cx - radius:.2f} {cy + k:.2f} {cx - radius:.2f} {cy:.2f} c",
            f"{cx - radius:.2f} {cy - k:.2f} {cx - k:.2f} {cy - radius:.2f} {cx:.2f} {cy - radius:.2f} c",
            f"{cx + k:.2f} {cy - radius:.2f} {cx + radius:.2f} {cy - k:.2f} {cx + radius:.2f} {cy:.2f} c f",
        ])

    def wedge(self, cx: float, cy: float, radius: float, start: float, end: float,
              fill: tuple[float, float, float]) -> None:
        if end <= start:
            return
        steps = max(1, math.ceil((end - start) / (math.pi / 2)))
        delta = (end - start) / steps
        x0, y0 = cx + radius * math.cos(start), cy + radius * math.sin(start)
        parts = [color(fill), f"{cx:.2f} {cy:.2f} m", f"{x0:.2f} {y0:.2f} l"]
        angle = start
        for _ in range(steps):
            next_angle = angle + delta
            k = 4 / 3 * math.tan(delta / 4)
            p0x, p0y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            p1x, p1y = cx + radius * math.cos(next_angle), cy + radius * math.sin(next_angle)
            c1x, c1y = p0x - k * radius * math.sin(angle), p0y + k * radius * math.cos(angle)
            c2x, c2y = p1x + k * radius * math.sin(next_angle), p1y - k * radius * math.cos(next_angle)
            parts.append(f"{c1x:.2f} {c1y:.2f} {c2x:.2f} {c2y:.2f} {p1x:.2f} {p1y:.2f} c")
            angle = next_angle
        parts.append("h f")
        self.commands.extend(parts)


def compact_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"AED {value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"AED {value / 1_000:,.0f}K"
    return f"AED {value:,.0f}"


def portfolio_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"AED {value / 1_000_000:,.2f}M"
    return f"AED {value:,.0f}"


def panel(canvas: Canvas, x: float, y: float, width: float, height: float, title: str) -> None:
    canvas.rect(x, y, width, height, fill=(1, 1, 1), stroke=GRID)
    canvas.text(x + 12, y + height - 20, title, 10, INK, "F2")


def build_department_totals(projects: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"budget": 0.0, "actual": 0.0})
    for row in projects:
        department = row.get("department") or "Unknown"
        totals[department]["budget"] += number(row.get("budget"))
        totals[department]["actual"] += number(row.get("actual_cost"))
    return totals


def draw_department_chart(canvas: Canvas, x: float, y: float, width: float, height: float,
                          totals: dict[str, dict[str, float]]) -> None:
    panel(canvas, x, y, width, height, "Actual spend vs budget by department")
    shown = sorted(totals, key=lambda name: totals[name]["budget"], reverse=True)
    legend_y = y + height - 39
    canvas.rect(x + 14, legend_y - 2, 8, 8, fill=PALETTE[0])
    canvas.text(x + 27, legend_y, "Budget", 7, MUTED)
    canvas.rect(x + 88, legend_y - 2, 8, 8, fill=PALETTE[1])
    canvas.text(x + 101, legend_y, "Actual cost", 7, MUTED)
    plot_top = legend_y - 13
    row_step = min(17, (height - 67) / max(len(shown), 1))
    bar_x, bar_max_width = x + 103, width - 166
    max_value = max((max(totals[name]["budget"], totals[name]["actual"]) for name in shown), default=1) or 1
    for index, department in enumerate(shown):
        row_y = plot_top - (index + 1) * row_step
        bar_height = max(2.4, min(4, row_step * 0.27))
        canvas.text(x + 12, row_y + 2, department[:14], 6.2, MUTED)
        canvas.rect(bar_x, row_y + bar_height + 1, bar_max_width * totals[department]["budget"] / max_value, bar_height, fill=PALETTE[0])
        canvas.rect(bar_x, row_y - 1, bar_max_width * totals[department]["actual"] / max_value, bar_height, fill=PALETTE[1])
        canvas.text(x + width - 57, row_y + 1, compact_money(totals[department]["actual"]), 5.8, INK)


def draw_vendor_donut(canvas: Canvas, x: float, y: float, width: float, height: float,
                      vendor_spend: dict[str, float]) -> None:
    panel(canvas, x, y, width, height, "Vendor concentration | Top 5 + Other")
    ranked = sorted(vendor_spend.items(), key=lambda item: item[1], reverse=True)
    top = ranked[:5]
    other_total = sum(value for _, value in ranked[5:])
    slices = top + ([ ("Other", other_total) ] if other_total > 0 else [])
    grand_total = sum(value for _, value in ranked)
    cx, cy, radius, inner = x + 96, y + 93, 59, 32
    angle = math.pi / 2
    for index, (_, value) in enumerate(slices):
        sweep = value / grand_total * 2 * math.pi if grand_total else 0
        canvas.wedge(cx, cy, radius, angle, angle + sweep, PALETTE[index % len(PALETTE)])
        angle += sweep
    canvas.circle(cx, cy, inner, (1, 1, 1))
    canvas.text(cx - 26, cy + 3, compact_money(grand_total), 7, INK, "F2")
    canvas.text(cx - 17, cy - 9, "Total", 7, MUTED)
    legend_x, legend_top = x + 174, y + height - 49
    for index, (name, value) in enumerate(slices):
        row_y = legend_top - index * 21
        canvas.rect(legend_x, row_y - 2, 8, 8, fill=PALETTE[index % len(PALETTE)])
        share = 100 * value / grand_total if grand_total else 0
        canvas.text(legend_x + 14, row_y, f"{name[:19]}  {share:.1f}%", 7, INK)
        canvas.text(legend_x + 14, row_y - 9, compact_money(value), 6.5, MUTED)


def build_monthly_category_totals(
    transactions: list[dict[str, str]],
) -> tuple[list[str], dict[str, dict[str, float]]]:
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in transactions:
        month, category = row.get("transaction_year_month") or "", row.get("category") or "Unknown"
        if len(month) == 7:
            totals[category][month] += number(row.get("amount_aed"))
    months = sorted({month for values in totals.values() for month in values})
    return months, totals


def draw_monthly_chart(canvas: Canvas, x: float, y: float, width: float, height: float,
                       months: list[str], category_totals: dict[str, dict[str, float]]) -> None:
    panel(canvas, x, y, width, height, "Monthly transaction spend by category")
    categories = sorted(category_totals, key=lambda c: sum(category_totals[c].values()), reverse=True)[:5]
    legend_xs, legend_top = [x + 14, x + 143, x + 273], y + height - 39
    for index, category in enumerate(categories):
        lx, ly = legend_xs[index % 3], legend_top - (index // 3) * 11
        canvas.line(lx, ly + 2, lx + 13, ly + 2, PALETTE[index], 2)
        canvas.text(lx + 17, ly, category[:16], 6.5, MUTED)
    left, right = x + 42, x + width - 15
    bottom, top = y + 34, legend_top - 23
    if not months:
        canvas.text(left, bottom + 30, "No transaction month data available", 8, MUTED)
        return
    maximum = max((category_totals[c].get(m, 0.0) for c in categories for m in months), default=1) or 1
    for grid in range(4):
        gy = bottom + (top - bottom) * grid / 3
        canvas.line(left, gy, right, gy, GRID, 0.4)
        canvas.text(x + 5, gy - 2, f"{maximum * grid / 3 / 1_000_000:.1f}M", 6, MUTED)
    for category_index, category in enumerate(categories):
        points = []
        for month_index, month in enumerate(months):
            px = left + (right - left) * month_index / max(len(months) - 1, 1)
            py = bottom + (top - bottom) * category_totals[category].get(month, 0.0) / maximum
            points.append((px, py))
        for point_a, point_b in zip(points, points[1:]):
            canvas.line(*point_a, *point_b, PALETTE[category_index], 1.25)
        for px, py in points:
            canvas.circle(px, py, 1.4, PALETTE[category_index])
    ticks = sorted(set([0, len(months) - 1] + list(range(0, len(months), max(1, len(months) // 5)))))
    for tick in ticks:
        px = left + (right - left) * tick / max(len(months) - 1, 1)
        canvas.text(px - 14, bottom - 14, months[tick], 5.8, MUTED)


def draw_variance_table(canvas: Canvas, x: float, y: float, width: float, height: float,
                        projects: list[dict[str, str]]) -> None:
    panel(canvas, x, y, width, height, "Top 10 projects by budget variance")
    ranked = sorted(projects, key=lambda row: number(row.get("budget_variance")), reverse=True)[:10]
    header_y = y + height - 40
    canvas.text(x + 11, header_y, "PROJECT", 6.5, MUTED, "F2")
    canvas.text(x + 195, header_y, "DEPARTMENT", 6.5, MUTED, "F2")
    canvas.text(x + width - 82, header_y, "VARIANCE", 6.5, MUTED, "F2")
    canvas.line(x + 10, header_y - 5, x + width - 10, header_y - 5, GRID, 0.6)
    step = min(12.3, (height - 56) / 10)
    for index, row in enumerate(ranked):
        row_y = header_y - 18 - index * step
        if index % 2 == 0:
            canvas.rect(x + 7, row_y - 3, width - 14, step, fill=PANEL)
        variance = number(row.get("budget_variance"))
        canvas.text(x + 11, row_y, row.get("project_name", "")[:30], 6.2, INK)
        canvas.text(x + 195, row_y, row.get("department", "")[:13], 6.2, MUTED)
        canvas.text(x + width - 82, row_y, compact_money(variance), 6.2, PALETTE[1] if variance > 0 else PALETTE[0])


def make_pdf(content: bytes) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    pdf, offsets = bytearray(b"%PDF-1.4\n"), [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(pdf)


def make_dashboard() -> None:
    projects, transactions = load_csv("projects_clean.csv"), load_csv("transactions_clean.csv")
    if not projects or not transactions:
        raise ValueError("Both cleaned projects and transactions CSVs must contain rows")

    total_budget = sum(number(row.get("budget")) for row in projects)
    total_actual = sum(number(row.get("actual_cost")) for row in projects)
    over_budget_count = sum(number(row.get("actual_cost")) > number(row.get("budget")) for row in projects)
    over_budget_pct = 100 * over_budget_count / len(projects)
    department_totals = build_department_totals(projects)
    vendor_spend: dict[str, float] = defaultdict(float)
    for row in transactions:
        vendor_spend[row.get("vendor_name") or "Unknown"] += number(row.get("amount_aed"))
    months, category_totals = build_monthly_category_totals(transactions)

    canvas = Canvas()
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=(0.965, 0.976, 0.976))
    canvas.text(34, 560, "Project Spend Performance", 20, INK, "F2")
    canvas.text(35, 542, "Executive portfolio view | Calculated from current cleaned assessment CSVs", 8.5, MUTED)

    kpis = [
        ("TOTAL PROJECT BUDGET", portfolio_money(total_budget)),
        ("TOTAL ACTUAL PROJECT COST", portfolio_money(total_actual)),
        ("PROJECTS OVER BUDGET", f"{over_budget_pct:.1f}% ({over_budget_count}/{len(projects)})"),
        ("TRANSACTIONS", f"{len(transactions):,}"),
    ]
    for index, (label, value) in enumerate(kpis):
        cx = 34 + index * 196
        canvas.rect(cx, 476, 185, 50, fill=(1, 1, 1), stroke=GRID)
        canvas.text(cx + 11, 507, label, 6.8, MUTED, "F2")
        canvas.text(cx + 11, 487, value, 12, INK, "F2")

    chart_w, chart_h = 379, 194
    left_x, right_x, top_y, bottom_y = 34, 429, 266, 55
    draw_department_chart(canvas, left_x, top_y, chart_w, chart_h, department_totals)
    draw_vendor_donut(canvas, right_x, top_y, chart_w, chart_h, vendor_spend)
    draw_monthly_chart(canvas, left_x, bottom_y, chart_w, chart_h, months, category_totals)
    draw_variance_table(canvas, right_x, bottom_y, chart_w, chart_h, projects)

    canvas.text(35, 34, "FILTER PREVIEW", 6.5, MUTED, "F2")
    sx = 132
    for label in ("Region", "Project status", "Year"):
        canvas.rect(sx, 23, 130, 20, fill=(1, 1, 1), stroke=GRID)
        canvas.text(sx + 7, 35, f"{label}: All  v", 7, INK)
        sx += 140
    canvas.text(555, 30, "All departments | Top 5 spend categories | Positive variance = over budget", 6.2, MUTED)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = make_pdf("\n".join(canvas.commands).encode("latin-1", errors="replace"))
    output_path = OUTPUT_PATH
    try:
        output_path.write_bytes(pdf_bytes)
    except PermissionError:
        output_path = OUTPUT_PATH.with_name("dashboard_mockup_corrected.pdf")
        output_path.write_bytes(pdf_bytes)
    print(f"Projects: {len(projects)} | Transactions: {len(transactions)}")
    print(f"Budget: {total_budget:.2f} | Actual cost: {total_actual:.2f}")
    print(f"Over budget: {over_budget_count}/{len(projects)} ({over_budget_pct:.1f}%)")
    print(f"Monthly range: {months[0] if months else 'n/a'} to {months[-1] if months else 'n/a'}")
    print(f"Saved dashboard: {output_path}")


if __name__ == "__main__":
    make_dashboard()