import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
TOKEN_FILE = "src/token.pickle"  

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify"
]

def create_token():
    flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_APPLICATION_CREDENTIALS, SCOPES)
    creds = flow.run_local_server(port=0) 
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    print(f"Token berhasil dibuat: {TOKEN_FILE}")

if __name__ == "__main__":
    create_token()
