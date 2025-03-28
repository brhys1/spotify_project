from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import snowflake.connector
import os
import requests
import openpyxl
import pandas
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production


# Spotify API credentials
CLIENT_ID = '339311402add405fba5b4e61261b8f81'
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
SCOPE = 'user-read-private user-read-email playlist-read-private user-library-read playlist-read-collaborative'  # Adjust scopes as needed


def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE')
    )

def insert_song_into_snowflake(track_data):
    conn = get_snowflake_connection()
    
    cursor = conn.cursor()
    
    query = """
        INSERT INTO party_songs (
            id, name, artist, album, release_year, 
            danceability, energy, valence, tempo, loudness, 
            speechiness, instrumentalness, liveness, explicit, popularity, duration_ms, is_party_song
        ) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    cursor.execute(query, (
        track_data["id"], track_data["name"], track_data["artist"], track_data["album"], track_data["release_year"],
        track_data["danceability"], track_data["energy"], track_data["valence"], track_data["tempo"], track_data["loudness"],
        track_data["speechiness"], track_data["instrumentalness"], track_data["liveness"], track_data["explicit"], 
        track_data["popularity"], track_data["duration_ms"], track_data["is_party_song"]
    ))
    
    conn.commit()
    cursor.close()
    conn.close()


@app.route('/login')
def login():
    if 'access_token' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/')
def home():
    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    #write email, refresh, and username to firebase


    data = playlists_data()

    for datum in data:
        if datum[1] == 'P2P: Non-Party Songs':
            party = False
            process_playlist(datum[0], party)
        if datum[1] == 'P2P: Party Songs':
            party = True
            process_playlist(datum[0], party)

    return render_template('home.html', profile = profile_data())


@app.route('/spotify_redirect')
def spotify_redirect():
    #call firebase check if email exis
    #if exists: #if exists
    #pull refresh
    #get new access token

    # Construct query parameters for the authorization URL
    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "client_id": CLIENT_ID
    }
    # Encode query parameters and create full URL
    url_args = "&".join([f"{key}={urllib.parse.quote(val)}" for key, val in auth_query_parameters.items()])
    auth_url_full = f"{AUTH_URL}/?{url_args}"
    return redirect(auth_url_full)

@app.route('/callback')
def callback():
    # Get the authorization code from the callback
    code = request.args.get('code')
    if not code:
        return "Error: No code provided", 400

    # Prepare data for the token request
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # Request an access token
    response = requests.post(TOKEN_URL, data=token_data, headers=token_headers)
    response_data = response.json()

    if "access_token" not in response_data:
        return f"Error fetching token: {response_data}", 400

    # Save the access token in the session (or your preferred storage)
    session['access_token'] = response_data['access_token']
    session['refresh_token'] = response_data.get('refresh_token')
    return redirect(url_for('home'))
    

def profile_data():
    # Retrieve the access token from the session
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    # Set up the header with the token
    headers = {"Authorization": f"Bearer {access_token}"}

    # Make a GET request to the Spotify API
    profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if profile_response.status_code != 200:
        return f"Error: {profile_response.json()}", profile_response.status_code

    profile_data = profile_response.json()
    return profile_data  # This returns JSON data; for a real app, you might render a template

def playlists_data():
    # Retrieve the access token from the session
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))
    
    # Set up the authorization header with the access token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Make the GET request to the Spotify API for the user's playlists
    response = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
    
    # Check for a successful response
    if response.status_code != 200:
        return f"Error fetching playlists: {response.json()}", response.status_code
    
    # Parse the JSON data
    playlists_data = response.json()
    data = [[playlist["id"], playlist["name"]] for playlist in playlists_data["items"]]
    
    # Optionally, you can format this data or pass it to a template
    print(data)
    return data  # This will return a JSON response



def process_playlist(playlist_id, is_party_song):
    # Retrieve the access token from the session
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching playlist: {response.json()}")
        return

    tracks_data = response.json()["items"]
    
    for track_item in tracks_data:
        track = track_item["track"]
        track_id = track["id"]
        
        # Get track audio features
        features = get_track_features(track_id, access_token)
        if not features:
            continue  # Skip if unable to fetch features

        # Prepare song data
        song_data = {
            "id": track["id"],
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "release_year": int(track["album"]["release_date"].split("-")[0]),
            "explicit": track["explicit"],
            "popularity": track["popularity"],
            "duration_ms": track["duration_ms"],
            "is_party_song": is_party_song  # Label from playlist name
        }

        # Insert into Snowflake
        insert_song_into_snowflake(song_data)

def get_track_features(track_id, access_token):
    url = f"https://api.spotify.com/v1/audio-features/{track_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 403:
        print("❌ ERROR 403: Access Denied. Token may be missing required scopes.")
        return None
    elif response.status_code == 401:
        print("❌ ERROR 401: Token Expired. Try refreshing the token.")
        return None
    if response.status_code != 200:
        print(f"Error fetching track features: {response.json()}")
        return None

    return response.json()


def refresh_algorithm():
    pass
    #pull all the refresh tokens
    #get all the access tokens
    #rerun algorithm

# Set up the scheduler to run the daily_task every day at midnight
scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_algorithm, trigger="cron", hour=4, minute=0)
scheduler.start()

# Ensure the scheduler is shut down when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(debug=True)


