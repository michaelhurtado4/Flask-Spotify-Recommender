from datetime import datetime
import requests
import time 
import os
import urllib.parse

from flask import Flask, redirect, request, jsonify, session

app = Flask(__name__)
app.secret_key = '123RANdomKeyINeed675'
TIME = datetime.now().timestamp()
client_id = os.getenv('client_id)
client_secret = os.getenv('client_secret')
PLAYLIST = ''
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = 'https://api.spotify.com/v1/'
REDIRECT_URI = 'http://localhost:5000/callback'

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
        'show_dialog': False
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

    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

    return redirect('/setrecplaylist')

@app.route('/setrecplaylist')
def set_rec_playlist():

    global PLAYLIST

    if 'access_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    
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
            PLAYLIST = playlist['id']
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
        PLAYLIST = response_json['id']
    
    return redirect('/likedsongs')

@app.route('/likedsongs')
def get_likedsongs():

    global TIME
    global PLAYLIST

    if 'access_token' not in session:
        return redirect('/login')


    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}",
        'Content-Type': 'application/json' 
    }

    response = requests.get(API_BASE_URL + 'me/tracks?limit=50&offset=0', headers=headers)
    likedsongs= response.json()

    songs_to_add = []
    for song in likedsongs['items']:
        song_time = datetime.strptime(song['added_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
        if (song_time > TIME):
            print(song['track']['name'])
            response = requests.get(API_BASE_URL + f"recommendations?limit=3&seed_tracks={song['track']['id']}&min_popularity=70", headers=headers)
            recommendedsongs = response.json()
            for rec_song in recommendedsongs['tracks']:
                songs_to_add.append(rec_song['uri'])
    print(songs_to_add)
    data = {
        'uris': songs_to_add,
        'position': 0
    }      
    response = requests.post(API_BASE_URL + f'playlists/{PLAYLIST}/tracks', headers=headers, json=data)
    TIME = datetime.strptime(likedsongs['items'][0]['added_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
    time.sleep(30)
    return redirect('/likedsongs')


@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()
        
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/setrecplaylist')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))






