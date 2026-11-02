"""Security summary + CSV / PDF exports."""
import csv
import io
from datetime import datetime

from database import db_service as db

CSV_COLUMNS = ["id", "time", "duration", "protocol", "service", "flag",
               "src_bytes", "dst_bytes", "prediction", "confidence", "source"]


def build_summary():
    total = db.get_total_predictions()
    attacks = db.get_attack_count()
    distribution = [
        (row[0], row[1]) for row in db.get_attack_distribution()
        if row[0] != "normal"
    ]
    distribution.sort(key=lambda r: r[1], reverse=True)
    return {
        "total": total,
        "normal": db.get_normal_count(),
        "attacks": attacks,
        "detection_rate": round(attacks / total * 100, 1) if total else 0,
        "open_alerts": db.count_alerts("open"),
        "open_incidents": db.count_incidents("open"),
        "attack_types": distribution,
        "generated": datetime.now().strftime("%d-%m-%Y %H:%M"),
    }


def _csv_safe(value):
    """Stop spreadsheet formula injection when the CSV is opened in Excel."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def predictions_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for row in db.get_all_predictions():
        writer.writerow([_csv_safe(row[c]) for c in CSV_COLUMNS])
    return buf.getvalue().encode("utf-8")


def summary_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    summary = build_summary()
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="CyberShield AI report")
    story = [
        Paragraph("CyberShield AI - Security Report", styles["Title"]),
        Paragraph(f"Generated {summary['generated']}", styles["Normal"]),
        Spacer(1, 14),
    ]

    def table(data, widths=None):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1120")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ]))
        return t

    story.append(Paragraph("Overview", styles["Heading2"]))
    story.append(table([
        ["Metric", "Value"],
        ["Total predictions", summary["total"]],
        ["Normal traffic", summary["normal"]],
        ["Attack traffic", summary["attacks"]],
        ["Detection rate", f"{summary['detection_rate']}%"],
        ["Open alerts", summary["open_alerts"]],
        ["Open incidents", summary["open_incidents"]],
    ], [260, 120]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Attack types", styles["Heading2"]))
    rows = [["Attack type", "Count"]] + [list(r) for r in summary["attack_types"]]
    if len(rows) == 1:
        rows.append(["No attacks recorded", 0])
    story.append(table(rows, [260, 120]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Latest attacks", styles["Heading2"]))
    rows = [["Time", "Protocol", "Service", "Flag", "Attack"]]
    for r in db.get_recent_attacks(25):
        rows.append([r["time"], r["protocol"], r["service"], r["flag"], r["prediction"]])
    if len(rows) == 1:
        rows.append(["-", "-", "-", "-", "none"])
    story.append(table(rows))

    doc.build(story)
    return buf.getvalue()
