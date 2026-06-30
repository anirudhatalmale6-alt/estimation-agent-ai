"""
Monitors Outlook inbox via Microsoft Graph API for PET ticket creation
notification emails. When a new PET email is detected, extracts the ticket ID
and triggers the estimation workflow.

Requires Azure AD app registration with Mail.Read permission.
"""

import os
import re
import json
import time
import requests


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OutlookEmailTrigger:
    def __init__(self, client_id=None, client_secret=None, tenant_id=None,
                 user_email=None, refresh_token=None):
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.user_email = user_email or os.getenv("PERF_MANAGER_EMAIL")
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
        if "refresh_token" in data:
            self.refresh_token = data["refresh_token"]
        return self.access_token

    def _headers(self):
        if not self.access_token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def check_for_pet_emails(self, since_minutes=60, mark_read=True):
        from datetime import datetime, timedelta, timezone
        since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        filter_query = (
            f"isRead eq false and "
            f"receivedDateTime ge {since_str} and "
            f"(contains(subject, 'PET') or contains(subject, 'Performance Estimation'))"
        )

        url = f"{GRAPH_BASE}/me/messages"
        params = {
            "$filter": filter_query,
            "$select": "id,subject,from,receivedDateTime,body,bodyPreview",
            "$orderby": "receivedDateTime desc",
            "$top": 20
        }

        response = requests.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        messages = response.json().get("value", [])

        pet_notifications = []
        for msg in messages:
            pet_id = self._extract_pet_id(msg)
            if pet_id:
                pet_notifications.append({
                    "email_id": msg["id"],
                    "pet_ticket_id": pet_id,
                    "subject": msg.get("subject", ""),
                    "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                    "received": msg.get("receivedDateTime", ""),
                    "preview": msg.get("bodyPreview", "")[:200]
                })
                if mark_read:
                    self._mark_as_read(msg["id"])

        return pet_notifications

    def _extract_pet_id(self, message):
        text = (
            message.get("subject", "") + " " +
            message.get("bodyPreview", "") + " " +
            message.get("body", {}).get("content", "")
        )
        patterns = [
            r"(PET-\d+)",
            r"(PET_\d+)",
            r"requestcentral[^\s]*/(PET-?\d+)",
            r"Performance\s+Estimation\s+Ticket[:\s]+(PET-?\d+)",
            r"ticket[:\s]+(PET-?\d+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ticket_id = match.group(1).upper()
                if not ticket_id.startswith("PET-"):
                    ticket_id = "PET-" + ticket_id.replace("PET", "").replace("_", "").replace("-", "")
                return ticket_id
        return None

    def _mark_as_read(self, message_id):
        url = f"{GRAPH_BASE}/me/messages/{message_id}"
        requests.patch(url, headers=self._headers(), json={"isRead": True})

    def get_email_details(self, message_id):
        url = f"{GRAPH_BASE}/me/messages/{message_id}"
        params = {"$select": "id,subject,from,toRecipients,body,receivedDateTime,hasAttachments"}
        response = requests.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    def poll(self, interval_seconds=300, callback=None):
        print(f"Polling inbox every {interval_seconds}s for PET notification emails...")
        while True:
            try:
                notifications = self.check_for_pet_emails(since_minutes=interval_seconds // 60 + 5)
                for notif in notifications:
                    print(f"  Found: {notif['pet_ticket_id']} - {notif['subject']}")
                    if callback:
                        callback(notif)
            except Exception as e:
                print(f"  Poll error: {e}")
            time.sleep(interval_seconds)
