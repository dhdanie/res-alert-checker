import os.path
import base64
import json
import re
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging
import requests


class MailAuth:

    def read_emails(self, login_id):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file(
                "token.json", ["https://mail.google.com/"]
            )
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    # your creds file here. Please create json file as here https://cloud.google.com/docs/authentication/getting-started
                    "credentials.json",
                    ["https://mail.google.com/"],
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        try:
            # Call the Gmail API
            service = build("gmail", "v1", credentials=creds)
            messages = []
            for i in range(1, 6):
                results = (
                    service.users()
                    .messages()
                    .list(
                        userId="me",
                        labelIds=["INBOX"],
                        q=f'to:resfinderdisney+{login_id}@gmail.com is:unread subject:"Your one-time passcode for Walt Disney World" ',  # TODO: get rid of double checking for one email subject
                    )
                    .execute()
                )
                messages = results.get("messages", [])
                if len(messages) > 0:
                    break
                time.sleep(5)

            out = False
            for message in messages:
                if not out:
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message["id"])
                        .execute()
                    )
                    email_data = msg["payload"]["headers"]
                    subject = next(
                        (
                            val
                            for val in email_data
                            if val["value"]
                            == "Your one-time passcode for Walt Disney World"
                        ),
                        False,
                    )
                    if subject:
                        data = msg["payload"]["body"]["data"]
                        byte_code = base64.urlsafe_b64decode(data)

                        text = byte_code.decode("utf-8")
                        text = text[text.index('<span id="otp_code">') + 20 :]
                        text = text[:6]
                        if not out:
                            out = text
                service.users().messages().modify(
                    userId="me", id=message["id"], body={"removeLabelIds": ["UNREAD"]}
                ).execute()
            return out
        except Exception as error:
            print(f"An error occurred: {error}")
