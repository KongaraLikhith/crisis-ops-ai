import os
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()
creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
scopes = ['https://www.googleapis.com/auth/drive.readonly']

try:
    creds = service_account.Credentials.from_service_account_file(creds_file, scopes=scopes)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # List folders visible to the SA
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name)"
    ).execute()
    folders = results.get('files', [])
    
    print("\nVisible Folders:")
    for f in folders:
        print(f" - {f['name']} ({f['id']})")
        
except Exception as e:
    print(f"GDrive Fail: {e}")
