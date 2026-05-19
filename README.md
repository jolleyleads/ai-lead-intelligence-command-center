# Contractor AI Lead Intelligence Command Center

This system helps contractor companies find and prioritize leads with automation pain.

## Features
- Contractor lead intake
- Lead scoring
- Pain detection
- Email/SMS outreach drafting
- Optional Twilio SMS sending
- Optional Make.com webhook automation
- Calendar booking link
- ROI tracking
- Render-ready deployment

## Environment Variables
BOOKING_LINK = your Calendly or Google Calendar booking link  
MAKE_WEBHOOK_URL = optional Make.com webhook  
TWILIO_SID = optional Twilio SID  
TWILIO_TOKEN = optional Twilio token  
TWILIO_FROM = optional Twilio phone number  

## Render
Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app
