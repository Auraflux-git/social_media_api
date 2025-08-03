from fastapi import FastAPI, Query , HTTPException
from fastapi.responses import JSONResponse , StreamingResponse
from yt_dlp import YoutubeDL
from typing import Dict
from urllib.parse import unquote , quote
import httpx
import re , uuid

app = FastAPI(title="Social Media Downloader API")
short_links = {}
# Shortened for brevity — use your full dict here
@app.get("/")
def root():
    return {"message": "Auraflux API is live"}
supported_platforms = {
    "YouTube": {
        "urls": [
            "https://www.youtube.com",
            "https://youtube.com",
            "https://youtu.be",
            "https://m.youtube.com",
            "https://music.youtube.com"
        ]
    },
    "Instagram": {
        "urls": [
            "https://www.instagram.com",
            "https://instagram.com",
            "https://www.instagram.com/reel",
            "https://www.instagram.com/stories"
        ]
    },
    "Facebook": {
        "urls": [
            "https://www.facebook.com",
            "https://facebook.com",
            "https://fb.watch",
            "https://m.facebook.com"
        ]
    },
    "Twitter (X)": {
        "urls": [
            "https://twitter.com",
            "https://x.com",
            "https://mobile.twitter.com",
            "https://fxtwitter.com"
        ]
    },
    "TikTok": {
        "urls": [
            "https://www.tiktok.com",
            "https://tiktok.com",
            "https://vm.tiktok.com"
        ]
    },
    "Vimeo": {
        "urls": [
            "https://vimeo.com",
            "https://www.vimeo.com",
            "https://player.vimeo.com"
        ]
    },
    "SoundCloud": {
        "urls": [
            "https://soundcloud.com",
            "https://m.soundcloud.com"
        ]
    },
    "Bandcamp": {
        "urls": [
            "https://bandcamp.com",
            "https://*.bandcamp.com"
        ]
    },
    "Twitch": {
        "urls": [
            "https://www.twitch.tv",
            "https://twitch.tv",
            "https://clips.twitch.tv"
        ]
    },
    "Dailymotion": {
        "urls": [
            "https://www.dailymotion.com",
            "https://dailymotion.com"
        ]
    },
    "Mixcloud": {
        "urls": [
            "https://www.mixcloud.com",
            "https://mixcloud.com"
        ]
    },
    "Audiomack": {
        "urls": [
            "https://audiomack.com",
            "https://www.audiomack.com"
        ]
    },
    "Rumble": {
        "urls": [
            "https://rumble.com",
            "https://www.rumble.com"
        ]
    },
    "Odysee": {
        "urls": [
            "https://odysee.com",
            "https://www.odysee.com"
        ]
    },
    "Bilibili": {
        "urls": [
            "https://www.bilibili.com",
            "https://bilibili.com",
            "https://m.bilibili.com"
        ]
    },
    "Streamable": {
        "urls": [
            "https://streamable.com",
            "https://www.streamable.com"
        ]
    },
    "TED": {
        "urls": [
            "https://www.ted.com",
            "https://ted.com"
        ]
    }
}


@app.get("/supported")
async def get_supported():
    return supported_platforms

def extract_info(url: str) -> Dict:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'forcejson': True,
        'no_cookies_from_browser': True,
        'no_cookies': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/116.0.5845.188 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            title = info.get("title", "")
            thumbnail = info.get("thumbnail")
            formats = info.get("formats", [])

            seen_video = set()
            seen_audio = set()
            seen_progressive = set()

            video_formats = []
            audio_formats = []
            progressive_formats = []

            for f in formats:
                ext = f.get("ext")
                height = f.get("height")
                abr = f.get("abr")
                url = f.get("url")
                acodec = f.get("acodec")
                vcodec = f.get("vcodec")
                format_id = f.get("format_id")

                # Progressive = has both video + audio
                if vcodec != "none" and acodec != "none":
                    key = (height, ext)
                    if key not in seen_progressive:
                        seen_progressive.add(key)
                        filename = f"{title.replace(' ', '_')}_{height}p.{ext}"
                        code = uuid.uuid4().hex[:6]
                        short_links[code] = {"url": url, "filename": filename}
                        progressive_formats.append({
                            "format_id": format_id,
                            "ext": ext,
                            "height": height,
                            "original_url": url,
                            "download_url": f"http://localhost:8000/d/{code}"
                        })

                # Video-only
                elif vcodec != "none" and acodec == "none":
                    key = (height, ext)
                    if key not in seen_video:
                        seen_video.add(key)
                        filename = f"{title.replace(' ', '_')}_{height}p_video.{ext}"
                        code = uuid.uuid4().hex[:6]
                        short_links[code] = {"url": url, "filename": filename}
                        video_formats.append({
                            "format_id": format_id,
                            "ext": ext,
                            "height": height,
                            "original_url": url,
                            "download_url": f"http://localhost:8000/d/{code}",
                            "suggestion": "This is a video-only format. It has no audio. To get sound, download the matching audio and merge using FFmpeg or use the 'Merged Download' option if available."
                        })

                # Audio-only
                elif vcodec == "none" and acodec != "none":
                    key = (abr, ext)
                    if key not in seen_audio:
                        seen_audio.add(key)
                        filename = f"{title.replace(' ', '_')}_{abr}kbps_audio.{ext}"
                        code = uuid.uuid4().hex[:6]
                        short_links[code] = {"url": url, "filename": filename}
                        audio_formats.append({
                            "format_id": format_id,
                            "ext": ext,
                            "abr": abr,
                            "original_url": url,
                            "download_url": f"http://localhost:8000/d/{code}"
                        })

            return {
                "success": True,
                "title": title,
                "thumbnail": thumbnail,
                "progressive_formats": sorted(progressive_formats, key=lambda x: x["height"] or 0, reverse=True),
                "video_formats": sorted(video_formats, key=lambda x: x["height"] or 0, reverse=True),
                "audio_formats": sorted(audio_formats, key=lambda x: x["abr"] or 0, reverse=True)
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
    
@app.get("/d/{code}")
async def short_link_redirect(code: str):
    if code not in short_links:
        return JSONResponse({"success": False, "error": "Invalid or expired short code"}, status_code=404)

    item = short_links[code]
    url = item["url"]
    filename = item["filename"]

    try:
        decoded_url = unquote(url)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(decoded_url, follow_redirects=True)

        content_type = response.headers.get("content-type", "application/octet-stream")
        return StreamingResponse(
            iter([response.content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "Content-Length": str(len(response.content))
            }
        )
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    
# Create dynamic endpoints like /youtube, /instagram
def make_route(platform: str):
    @app.get(f"/{platform}")
    async def handle_media_request(url: str = Query(...)):
        result = extract_info(url)
        return JSONResponse(result)
    
for name in supported_platforms:
    route_name = re.sub(r"[^\w]", "", name).lower()
    make_route(route_name)
