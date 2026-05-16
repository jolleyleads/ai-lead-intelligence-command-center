from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import os

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lead_intelligence.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

TARGET_INDUSTRIES = [
    "hvac",
    "electrician",
    "electrical contractor",
    "roofing",
    "plumbing",
    "restoration",
    "remodeling",
    "solar",
    "med spa",
    "dental"
]

HIGH_SIGNAL_KEYWORDS = [
    "need dispatcher",
    "hiring dispatcher",
    "office admin",
    "appointment setter",
    "csr",
    "customer service representative",
    "sales coordinator",
    "scheduler",
    "missed calls",
    "never called back",
    "hard to reach",
    "bad communication",
    "slow response",
    "overwhelmed",
    "too many leads",
    "need help scheduling",
    "follow up",
    "lead tracking",
    "crm",
    "automation",
    "hiring immediately",
    "urgent"
]

MEDIUM_SIGNAL_KEYWORDS = [
    "hiring",
    "growing",
    "expanding",
    "busy",
    "booking",
    "calls",
    "leads",
    "estimate",
    "quote",
    "appointments",
    "reviews",
    "website",
    "forms"
]

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.String(100), unique=True)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(120))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def make_lead_id(company, website, phone, email):
    raw = f"{company}|{website}|{phone}|{email}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def score_lead(industry, signal_text, website=""):
    text = f"{industry} {signal_text} {website}".lower()
    score = 10
    reasons = []

    for industry_name in TARGET_INDUSTRIES:
        if industry_name in text:
            score += 12
            reasons.append(f"Target industry match: {industry_name}")

    for keyword in HIGH_SIGNAL_KEYWORDS:
        if keyword in text:
            score += 14
            reasons.append(f"High-intent signal: {keyword}")

    for keyword in MEDIUM_SIGNAL_KEYWORDS:
        if keyword in text:
            score += 6
            reasons.append(f"Medium signal: {keyword}")

    if "never called back" in text or "hard to reach" in text or "slow response" in text:
        score += 18
        reasons.append("Customer communication problem detected")

    if "dispatcher" in text or "scheduler" in text or "appointment setter" in text:
        score += 16
        reasons.append("Hiring for roles automation can reduce")

    if "crm" not in text and ("leads" in text or "appointments" in text or "calls" in text):
        score += 8
        reasons.append("Possible missing CRM / lead tracking")

    if score > 100:
        score = 100

    if score >= 75:
        priority = "High"
        pitch = "Lead with missed revenue, faster response, automated follow-up, and booked-job recovery."
        solution = "AI lead follow-up system, missed-call automation, CRM pipeline, Gmail/SMS follow-up, and dashboard reporting."
    elif score >= 45:
        priority = "Medium"
        pitch = "Lead with organization, follow-up, and operational efficiency."
        solution = "Simple CRM, automated reminders, lead tracking, and follow-up workflows."
    else:
        priority = "Low"
        pitch = "Nurture lead. Not enough urgent pain yet."
        solution = "Basic monitoring and future automation audit."

    pain_summary = "; ".join(reasons) if reasons else "No strong automation pain detected yet."

    return score, priority, pain_summary, pitch, solution

def seed_leads():
    examples = [
        {
            "company": "Coastal HVAC Pros",
            "industry": "HVAC",
            "city": "Virginia Beach",
            "state": "VA",
            "source": "Demo Signal",
            "signal_text": "Hiring dispatcher and customer service representative. Reviews mention slow response and hard to reach during busy season.",
            "website": "https://example.com"
        },
        {
            "company": "Tidewater Plumbing Group",
            "industry": "Plumbing",
            "city": "Norfolk",
            "state": "VA",
            "source": "Demo Signal",
            "signal_text": "Busy plumbing company hiring scheduler. Needs help managing calls, estimates, appointments, and follow up.",
            "website": "https://example.com"
        },
        {
            "company": "Lone Star Electrical Services",
            "industry": "Electrical Contractor",
            "city": "Dallas",
            "state": "TX",
            "source": "Demo Signal",
            "signal_text": "Growing electrical contractor hiring office admin and sales coordinator. Many leads and quote requests.",
            "website": "https://example.com"
        }
    ]

    for item in examples:
        lead_id = make_lead_id(item["company"], item["website"], "", "")

        if not Lead.query.filter_by(lead_id=lead_id).first():
            score, priority, pain_summary, pitch, solution = score_lead(
                item["industry"],
                item["signal_text"],
                item["website"]
            )

            lead = Lead(
                lead_id=lead_id,
                company=item["company"],
                industry=item["industry"],
                contact_name="",
                phone="",
                email="",
                website=item["website"],
                city=item["city"],
                state=item["state"],
                source=item["source"],
                signal_text=item["signal_text"],
                score=score,
                priority=priority,
                pain_summary=pain_summary,
                recommended_pitch=pitch,
                recommended_solution=solution,
                status="New",
                notes="Seed lead for demo"
            )

            db.session.add(lead)

    db.session.commit()

@app.before_request
def setup():
    db.create_all()
    if Lead.query.count() == 0:
        seed_leads()

@app.route("/")
def index():
    leads = Lead.query.order_by(Lead.score.desc(), Lead.created_at.desc()).all()
    activities = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
    return render_template("index.html", leads=leads, activities=activities)

@app.route("/api/leads")
def api_leads():
    industry = request.args.get("industry", "").lower()
    priority = request.args.get("priority", "").lower()

    query = Lead.query

    if industry:
        query = query.filter(Lead.industry.ilike(f"%{industry}%"))

    if priority:
        query = query.filter(Lead.priority.ilike(f"%{priority}%"))

    leads = query.order_by(Lead.score.desc()).all()

    return jsonify({
        "count": len(leads),
        "leads": [
            {
                "id": lead.lead_id,
                "company": lead.company,
                "industry": lead.industry,
                "contact_name": lead.contact_name,
                "phone": lead.phone,
                "email": lead.email,
                "website": lead.website,
                "city": lead.city,
                "state": lead.state,
                "source": lead.source,
                "signal_text": lead.signal_text,
                "score": lead.score,
                "priority": lead.priority,
                "pain_summary": lead.pain_summary,
                "recommended_pitch": lead.recommended_pitch,
                "recommended_solution": lead.recommended_solution,
                "status": lead.status,
                "notes": lead.notes
            }
            for lead in leads
        ]
    })

@app.route("/api/score", methods=["POST"])
def api_score():
    data = request.get_json(silent=True) or {}

    score, priority, pain_summary, pitch, solution = score_lead(
        data.get("industry", ""),
        data.get("signal_text", ""),
        data.get("website", "")
    )

    return jsonify({
        "score": score,
        "priority": priority,
        "pain_summary": pain_summary,
        "recommended_pitch": pitch,
        "recommended_solution": solution
    })

@app.route("/api/add-lead", methods=["POST"])
def api_add_lead():
    data = request.get_json(silent=True) or {}

    company = data.get("company", "Unknown Company")
    website = data.get("website", "")
    phone = data.get("phone", "")
    email = data.get("email", "")

    lead_id = make_lead_id(company, website, phone, email)

    existing = Lead.query.filter_by(lead_id=lead_id).first()
    if existing:
        return jsonify({
            "status": "duplicate",
            "lead_id": lead_id
        })

    score, priority, pain_summary, pitch, solution = score_lead(
        data.get("industry", ""),
        data.get("signal_text", ""),
        website
    )

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
        score=score,
        priority=priority,
        pain_summary=pain_summary,
        recommended_pitch=pitch,
        recommended_solution=solution,
        status=data.get("status", "New"),
        notes=data.get("notes", "")
    )

    db.session.add(lead)

    activity = Activity(
        event_type="lead_added",
        details=f"Added {company} with score {score} and priority {priority}"
    )

    db.session.add(activity)
    db.session.commit()

    return jsonify({
        "status": "saved",
        "lead_id": lead_id,
        "score": score,
        "priority": priority,
        "pain_summary": pain_summary,
        "recommended_pitch": pitch,
        "recommended_solution": solution
    })

@app.route("/api/update-lead", methods=["POST"])
def api_update_lead():
    data = request.get_json(silent=True) or {}
    lead = Lead.query.filter_by(lead_id=data.get("id")).first()

    if not lead:
        return jsonify({"status": "not_found"}), 404

    lead.status = data.get("status", lead.status)
    lead.notes = data.get("notes", lead.notes)

    db.session.add(Activity(
        event_type="lead_updated",
        details=f"Updated {lead.company} to {lead.status}"
    ))

    db.session.commit()

    return jsonify({"status": "updated"})

@app.route("/api/outreach-draft", methods=["POST"])
def api_outreach_draft():
    data = request.get_json(silent=True) or {}

    company = data.get("company", "your company")
    industry = data.get("industry", "service business")
    pain = data.get("pain_summary", "missed leads and slow follow-up")

    subject = f"Quick idea to help {company} capture more booked jobs"

    body = f"""Hi,

I noticed {company} may have an opportunity to tighten up lead follow-up and customer communication.

I build AI-powered workflow systems for {industry} companies that help reduce missed leads, organize follow-up, and turn more calls/forms into booked appointments.

The main thing I focus on is simple:
identify operational revenue leaks and automate them.

Based on the signals I found, the opportunity may be:
{pain}

Would it make sense to show you a quick example of how this could work for your business?

Best,
Matthew Jolley
AI Automation Engineer
https://github.com/jolleyleads
"""

    return jsonify({
        "subject": subject,
        "body": body,
        "mode": "draft_only"
    })

@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "AI Lead Intelligence Command Center online",
        "leads_endpoint": "/api/leads",
        "score_endpoint": "/api/score",
        "add_lead_endpoint": "/api/add-lead",
        "outreach_endpoint": "/api/outreach-draft"
    })

if __name__ == "__main__":
    app.run(debug=True)
