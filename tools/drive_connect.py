"""One-time private Drive OAuth setup. No third-party dependencies."""
import base64
import datetime as dt
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = Path.home() / '.config/hermes-drive'
SCOPE = 'https://www.googleapis.com/auth/drive.file'
REDIRECT = 'http://localhost:1'
TOKEN_URI = 'https://oauth2.googleapis.com/token'

def save(name, data):
    path = BASE / name
    temporary = BASE / (name + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    os.replace(temporary, path)

def read(name):
    return json.loads((BASE / name).read_text())

def request(url, data=None, token=None):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    encoded = urllib.parse.urlencode(data).encode() if data is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=encoded, headers=headers), timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit('Google request failed, HTTP ' + str(exc.code) + '; response omitted to protect credentials.') from None
    except urllib.error.URLError:
        raise SystemExit('Google connection failed; credentials were not printed.') from None

def token_payload(response, client, previous=None):
    scopes = response.get('scope', SCOPE).split()
    if scopes != [SCOPE]:
        raise SystemExit('Unexpected granted scopes; refusing to save token.')
    refresh = response.get('refresh_token') or (previous or {}).get('refresh_token')
    if not refresh:
        raise SystemExit('No refresh token returned; persistent connection is not ready.')
    return dict(type='authorized_user', token=response['access_token'], refresh_token=refresh,
                token_uri=TOKEN_URI, client_id=client['client_id'], client_secret=client['client_secret'],
                scopes=[SCOPE], expiry=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=response['expires_in'])).strftime('%Y-%m-%dT%H:%M:%SZ'))

def metadata(token, ids):
    result=[]
    for file_id in ids:
        query=urllib.parse.urlencode({'fields':'id,name,mimeType,parents,capabilities(canAddChildren)'})
        item=request('https://www.googleapis.com/drive/v3/files/'+urllib.parse.quote(file_id,safe='')+'?'+query, token=token)
        if item['mimeType'] != 'application/vnd.google-apps.folder':
            raise SystemExit('Selected item is not a folder.')
        result.append(item)
    return result

def main():
    os.umask(0o077)
    BASE.mkdir(parents=True,exist_ok=True)
    BASE.chmod(0o700)
    client=read('client_secret.json')['installed']
    action=sys.argv[1]
    if action in ('start', 'start-basic'):
        if (BASE/'token.json').exists():
            raise SystemExit('Token already exists; refusing to replace existing authorization.')
        verifier=secrets.token_urlsafe(64)
        state=secrets.token_urlsafe(32)
        save('pending.json',dict(state=state,verifier=verifier,redirect_uri=REDIRECT,picker=(action=='start')))
        query=dict(client_id=client['client_id'],redirect_uri=REDIRECT,response_type='code',scope=SCOPE,
                   access_type='offline',prompt='consent',include_granted_scopes='false',state=state,
                   code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='),
                   code_challenge_method='S256')
        if action=='start':
            query.update(trigger_onepick='true',allow_multiple='true',allow_folder_selection='true')
        url='https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode(query)
        (BASE/'authorization-url.txt').write_text(url+'\n')
        print(url)
    elif action=='finish':
        pending=read('pending.json')
        callback=getpass.getpass('Paste the full localhost redirect URL (hidden): ')
        parsed=urllib.parse.urlparse(callback.strip())
        if parsed.scheme!='http' or parsed.hostname!='localhost' or parsed.port!=1:
            raise SystemExit('Unexpected callback address.')
        query=urllib.parse.parse_qs(parsed.query)
        if not secrets.compare_digest(query.get('state',[''])[0],pending['state']):
            raise SystemExit('OAuth state mismatch.')
        if query.get('error') or not query.get('code'):
            raise SystemExit('Authorization was cancelled or code is missing.')
        selected=list(dict.fromkeys(x for x in query.get('picked_file_ids',[''])[0].split(',') if x))
        if pending.get('picker',True) and not selected:
            raise SystemExit('No explicitly selected folders returned.')
        response=request(TOKEN_URI,dict(client_id=client['client_id'],client_secret=client['client_secret'],
                         code=query['code'][0],code_verifier=pending['verifier'],redirect_uri=REDIRECT,grant_type='authorization_code'))
        payload=token_payload(response,client)
        save('token.json',payload)
        save('selected-folders.json',dict(ids=selected))
        (BASE/'pending.json').unlink()
        print('TOKEN_SAVED_PRIVATE; scope=drive.file; refresh_token=present')
        folders=metadata(payload['token'],selected)
        save('selected-folders.json',dict(ids=selected,folders=folders))
        print(json.dumps(folders,ensure_ascii=False,indent=2))
        if not selected:
            print('AUTHORIZATION_READY; folder access still needs validation.')
    elif action=='check':
        previous=read('token.json')
        response=request(TOKEN_URI,dict(client_id=client['client_id'],client_secret=client['client_secret'],
                         refresh_token=previous['refresh_token'],grant_type='refresh_token'))
        payload=token_payload(response,client,previous)
        save('token.json',payload)
        print('REFRESH_OK; scope=drive.file')
        print(json.dumps(metadata(payload['token'],read('selected-folders.json')['ids']),ensure_ascii=False,indent=2))
    else:
        raise SystemExit('Use start, start-basic, finish or check.')

if __name__=='__main__':
    main()
