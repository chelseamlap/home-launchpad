"""Google Sheets integration for the Money tab budget data.

Uses a Google Service Account for authentication, scoped to only the
sheets shared with it. Each user creates their own service account,
shares a specific Drive folder with it, and puts their budget sheet there.

SETUP:
1. Go to https://console.cloud.google.com/
2. Create or select your project
3. Enable the Google Sheets API
4. Go to IAM & Admin > Service Accounts > Create Service Account
5. Download the JSON key file
6. Save it as data/google_service_account.json
7. In Google Drive, create a folder for your dashboard sheets
8. Share that folder with the service account email
   (the email looks like: name@project-id.iam.gserviceaccount.com)
9. Put your budget spreadsheet in that folder
"""
import logging
import os
from datetime import datetime, timedelta

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "data", "google_service_account.json")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def is_sheets_connected():
    """Check if a service account key file exists."""
    return os.path.exists(SERVICE_ACCOUNT_FILE)


def _get_service():
    """Build the Sheets API service using service account credentials."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.warning("No service account key at %s", SERVICE_ACCOUNT_FILE)
        return None
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build("sheets", "v4", credentials=creds)
    except Exception as e:
        logger.error("Failed to build Sheets service: %s", e)
        return None


def get_budget_data(sheet_id):
    """
    Read budget data from the Google Sheet.

    Expected Sheet Format:
    Sheet 1: "Budget"
      Row 1: Headers — Category | Budget | Spent
      Row 2+: Data rows
      Example:
        Groceries    | 800  | 523.45
        Dining       | 400  | 287.00
        Home         | 300  | 150.00
        Kids         | 200  | 89.50
        Subscriptions| 150  | 149.99
        Misc         | 200  | 45.00

    Sheet 2: "Bills"
      Row 1: Headers — Bill Name | Amount | Due Date
      Row 2+: Data rows
      Example:
        Mortgage     | 2400  | 2026-04-15
        Electric     | 185   | 2026-04-10
        Internet     | 75    | 2026-04-12
    """
    if not sheet_id:
        return _sample_data()

    service = _get_service()
    if not service:
        return _sample_data()

    try:
        # Read budget categories
        budget_result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="Budget!A2:C20",
        ).execute()
        budget_rows = budget_result.get("values", [])

        categories = []
        for row in budget_rows:
            if len(row) >= 3:
                categories.append({
                    "name": row[0],
                    "budget": float(row[1].replace(",", "").replace("$", "")),
                    "spent": float(row[2].replace(",", "").replace("$", "")),
                })

        # Read bills
        bills_result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="Bills!A2:C50",
        ).execute()
        bills_rows = bills_result.get("values", [])

        bills = []
        now = datetime.now()
        week_end = now + timedelta(days=7)

        for row in bills_rows:
            if len(row) >= 3:
                try:
                    due = datetime.strptime(row[2].strip(), "%Y-%m-%d")
                    if now.date() <= due.date() <= week_end.date():
                        days_until = (due.date() - now.date()).days
                        bills.append({
                            "name": row[0],
                            "amount": float(row[1].replace(",", "").replace("$", "")),
                            "due_date": row[2],
                            "due_display": due.strftime("%a %b %-d"),
                            "days_until": days_until,
                        })
                except (ValueError, IndexError):
                    continue

        return {"categories": categories, "bills": bills, "source": "google_sheets"}

    except Exception as e:
        logger.error(f"Sheets fetch failed: {e}")
        return _sample_data()


def _sample_data():
    """Return sample/placeholder data when Sheets isn't connected."""
    return {
        "categories": [
            {"name": "Groceries", "budget": 800, "spent": 0},
            {"name": "Dining", "budget": 400, "spent": 0},
            {"name": "Home", "budget": 300, "spent": 0},
            {"name": "Kids", "budget": 200, "spent": 0},
            {"name": "Subscriptions", "budget": 150, "spent": 0},
            {"name": "Misc", "budget": 200, "spent": 0},
        ],
        "bills": [],
        "source": "sample",
    }
