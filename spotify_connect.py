from flask import Flask, redirect, request, session, url_for, render_template
import os
import requests
import openpyxl
import pandas
import urllib.parse

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production

# Spotify API credentials
CLIENT_ID = '339311402add405fba5b4e61261b8f81'
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
SCOPE = 'user-read-private user-read-email playlist-read-private'  # Adjust scopes as needed

@app.route('/login')
def login():
    if 'access_token' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/')
def home():
    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    

    return render_template('home.html', profile = profile_data())


@app.route('/spotify_redirect')
def spotify_redirect():
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
    playlist_names = [playlist["name"] for playlist in playlists_data["items"]]
    
    # Optionally, you can format this data or pass it to a template
    print(playlist_names)

    return playlists_data  # This will return a JSON response

def playlist_data(playlist_id):
    # Retrieve the access token from the session
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    # Set up the authorization header with the access token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Construct the endpoint URL using the playlist ID
    playlist_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    
    # Make the GET request to fetch the playlist data
    response = requests.get(playlist_url, headers=headers)
    
    if response.status_code != 200:
        return f"Error fetching playlist: {response.json()}", response.status_code
    
    # Parse the JSON data from the response
    playlist_data = response.json()
    
    # Optionally, you can render this data in a template instead of returning JSON
    return playlist_data


if __name__ == "__main__":
    app.run(debug=True)


