# AI Automation Lead Intelligence Command Center

AI-powered contractor lead intelligence, revenue leak detection, outreach drafting, ROI tracking, and Make.com-ready workflow infrastructure.

## Features

- Contractor/service-business lead scoring
- Seeded demo leads
- AI summary generation with OpenAI optional fallback
- Rule-based summaries when OpenAI is not configured
- Gmail-ready draft endpoint
- Email/SMS outreach drafting
- Optional Twilio SMS sending
- Make.com webhook support
- Google Sheets sync payload support
- Bulk lead import API
- Lead source template API
- Contractor intelligence cards
- ROI dashboard
- Login foundation with ADMIN_USERNAME and ADMIN_PASSWORD
- Render-safe deployment
- SQLite fallback when DATABASE_URL is not set

## API Endpoints

GET /api/health  
GET /api/leads  
GET /api/lead-source-template  
POST /api/add-lead  
POST /api/import-leads  
POST /api/outreach/<lead_id>  
POST /api/gmail-draft/<lead_id>  
POST /api/sheets-sync/<lead_id>  
POST /api/send-sms/<lead_id>  
POST /api/update-lead  
POST /api/regenerate-summary/<lead_id>  

## Render Deployment

Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app

Root directory:
leave blank

Branch:
main

## Environment Variables

Required:
PYTHON_VERSION = 3.11.9

Optional:
BOOKING_LINK  
MAKE_WEBHOOK_URL  
OPENAI_API_KEY  
ADMIN_USERNAME  
ADMIN_PASSWORD  
SECRET_KEY  
DATABASE_URL  
TWILIO_SID  
TWILIO_TOKEN  
TWILIO_FROM  

## Business Value

This app helps AI automation sellers and contractors identify missed revenue, slow follow-up, weak lead tracking, hiring strain, CRM gaps, and automation opportunities.

Position it as:

AI Lead Intelligence and Revenue Recovery System for contractors and service businesses.
