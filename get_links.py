from dataclasses import dataclass
import requests
import os
from dotenv import load_dotenv


@dataclass
class MusicLinksResponse():
    spotify_url: str
    apple_music_url: str | None
    deezer_url: str | None
    tidal_url: str | None
    image_url: str
    album_name: str
    artist_name: str


def get_releases(
        spotify_url: str,
        musiclink_key: str,
    ) -> MusicLinksResponse:
    api_url = 'https://albumsweekly.com/links/get_links'
    params = {
        'spotifyUrl': spotify_url,
    }
    headers = {
        'Authorization': f'Bearer {musiclink_key}'
    }
    response = requests.get(api_url, params=params, headers=headers)
    if response.status_code != 200:
        raise ValueError(
            f"API request failed with status code {response.status_code}: "
            f"{response.text}"
        )
    data = response.json()

    return MusicLinksResponse(
        spotify_url=data.get('spotify_url'),
        apple_music_url=data.get('apple_music_url'),
        deezer_url=data.get('deezer_url'),
        tidal_url=data.get('tidal_url'),
        image_url=data.get('image_url'),
        album_name=data.get('album_name'),
        artist_name=data.get('artist_name')
    )
