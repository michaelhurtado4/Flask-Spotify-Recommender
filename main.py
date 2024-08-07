from datetime import datetime
from dotenv import load_dotenv
import os
import requests
import urllib.parse
import redis 
import subprocess

from flask import Flask, redirect, request, jsonify, session

load_dotenv()

client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
REDIS_URL = os.getenv('redis_url')
redis_client = redis.StrictRedis.from_url(REDIS_URL)
app = Flask(__name__)

app.secret_key = os.getenv("secret_key")
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = 'https://api.spotify.com/v1/'
REDIRECT_URI = os.getenv('redirect_uri')

@app.route('/')
def index():
    return "Welcome to my Spotify App <a href='/login'> Login With Spotify</a>"

@app.route('/login')
def login():
    scope = 'user-library-read playlist-read-private playlist-modify-public playlist-modify-private user-read-private user-read-email'

    parameters = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(parameters)}"

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': client_id,
            'client_secret': client_secret
        }

    response = requests.post(TOKEN_URL, data=req_body)
    token_info = response.json()

    redis_client.set('access_token', token_info['access_token'])
    redis_client.set('refresh_token', token_info['refresh_token'])
    redis_client.set('expires_at', datetime.now().timestamp() + token_info['expires_in'])
    redis_client.set('time', datetime.now().timestamp())
    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
    session['time'] = datetime.now().timestamp()
    print(token_info['access_token'])

    return redirect('/setrecplaylist')

@app.route('/setrecplaylist')
def set_rec_playlist():

    if 'access_token' not in session:
        return redirect('/login')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}",
        'Content-Type': 'application/json'
    }

    response = requests.get(API_BASE_URL + 'me/playlists?limit=50&offset=0', headers=headers)
    playlists = response.json()
    check = False
    for playlist in playlists['items']:
        if playlist['name'] == 'Songs to Try':
            check = True
            session['playlist'] = playlist['id']
            redis_client.set('playlist', playlist['id'])
    if (check == False): 
        response = requests.get(API_BASE_URL + 'me', headers=headers)
        user_details = response.json()
        user_id = user_details['id']
        data = {
            'name': 'Songs to Try',
            'description': 'Songs to check out and see if you like',
            'public': False
        }
        response = requests.post(API_BASE_URL + f'users/{user_id}/playlists', headers=headers, json=data)
        response_json = response.json()
        redis_client.set('playlist', response_json['id'])
        session['playlist'] = response_json['id']

    subprocess.Popen(["celery", "-A", "celery_config.celery_app", "beat", "--loglevel=info"], start_new_session=True)
    
    return jsonify(playlists)







