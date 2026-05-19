from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib, os, json, requests

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///lead_intelligence.db").replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

BOOKING_LINK = os.getenv("BOOKING_LINK", "https://calendly.com/your-link/demo")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")

TARGET_INDUSTRIES = ["hvac","plumbing","roofing","electrician","electrical contractor","restoration","remodeling","solar","med spa","dental"]
HIGH_SIGNALS = ["missed calls","never called back","slow response","hard to reach","hiring dispatcher","dispatcher","scheduler","appointment setter","csr","too many leads","follow up","crm","urgent","need help scheduling"]
MEDIUM_SIGNALS = ["hiring","busy","growing","calls","leads","quote","estimate","appointments","reviews","website","forms","booking"]

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.String(120), unique=True)
    company = db.Column(db.String(200))
    industry = db.Column(db.String(120))
    contact_name = db.Column(db.String(200))
    phone = db.Column(db.String(100))
    email = db.Column(db.String(200))
    website = db.Column(db.String(300))
    city = db.Column(db.String(120))
    state = db.Column(db.String(80))
    source = db.Column(db.String(200))
    signal_text = db.Column(db.Text)
    score = db.Column(db.Integer)
    priority = db.Column(db.String(80))
    pain_summary = db.Column(db.Text)
    recommended_pitch = db.Column(db.Text)
    recommended_solution = db.Column(db.Text)
    status = db.Column(db.String(100), default="New")
    notes = db.Column(db.Text)
    estimated_job_value = db.Column(db.Float, default=0)
    missed_leads_per_month = db.Column(db.Integer, default=0)
    close_rate = db.Column(db.Float, default=0.25)
    projected_monthly_recovered = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Outreach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.String(120))
    channel = db.Column(db.String(50))
    subject = db.Column(db.String(300))
    message = db.Column(db.Text)
    status = db.Column(db.String(80), default="drafted")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def lead_hash(company, website, phone, email):
    return hashlib.md5(f"{company}|{website}|{phone}|{email}".encode()).hexdigest()

def score_lead(industry, signal_text, website=""):
    text = f"{industry} {signal_text} {website}".lower()
    score, reasons = 10, []

    for x in TARGET_INDUSTRIES:
        if x in text:
            score += 12
            reasons.append(f"Target contractor/service industry: {x}")

    for x in HIGH_SIGNALS:
        if x in text:
            score += 14
            reasons.append(f"High buying signal: {x}")

    for x in MEDIUM_SIGNALS:
        if x in text:
            score += 6
            reasons.append(f"Medium buying signal: {x}")

    if any(x in text for x in ["missed calls","never called back","slow response","hard to reach"]):
        score += 18
        reasons.append("Customer communication/revenue leak detected")

    if any(x in text for x in ["dispatcher","scheduler","appointment setter","csr"]):
        score += 16
        reasons.append("Hiring for work automation can reduce")

    score = min(score, 100)

    if score >= 75:
        priority = "High"
        pitch = "Lead with missed revenue, faster response, automated follow-up, and booked-job recovery."
        solution = "Missed-call text back, lead capture, SMS/email follow-up, calendar booking, CRM pipeline, and ROI dashboard."
    elif score >= 45:
        priority = "Medium"
        pitch = "Lead with organization, follow-up, and workflow efficiency."
        solution = "Lead tracking, reminders, booking workflow, and automated follow-up."
    else:
        priority = "Low"
        pitch = "Nurture lead until stronger pain appears."
        solution = "Basic monitoring and future automation audit."

    return score, priority, "; ".join(reasons) or "No strong pain detected yet.", pitch, solution

def calc_roi(job_value, missed, close_rate):
    try:
        return round(float(job_value) * int(missed) * float(close_rate), 2)
    except:
        return 0

def build_messages(lead):
    booking = BOOKING_LINK
    subject = f"Quick idea to help {lead.company} capture more booked jobs"
    email = f"""Hi {lead.contact_name or 'there'},

I noticed {lead.company} may have a follow-up or lead-response opportunity.

I build AI workflow systems for {lead.industry or 'contractor'} companies that help capture missed calls, organize leads, automate follow-up, and turn more inquiries into booked appointments.

Based on the signals I found, the opportunity looks like:
{lead.pain_summary}

A simple system could help with:
- missed-call text back
- automated email/SMS follow-up
- lead scoring
- calendar booking
- ROI tracking

Would it make sense to show you a quick demo?

Book here: {booking}

Best,
Matthew Jolley
AI Automation Engineer
"""
    sms = f"Hi {lead.contact_name or ''}, this is Matthew. I help {lead.industry or 'contractor'} companies capture missed leads with AI follow-up, SMS/email automation, and booking workflows. Quick demo? {booking}"
    return subject, email, sms

def send_sms_if_configured(to, body):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, to]):
        return {"sent": False, "reason": "Twilio not configured; SMS saved as draft."}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    r = requests.post(url, data={"From": TWILIO_FROM, "To": to, "Body": body}, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=15)
    return {"sent": r.ok, "status_code": r.status_code, "response": r.text[:300]}

@app.before_request
def setup():
    db.create_all()

@app.route("/")
def index():
    leads = Lead.query.order_by(Lead.score.desc(), Lead.created_at.desc()).all()
    outreach = Outreach.query.order_by(Outreach.created_at.desc()).limit(20).all()
    total_pipeline = sum([x.projected_monthly_recovered or 0 for x in leads])
    return render_template("index.html", leads=leads, outreach=outreach, total_pipeline=total_pipeline, booking_link=BOOKING_LINK)

@app.route("/api/health")
def health():
    return jsonify({"status": "online", "system": "Contractor AI Lead Intelligence + Outreach + ROI Command Center"})

@app.route("/api/leads")
def api_leads():
    leads = Lead.query.order_by(Lead.score.desc()).all()
    return jsonify({"count": len(leads), "leads": [lead_to_dict(x) for x in leads]})

def lead_to_dict(x):
    return {
        "id": x.lead_id, "company": x.company, "industry": x.industry,
        "contact_name": x.contact_name, "phone": x.phone, "email": x.email,
        "website": x.website, "city": x.city, "state": x.state,
        "source": x.source, "signal_text": x.signal_text, "score": x.score,
        "priority": x.priority, "pain_summary": x.pain_summary,
        "recommended_pitch": x.recommended_pitch,
        "recommended_solution": x.recommended_solution,
        "status": x.status, "notes": x.notes,
        "estimated_job_value": x.estimated_job_value,
        "missed_leads_per_month": x.missed_leads_per_month,
        "close_rate": x.close_rate,
        "projected_monthly_recovered": x.projected_monthly_recovered
    }

@app.route("/api/add-lead", methods=["POST"])
def add_lead():
    data = request.get_json(silent=True) or {}
    company = data.get("company", "Unknown Company")
    website = data.get("website", "")
    phone = data.get("phone", "")
    email = data.get("email", "")
    lead_id = lead_hash(company, website, phone, email)

    existing = Lead.query.filter_by(lead_id=lead_id).first()
    if existing:
        return jsonify({"status": "duplicate", "lead": lead_to_dict(existing)})

    score, priority, pain, pitch, solution = score_lead(data.get("industry",""), data.get("signal_text",""), website)
    roi = calc_roi(data.get("estimated_job_value", 0), data.get("missed_leads_per_month", 0), data.get("close_rate", 0.25))

    lead = Lead(
        lead_id=lead_id, company=company, industry=data.get("industry",""),
        contact_name=data.get("contact_name",""), phone=phone, email=email,
        website=website, city=data.get("city",""), state=data.get("state",""),
        source=data.get("source","Manual/API"), signal_text=data.get("signal_text",""),
        score=score, priority=priority, pain_summary=pain,
        recommended_pitch=pitch, recommended_solution=solution,
        estimated_job_value=float(data.get("estimated_job_value") or 0),
        missed_leads_per_month=int(data.get("missed_leads_per_month") or 0),
        close_rate=float(data.get("close_rate") or 0.25),
        projected_monthly_recovered=roi,
        status="New", notes=data.get("notes","")
    )
    db.session.add(lead)
    db.session.commit()

    if MAKE_WEBHOOK_URL:
        try:
            requests.post(MAKE_WEBHOOK_URL, json=lead_to_dict(lead), timeout=10)
        except Exception:
            pass

    return jsonify({"status": "saved", "lead": lead_to_dict(lead)})

@app.route("/api/outreach/<lead_id>", methods=["POST"])
def outreach(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404

    subject, email_body, sms_body = build_messages(lead)

    db.session.add(Outreach(lead_id=lead.lead_id, channel="email", subject=subject, message=email_body, status="drafted"))
    db.session.add(Outreach(lead_id=lead.lead_id, channel="sms", subject="", message=sms_body, status="drafted"))
    db.session.commit()

    return jsonify({"status": "drafted", "email_subject": subject, "email_body": email_body, "sms_body": sms_body})

@app.route("/api/send-sms/<lead_id>", methods=["POST"])
def send_sms(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404
    _, _, sms_body = build_messages(lead)
    result = send_sms_if_configured(lead.phone, sms_body)
    db.session.add(Outreach(lead_id=lead.lead_id, channel="sms", message=sms_body, status="sent" if result.get("sent") else "drafted"))
    db.session.commit()
    return jsonify(result)

@app.route("/api/update-lead", methods=["POST"])
def update_lead():
    data = request.get_json(silent=True) or {}
    lead = Lead.query.filter_by(lead_id=data.get("id")).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404
    lead.status = data.get("status", lead.status)
    lead.notes = data.get("notes", lead.notes)
    db.session.commit()
    return jsonify({"status": "updated", "lead": lead_to_dict(lead)})

if __name__ == "__main__":
    app.run(debug=True)
