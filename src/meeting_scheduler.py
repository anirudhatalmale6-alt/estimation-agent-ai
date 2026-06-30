"""
Drafts Microsoft Teams meeting invites for NFR discovery sessions.
Uses Microsoft Graph API to create calendar events or generates
.ics files for manual sending.

Requires Azure AD app registration with Calendars.ReadWrite permission
for auto-create, or no permissions for .ics file generation.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class MeetingScheduler:
    def __init__(self, client_id=None, client_secret=None, tenant_id=None,
                 refresh_token=None):
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.refresh_token = refresh_token or os.getenv("AZURE_REFRESH_TOKEN")
        self.access_token = None

    def authenticate(self):
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://graph.microsoft.com/.default"
        }
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        return self.access_token

    def _headers(self):
        if not self.access_token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def draft_meeting(self, project_name, pet_ticket_id, pm_name, pm_email,
                      perf_manager_email, estimation_summary,
                      proposed_date=None, duration_minutes=60,
                      additional_attendees=None):

        if proposed_date is None:
            now = datetime.now(timezone.utc)
            next_business = now + timedelta(days=1)
            while next_business.weekday() >= 5:
                next_business += timedelta(days=1)
            proposed_date = next_business.replace(hour=14, minute=0, second=0, microsecond=0)

        end_time = proposed_date + timedelta(minutes=duration_minutes)

        attendees = [
            {"emailAddress": {"address": pm_email, "name": pm_name}, "type": "required"},
            {"emailAddress": {"address": perf_manager_email, "name": "Performance Manager"}, "type": "required"}
        ]
        if additional_attendees:
            for att in additional_attendees:
                attendees.append({
                    "emailAddress": {"address": att["email"], "name": att.get("name", "")},
                    "type": "optional"
                })

        body_content = self._build_meeting_body(
            project_name, pet_ticket_id, pm_name, estimation_summary
        )

        event = {
            "subject": f"NFR Discovery - {project_name} ({pet_ticket_id})",
            "body": {
                "contentType": "HTML",
                "content": body_content
            },
            "start": {
                "dateTime": proposed_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC"
            },
            "location": {
                "displayName": "Microsoft Teams Meeting"
            },
            "attendees": attendees,
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
            "allowNewTimeProposals": True,
            "reminderMinutesBeforeStart": 15
        }

        return event

    def _build_meeting_body(self, project_name, pet_ticket_id, pm_name, estimation_summary):
        return f"""
<html>
<body>
<h2>NFR Discovery Session - {project_name}</h2>

<p>Hi {pm_name},</p>

<p>The performance team has completed a preliminary estimation for <b>{pet_ticket_id}</b> based on the attached HLD document. We'd like to schedule an NFR discovery session to walk through the design and gather non-functional requirements.</p>

<h3>Preliminary Estimation Summary</h3>
<pre>{estimation_summary}</pre>

<h3>Meeting Agenda</h3>
<ol>
<li><b>Project Overview</b> (5 min) - Brief project context and timeline</li>
<li><b>HLD Walkthrough</b> (20 min) - Architecture, components, integrations</li>
<li><b>NFR Discovery</b> (25 min) - Performance targets, workload profile, SLAs</li>
<li><b>Environment & Data</b> (5 min) - Test environment and data requirements</li>
<li><b>Next Steps</b> (5 min) - Action items and timeline</li>
</ol>

<h3>What to Prepare</h3>
<ul>
<li>Architecture diagram (if not in HLD)</li>
<li>Expected user volumes (normal and peak)</li>
<li>Response time targets and SLAs</li>
<li>Known performance concerns from previous releases</li>
<li>Test environment availability</li>
</ul>

<p><b>Please enable meeting transcription</b> so the performance team can capture NFR details accurately.</p>

<p>PET Ticket: {pet_ticket_id}<br>
Estimation Report: See attached or comment on the PET ticket</p>

<p>Thanks,<br>Performance Engineering Team</p>
</body>
</html>
"""

    def create_event_via_graph(self, event):
        url = f"{GRAPH_BASE}/me/events"
        response = requests.post(url, headers=self._headers(), json=event)
        response.raise_for_status()
        return response.json()

    def generate_ics_file(self, event, output_path):
        start = event["start"]["dateTime"].replace("-", "").replace(":", "").replace("T", "T")
        end = event["end"]["dateTime"].replace("-", "").replace(":", "").replace("T", "T")

        attendee_lines = []
        for att in event.get("attendees", []):
            email = att["emailAddress"]["address"]
            name = att["emailAddress"].get("name", email)
            role = "REQ-PARTICIPANT" if att["type"] == "required" else "OPT-PARTICIPANT"
            attendee_lines.append(f"ATTENDEE;ROLE={role};CN={name}:mailto:{email}")

        import re
        description = re.sub(r"<[^>]+>", "", event["body"]["content"])
        description = description.strip().replace("\n", "\\n")[:500]

        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Performance Engineering//Estimation Agent//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
DTSTART:{start}Z
DTEND:{end}Z
SUMMARY:{event['subject']}
DESCRIPTION:{description}
LOCATION:Microsoft Teams Meeting
{chr(10).join(attendee_lines)}
STATUS:TENTATIVE
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

        with open(output_path, "w") as f:
            f.write(ics_content)

        return output_path

    def draft_and_save(self, project_name, pet_ticket_id, pm_name, pm_email,
                       perf_manager_email, estimation_summary, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)

        event = self.draft_meeting(
            project_name=project_name,
            pet_ticket_id=pet_ticket_id,
            pm_name=pm_name,
            pm_email=pm_email,
            perf_manager_email=perf_manager_email,
            estimation_summary=estimation_summary
        )

        event_json_path = os.path.join(output_dir, f"meeting_draft_{pet_ticket_id}.json")
        with open(event_json_path, "w") as f:
            json.dump(event, f, indent=2)

        ics_path = os.path.join(output_dir, f"NFR_Discovery_{pet_ticket_id}.ics")
        self.generate_ics_file(event, ics_path)

        html_path = os.path.join(output_dir, f"meeting_invite_{pet_ticket_id}.html")
        with open(html_path, "w") as f:
            f.write(event["body"]["content"])

        return {
            "event_json": event_json_path,
            "ics_file": ics_path,
            "html_body": html_path,
            "subject": event["subject"],
            "proposed_time": event["start"]["dateTime"],
            "attendees": [a["emailAddress"]["address"] for a in event["attendees"]]
        }
