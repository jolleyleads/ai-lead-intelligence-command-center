from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import hashlib
import os
import requests

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "demo-secret-key-change-in-production")

db_url = os.getenv("DATABASE_URL", "sqlite:///lead_intelligence.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

BOOKING_LINK = os.getenv("BOOKING_LINK", "https://calendly.com/your-link/demo")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")

TARGET_INDUSTRIES = [
    "hvac", "plumbing", "roofing", "electrician", "electrical contractor",
    "restoration", "remodeling", "solar", "med spa", "dental", "contractor"
]

HIGH_SIGNALS = [
    "missed calls", "never called back", "slow response", "hard to reach",
    "hiring dispatcher", "dispatcher", "scheduler", "appointment setter",
    "csr", "too many leads", "follow up", "crm", "urgent",
    "need help scheduling", "bad communication", "overwhelmed",
    "no call back", "missed lead", "lost lead", "estimate never sent"
]

MEDIUM_SIGNALS = [
    "hiring", "busy", "growing", "calls", "leads", "quote", "estimate",
    "appointments", "reviews", "website", "forms", "booking", "expanding",
    "office admin", "customer service", "sales coordinator"
]

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
    reviews_signal = db.Column(db.Text)
    hiring_signal = db.Column(db.Text)
    website_weakness = db.Column(db.Text)
    business_pain = db.Column(db.Text)
    recommended_automation = db.Column(db.Text)
    next_best_action = db.Column(db.Text)
    ai_summary = db.Column(db.Text)
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

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not ADMIN_USERNAME or not ADMIN_PASSWORD:
            return f(*args, **kwargs)
        if session.get("logged_in"):
            return f(*args, **kwargs)
        return redirect(url_for("login"))
    return wrapper

def lead_hash(company, website, phone, email):
    raw = f"{company}|{website}|{phone}|{email}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def calc_roi(job_value, missed, close_rate):
    try:
        return round(float(job_value or 0) * int(missed or 0) * float(close_rate or 0.25), 2)
    except Exception:
        return 0

def score_lead(industry, signal_text, website="", reviews_signal="", hiring_signal="", website_weakness=""):
    text = f"{industry} {signal_text} {website} {reviews_signal} {hiring_signal} {website_weakness}".lower()
    score = 10
    reasons = []

    for item in TARGET_INDUSTRIES:
        if item in text:
            score += 12
            reasons.append(f"Target service industry match: {item}")

    for item in HIGH_SIGNALS:
        if item in text:
            score += 14
            reasons.append(f"High-intent automation signal: {item}")

    for item in MEDIUM_SIGNALS:
        if item in text:
            score += 6
            reasons.append(f"Medium buying signal: {item}")

    if any(x in text for x in ["missed calls", "never called back", "slow response", "hard to reach", "no call back"]):
        score += 18
        reasons.append("Revenue leak from slow or missed follow-up")

    if any(x in text for x in ["dispatcher", "scheduler", "appointment setter", "csr", "office admin"]):
        score += 16
        reasons.append("Hiring for roles automation can reduce")

    if "crm" not in text and any(x in text for x in ["leads", "appointments", "calls", "estimates"]):
        score += 8
        reasons.append("Possible missing CRM or lead tracking process")

    score = min(score, 100)

    if score >= 75:
        priority = "High"
        pitch = "Lead with missed revenue, response-speed pain, and booked-job recovery angle."
        solution = "AI missed-call response, CRM pipeline, SMS/email follow-up, calendar booking, ROI tracking, and dashboard reporting."
    elif score >= 45:
        priority = "Medium"
        pitch = "Lead with follow-up, organization, and workflow-efficiency angle."
        solution = "Lead tracking, reminders, email/SMS templates, booking links, and pipeline visibility."
    else:
        priority = "Low"
        pitch = "Nurture lead until stronger pain appears."
        solution = "Basic monitoring, follow-up reminders, and future automation audit."

    return score, priority, "; ".join(reasons) or "No strong automation pain detected yet.", pitch, solution

def fallback_ai_summary(lead):
    return (
        f"{lead.company} appears to be a {lead.industry or 'service'} business with possible automation opportunities. "
        f"Detected pain: {lead.pain_summary}. "
        f"Estimated recoverable monthly revenue: ${lead.projected_monthly_recovered:,.0f}. "
        f"Recommended next action: {lead.next_best_action or 'Start with a short automation audit and demo.'}"
    )

def ai_summary_for_lead(lead):
    if not OPENAI_API_KEY:
        return fallback_ai_summary(lead)

    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You summarize contractor leads for an AI automation sales dashboard."},
                {"role": "user", "content": f"Company: {lead.company}\nIndustry: {lead.industry}\nSignals: {lead.signal_text}\nReviews: {lead.reviews_signal}\nHiring: {lead.hiring_signal}\nWebsite weakness: {lead.website_weakness}\nPain: {lead.pain_summary}\nROI: {lead.projected_monthly_recovered}\nWrite a concise lead intelligence summary."}
            ],
            "temperature": 0.4
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=20)
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return fallback_ai_summary(lead)

def build_messages(lead):
    subject = f"Quick idea to help {lead.company} capture more booked jobs"
    pain = lead.business_pain or lead.pain_summary or "missed leads and slow follow-up"
    roi = f"${lead.projected_monthly_recovered:,.0f}/month" if lead.projected_monthly_recovered else "more monthly revenue"

    email = f"""Hi {lead.contact_name or 'there'},

I noticed {lead.company} may have an opportunity to tighten up lead response and follow-up.

The main signal I saw:
{pain}

I build AI automation systems for {lead.industry or 'service'} businesses that help capture missed calls, organize leads, automate follow-up, and turn more inquiries into booked appointments.

Based on the numbers, even a small improvement could potentially recover around {roi}.

The system can help with:
- missed-call response
- SMS/email follow-up
- lead scoring
- calendar booking
- CRM-style pipeline tracking
- ROI reporting

Would it make sense to show you a quick demo?

Book here: {BOOKING_LINK}

Best,
Matthew Jolley
AI Automation Engineer
https://github.com/jolleyleads
"""

    sms = f"Hi {lead.contact_name or ''}, this is Matthew. I help {lead.industry or 'contractor'} companies recover missed leads with AI follow-up, SMS/email workflows, booking, and ROI tracking. Quick demo? {BOOKING_LINK}"

    return subject, email, sms

def send_sms_if_configured(to, body):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, to]):
        return {"sent": False, "reason": "Twilio not configured; SMS saved as draft."}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    r = requests.post(url, data={"From": TWILIO_FROM, "To": to, "Body": body}, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=15)
    return {"sent": r.ok, "status_code": r.status_code, "response": r.text[:300]}

def create_or_update_lead(data):
    company = data.get("company", "Unknown Company")
    website = data.get("website", "")
    phone = data.get("phone", "")
    email = data.get("email", "")
    lead_id = lead_hash(company, website, phone, email)

    existing = Lead.query.filter_by(lead_id=lead_id).first()
    if existing:
        return existing, False

    score, priority, pain, pitch, solution = score_lead(
        data.get("industry", ""),
        data.get("signal_text", ""),
        website,
        data.get("reviews_signal", ""),
        data.get("hiring_signal", ""),
        data.get("website_weakness", "")
    )

    roi = calc_roi(
        data.get("estimated_job_value", 0),
        data.get("missed_leads_per_month", 0),
        data.get("close_rate", 0.25)
    )

    business_pain = data.get("business_pain") or pain
    recommended_automation = data.get("recommended_automation") or solution
    next_best_action = data.get("next_best_action") or "Generate outreach draft and book a short automation audit."

    lead = Lead(
        lead_id=lead_id,
        company=company,
        industry=data.get("industry", ""),
        contact_name=data.get("contact_name", ""),
        phone=phone,
        email=email,
        website=website,
        city=data.get("city", ""),
        state=data.get("state", ""),
        source=data.get("source", "Manual/API"),
        signal_text=data.get("signal_text", ""),
        reviews_signal=data.get("reviews_signal", ""),
        hiring_signal=data.get("hiring_signal", ""),
        website_weakness=data.get("website_weakness", ""),
        business_pain=business_pain,
        recommended_automation=recommended_automation,
        next_best_action=next_best_action,
        score=score,
        priority=priority,
        pain_summary=pain,
        recommended_pitch=pitch,
        recommended_solution=solution,
        estimated_job_value=float(data.get("estimated_job_value") or 0),
        missed_leads_per_month=int(data.get("missed_leads_per_month") or 0),
        close_rate=float(data.get("close_rate") or 0.25),
        projected_monthly_recovered=roi,
        status=data.get("status", "New"),
        notes=data.get("notes", "")
    )

    lead.ai_summary = fallback_ai_summary(lead)
    db.session.add(lead)
    db.session.commit()

    lead.ai_summary = ai_summary_for_lead(lead)
    db.session.commit()

    return lead, True

def lead_to_dict(x):
    return {
        "id": x.lead_id,
        "company": x.company,
        "industry": x.industry,
        "contact_name": x.contact_name,
        "phone": x.phone,
        "email": x.email,
        "website": x.website,
        "city": x.city,
        "state": x.state,
        "source": x.source,
        "signal_text": x.signal_text,
        "reviews_signal": x.reviews_signal,
        "hiring_signal": x.hiring_signal,
        "website_weakness": x.website_weakness,
        "business_pain": x.business_pain,
        "recommended_automation": x.recommended_automation,
        "next_best_action": x.next_best_action,
        "ai_summary": x.ai_summary,
        "score": x.score,
        "priority": x.priority,
        "pain_summary": x.pain_summary,
        "recommended_pitch": x.recommended_pitch,
        "recommended_solution": x.recommended_solution,
        "status": x.status,
        "notes": x.notes,
        "estimated_job_value": x.estimated_job_value,
        "missed_leads_per_month": x.missed_leads_per_month,
        "close_rate": x.close_rate,
        "projected_monthly_recovered": x.projected_monthly_recovered,
        "created_at": x.created_at.isoformat() if x.created_at else None
    }

def seed_leads():
    examples = [
        {
            "company": "Coastal HVAC Pros",
            "industry": "HVAC",
            "city": "Virginia Beach",
            "state": "VA",
            "source": "Demo Signal",
            "signal_text": "Hiring dispatcher and customer service representative. Reviews mention slow response, missed calls, and hard to reach during busy season.",
            "reviews_signal": "Several reviews mention hard to reach and slow callback times.",
            "hiring_signal": "Hiring dispatcher and customer service representative.",
            "website_weakness": "No obvious instant booking or missed-call recovery workflow visible.",
            "estimated_job_value": 1500,
            "missed_leads_per_month": 20,
            "close_rate": 0.25,
            "website": "https://example.com"
        },
        {
            "company": "Tidewater Plumbing Group",
            "industry": "Plumbing",
            "city": "Norfolk",
            "state": "VA",
            "source": "Demo Signal",
            "signal_text": "Busy plumbing company hiring scheduler. Needs help managing calls, estimates, appointments, and follow up.",
            "reviews_signal": "Customers mention delays getting estimates.",
            "hiring_signal": "Hiring scheduler.",
            "website_weakness": "Website has quote form but no visible automated follow-up.",
            "estimated_job_value": 900,
            "missed_leads_per_month": 18,
            "close_rate": 0.30,
            "website": "https://example.com"
        },
        {
            "company": "Lone Star Electrical Services",
            "industry": "Electrical Contractor",
            "city": "Dallas",
            "state": "TX",
            "source": "Demo Signal",
            "signal_text": "Growing electrical contractor hiring office admin and sales coordinator. Many leads and quote requests.",
            "reviews_signal": "Reviews suggest good work but inconsistent communication.",
            "hiring_signal": "Hiring office admin and sales coordinator.",
            "website_weakness": "No AI follow-up, lead scoring, or booking workflow visible.",
            "estimated_job_value": 1200,
            "missed_leads_per_month": 15,
            "close_rate": 0.25,
            "website": "https://example.com"
        }
    ]

    for item in examples:
        create_or_update_lead(item)

@app.before_request
def setup():
    db.create_all()
    if Lead.query.count() == 0:
        seed_leads()

@app.route("/login", methods=["GET", "POST"])
def login():
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        return redirect(url_for("index"))

    error = ""
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Invalid login."

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    leads = Lead.query.order_by(Lead.score.desc(), Lead.created_at.desc()).all()
    outreach = Outreach.query.order_by(Outreach.created_at.desc()).limit(20).all()

    total_revenue = sum([x.projected_monthly_recovered or 0 for x in leads])
    high_count = len([x for x in leads if x.priority == "High"])
    avg_score = round(sum([x.score or 0 for x in leads]) / len(leads), 1) if leads else 0

    metrics = {
        "total_leads": len(leads),
        "high_priority": high_count,
        "projected_revenue": total_revenue,
        "outreach_count": Outreach.query.count(),
        "average_score": avg_score,
        "new_count": len([x for x in leads if x.status == "New"]),
        "contacted_count": len([x for x in leads if x.status == "Contacted"]),
        "demo_mode": not ADMIN_USERNAME or not ADMIN_PASSWORD
    }

    return render_template("index.html", leads=leads, outreach=outreach, metrics=metrics, booking_link=BOOKING_LINK)

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "system": "AI Automation Lead Intelligence Command Center",
        "render_safe": True,
        "requires_paid_keys": False
    })

@app.route("/api/leads")
def api_leads():
    leads = Lead.query.order_by(Lead.score.desc()).all()
    return jsonify({"count": len(leads), "leads": [lead_to_dict(x) for x in leads]})

@app.route("/api/add-lead", methods=["POST"])
def add_lead():
    data = request.get_json(silent=True) or {}
    lead, created = create_or_update_lead(data)

    if MAKE_WEBHOOK_URL:
        try:
            requests.post(MAKE_WEBHOOK_URL, json=lead_to_dict(lead), timeout=10)
        except Exception:
            pass

    return jsonify({"status": "saved" if created else "duplicate", "lead": lead_to_dict(lead)})

@app.route("/api/import-leads", methods=["POST"])
def import_leads():
    data = request.get_json(silent=True) or {}
    source = data.get("source", "Bulk Import")
    incoming = data.get("leads", [])

    created = 0
    duplicates = 0
    results = []

    for item in incoming:
        item["source"] = item.get("source", source)
        lead, was_created = create_or_update_lead(item)
        if was_created:
            created += 1
        else:
            duplicates += 1
        results.append(lead_to_dict(lead))

    return jsonify({
        "status": "import_complete",
        "created": created,
        "duplicates": duplicates,
        "count": len(results),
        "leads": results
    })

@app.route("/api/lead-source-template")
def lead_source_template():
    return jsonify({
        "purpose": "Use this endpoint format from Make.com, Apify, Google Sheets, Yelp, Indeed, or Google Maps scrapers.",
        "send_to": "/api/import-leads",
        "method": "POST",
        "example_payload": {
            "source": "Google Maps / Apify / Make.com / Google Sheets",
            "leads": [
                {
                    "company": "Example HVAC Company",
                    "industry": "HVAC",
                    "city": "Virginia Beach",
                    "state": "VA",
                    "phone": "555-555-5555",
                    "email": "owner@example.com",
                    "website": "https://example.com",
                    "signal_text": "Reviews mention slow response and missed calls.",
                    "reviews_signal": "Customer complained about no callback.",
                    "hiring_signal": "Hiring dispatcher.",
                    "website_weakness": "No booking automation visible.",
                    "estimated_job_value": 1500,
                    "missed_leads_per_month": 12,
                    "close_rate": 0.25
                }
            ]
        }
    })

@app.route("/api/outreach/<lead_id>", methods=["POST"])
def outreach(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404

    subject, email_body, sms_body = build_messages(lead)

    db.session.add(Outreach(lead_id=lead.lead_id, channel="email", subject=subject, message=email_body, status="drafted"))
    db.session.add(Outreach(lead_id=lead.lead_id, channel="sms", subject="", message=sms_body, status="drafted"))
    db.session.commit()

    return jsonify({
        "status": "drafted",
        "gmail_ready": True,
        "email_subject": subject,
        "email_body": email_body,
        "sms_body": sms_body,
        "human_approval_required": True
    })

@app.route("/api/gmail-draft/<lead_id>", methods=["POST"])
def gmail_draft(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404

    subject, email_body, sms_body = build_messages(lead)

    db.session.add(Outreach(lead_id=lead.lead_id, channel="gmail_draft", subject=subject, message=email_body, status="drafted"))
    db.session.commit()

    return jsonify({
        "status": "gmail_draft_ready",
        "to": lead.email,
        "subject": subject,
        "body": email_body,
        "note": "This does not send automatically. Use Make.com or Gmail approval workflow to create/send drafts."
    })

@app.route("/api/sheets-sync/<lead_id>", methods=["POST"])
def sheets_sync(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404

    payload = lead_to_dict(lead)

    if MAKE_WEBHOOK_URL:
        try:
            r = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=10)
            return jsonify({"status": "sent_to_make_webhook", "status_code": r.status_code, "payload": payload})
        except Exception as e:
            return jsonify({"status": "webhook_failed", "error": str(e), "payload": payload})

    return jsonify({
        "status": "payload_ready",
        "note": "Add MAKE_WEBHOOK_URL env var to send this to Make.com / Google Sheets.",
        "payload": payload
    })

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

@app.route("/api/regenerate-summary/<lead_id>", methods=["POST"])
def regenerate_summary(lead_id):
    lead = Lead.query.filter_by(lead_id=lead_id).first()
    if not lead:
        return jsonify({"status": "not_found"}), 404

    lead.ai_summary = ai_summary_for_lead(lead)
    db.session.commit()

    return jsonify({"status": "summary_updated", "ai_summary": lead.ai_summary})

if __name__ == "__main__":
    app.run(debug=True)
