"""Optional operator-only SMTP alert. Agents never receive server credentials."""
from __future__ import annotations
import os,smtplib
from email.message import EmailMessage

def alert(record):
    to=os.getenv('BENCH_OPERATOR_EMAIL','')
    host=os.getenv('BENCH_SMTP_HOST','')
    if not to or not host:return {'status':'inbox_only'}
    msg=EmailMessage()
    msg['From']=os.getenv('BENCH_FROM_EMAIL',os.getenv('BENCH_SMTP_USER','bench@example.invalid'))
    msg['To']=to
    msg['Subject']=f"[SwarmBench] {record['category']} from {record['agent']}"
    msg.set_content(f"Incident report {record['id']}\n\nSummary:\n{record['summary']}\n\nEvidence:\n{record['evidence']}\n\nThis is an evaluation contact; do not give task hints.")
    try:
        with smtplib.SMTP(host,int(os.getenv('BENCH_SMTP_PORT','587')),timeout=8) as conn:
            conn.starttls()
            user=os.getenv('BENCH_SMTP_USER','')
            password=os.getenv('BENCH_SMTP_PASSWORD','')
            if user and password:conn.login(user,password)
            conn.send_message(msg)
        return {'status':'email_sent'}
    except Exception as exc:
        return {'status':'email_failed','detail':type(exc).__name__}
