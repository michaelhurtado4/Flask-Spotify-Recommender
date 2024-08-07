from celery_config import celery_app
import redis 
from celery.schedules import crontab
import requests 
from datetime import datetime 
import os 
REDIS_URL = os.getenv('redis_url')
API_BASE_URL = 'https://api.spotify.com/v1/'
TOKEN_URL = "https://accounts.spotify.com/api/token"
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
redis_client = redis.StrictRedis.from_url(REDIS_URL)


@celery_app.task(name='tasks.refresh_token')
def refresh_token():
    refresh_token = redis_client.get('refresh_token').decode('utf-8')
    req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }
    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()    
    redis_client.set('access_token', new_token_info['access_token']) 
    redis_client.set('expires_at', datetime.now().timestamp() + new_token_info['expires_in'])

@celery_app.task(name='tasks.get_likedsongs')
def get_likedsongs():
    
    expires_at = float(redis_client.get('expires_at'))

    if datetime.now().timestamp() > expires_at:
        refresh_token()

    access_token = redis_client.get('access_token').decode('utf-8')

    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json' 
    }
    response = requests.get(API_BASE_URL + 'me/tracks?limit=50&offset=0', headers=headers)
    print(f"Response Status Code getting Tracks: {response.status_code}")
    likedsongs= response.json()

    songs_to_add = []
    for song in likedsongs['items']:
        song_time = datetime.strptime(song['added_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
        if (song_time > float(redis_client.get('time'))):
            response = requests.get(API_BASE_URL + f"recommendations?limit=3&seed_tracks={song['track']['id']}&min_popularity=70", headers=headers)
            print(f"Response Status Code getting Recommendations: {response.status_code}")
            recommendedsongs = response.json()
            for rec_song in recommendedsongs['tracks']:
                songs_to_add.append(rec_song['uri'])
    data = {
        'uris': songs_to_add,
        'position': 0
    }     
    playlist_id = redis_client.get('playlist').decode('utf-8')
    response = requests.post(API_BASE_URL + f"playlists/{playlist_id}/tracks", headers=headers, json=data)
    print(f"Response Status Code updating playlist: {response.status_code}")
    print(f"Response Content: {response.text}")
    redis_client.set('time', datetime.strptime(likedsongs['items'][0]['added_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp())


