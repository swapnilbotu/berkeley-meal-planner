"""One-time local OAuth PKCE authorization; write directly to GitHub encrypted secrets.

Run on a trusted computer with a browser and authenticated `gh`. No credentials
are printed or saved by this program. Use a Desktop OAuth client JSON downloaded
from your own no-billing Google project. The consent screen must be In production
to avoid Testing-mode seven-day refresh token expiry.
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import urllib.parse
import webbrowser

import requests

SCOPES = 'openid email https://www.googleapis.com/auth/tasks'
parser = argparse.ArgumentParser()
parser.add_argument('--client', required=True, type=Path)
parser.add_argument('--repo', required=True, help='OWNER/REPOSITORY')
args = parser.parse_args()
if not shutil.which('gh'):
    raise SystemExit('Install the free GitHub CLI and run gh auth login first.')
subprocess.run(['gh','auth','status'], check=True, capture_output=True)
client = json.loads(args.client.read_text()).get('installed')
if not client:
    raise SystemExit('A Google Desktop OAuth client JSON is required.')
if client.get('auth_uri') != 'https://accounts.google.com/o/oauth2/auth' or client.get('token_uri') != 'https://oauth2.googleapis.com/token':
    raise SystemExit('Unexpected OAuth provider URLs.')
state = secrets.token_urlsafe(32)
verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
received = {}


class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        if q.get('state', [''])[0] != state:
            self.send_error(400, 'Invalid OAuth state')
            return
        received.update(q)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Authorization received. Return to the terminal; you may close this tab.')

    def log_message(self, *args):
        pass  # The callback URL contains a short-lived authorization code.


server = HTTPServer(('127.0.0.1', 0), Callback)
server.timeout = 180
redirect = f'http://127.0.0.1:{server.server_port}/'
url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id':client['client_id'], 'redirect_uri':redirect, 'response_type':'code',
    'scope':SCOPES, 'access_type':'offline', 'prompt':'consent', 'state':state,
    'code_challenge':challenge, 'code_challenge_method':'S256', 'login_hint':'swapnilbotu@gmail.com'})
print('Opening Google consent in your browser. Authorize swapnilbotu@gmail.com.')
if not webbrowser.open(url):
    raise SystemExit('Could not open browser. Run this on a computer with a browser.')
server.handle_request()
server.server_close()
if 'code' not in received:
    raise SystemExit('No authorization code received. No secrets were changed.')
r = requests.post('https://oauth2.googleapis.com/token', data={
    'code':received['code'][0], 'client_id':client['client_id'], 'client_secret':client['client_secret'],
    'redirect_uri':redirect, 'grant_type':'authorization_code', 'code_verifier':verifier}, timeout=30)
if not r.ok:
    raise SystemExit('OAuth exchange failed; no token response was printed.')
tokens = r.json()
if not tokens.get('refresh_token'):
    raise SystemExit('No refresh token received. Revoke the app grant and authorize again.')
profile = requests.get('https://openidconnect.googleapis.com/v1/userinfo',
                       headers={'Authorization':'Bearer '+tokens['access_token']}, timeout=30)
if not profile.ok or profile.json().get('email') != 'swapnilbotu@gmail.com' or not profile.json().get('email_verified'):
    raise SystemExit('Wrong Google account; no GitHub secrets were changed.')
for name, value in [('GOOGLE_CLIENT_ID', client['client_id']), ('GOOGLE_CLIENT_SECRET', client['client_secret']),
                    ('GOOGLE_REFRESH_TOKEN', tokens['refresh_token'])]:
    subprocess.run(['gh','secret','set',name,'--repo',args.repo], input=value, text=True,
                   check=True, capture_output=True)
print('Three encrypted GitHub Actions secrets configured. No credentials were printed or committed.')
