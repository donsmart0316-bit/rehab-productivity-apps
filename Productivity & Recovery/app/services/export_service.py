from __future__ import annotations

from io import BytesIO


def plan_markdown(profile: dict, prediction: dict, plan: dict, coaching: str) -> str:
    lines = [
        f"# Daily Productivity & Recovery Plan - {plan.get('date')}",
        "",
        f"User: {profile.get('name', 'User')}",
        "",
        "## Predictions",
        f"- Productivity: {prediction.get('productivity_score')}/100",
        f"- Burnout Risk: {prediction.get('burnout_risk')}",
        f"- Recovery: {prediction.get('recovery_score')}/100",
        f"- Sleep Debt: {prediction.get('sleep_debt')} hours",
        "",
        "## Schedule",
    ]
    for item in plan.get("schedule", []):
        lines.append(f"- {item['start']}-{item['end']}: {item['title']} - {item.get('reason', '')}")
    lines.extend(["", "## Coaching Notes", coaching])
    return "\n".join(lines)


def plan_text(profile: dict, prediction: dict, plan: dict, coaching: str) -> str:
    return plan_markdown(profile, prediction, plan, coaching).replace("#", "").replace("*", "")


def plan_pdf_bytes(profile: dict, prediction: dict, plan: dict, coaching: str) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return None

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 48
    text = pdf.beginText(48, y)
    text.setFont("Helvetica", 10)
    for line in plan_text(profile, prediction, plan, coaching).splitlines():
        if y < 54:
            pdf.drawText(text)
            pdf.showPage()
            y = height - 48
            text = pdf.beginText(48, y)
            text.setFont("Helvetica", 10)
        text.textLine(line[:105])
        y -= 13
    pdf.drawText(text)
    pdf.save()
    return buffer.getvalue()
