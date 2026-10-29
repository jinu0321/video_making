# /// script
# requires-python = ">=3.10"
# dependencies = ["google-api-python-client", "google-auth-oauthlib"]
# ///
"""Upload a finished Shorts folder to YouTube as a public video (or scheduled with --publish-at).

  uv run .claude/skills/upload/scripts/upload.py <폴더> [--publish-at 2026-10-30T18:00:00+09:00]

Reads <폴더>/youtube.json (title, description, tags), uploads output/*.mp4, tries
output/thumbnail.png as the custom thumbnail, then writes videoId/url back into youtube.json.
The OAuth client and saved token live in ~/.config/youtube-upload/.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

CONF = Path.home() / ".config" / "youtube-upload"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY = "27"  # Education


def credentials():
    token = CONF / "token.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:  # revoked, or the 7-day expiry of an OAuth app left in Testing
            creds = None
    if not creds or not creds.valid:
        secret = CONF / "client_secret.json"
        if not secret.exists():
            raise SystemExit(f"missing {secret} (see SKILL.md '처음 한 번')")
        creds = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0)
    token.write_text(creds.to_json())
    token.chmod(0o600)
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--publish-at", help="RFC 3339 time; the video stays private and YouTube publishes it then")
    args = ap.parse_args()

    meta_path = args.folder / "youtube.json"
    meta = json.loads(meta_path.read_text())
    if meta.get("videoId"):
        raise SystemExit(f"already uploaded: {meta['url']}")
    videos = list((args.folder / "output").glob("*.mp4"))
    if len(videos) != 1:
        raise SystemExit(f"expected one MP4 in output/, found {len(videos)}")
    title, desc = meta["title"], meta["description"]
    if len(title) > 100 or any(c in title + desc for c in "<>"):
        raise SystemExit("title must be 100 chars or less, and title/description must not contain < or >")

    status = {"privacyStatus": "private" if args.publish_at else "public", "selfDeclaredMadeForKids": False}
    if args.publish_at:
        status["publishAt"] = args.publish_at
    body = {
        "snippet": {"title": title, "description": desc, "tags": meta.get("tags", []),
                    "categoryId": CATEGORY, "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
        "status": status,
    }

    yt = build("youtube", "v3", credentials=credentials())
    media = MediaFileUpload(str(videos[0]), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        progress, resp = req.next_chunk(num_retries=3)
        if progress:
            print(f"uploading {progress.progress():.0%}")

    vid = resp["id"]
    # saved before the thumbnail step so a rerun can't upload the same video twice
    meta.update(videoId=vid, url=f"https://youtube.com/shorts/{vid}",
                privacy=resp["status"]["privacyStatus"], publishAt=args.publish_at,
                uploadedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"uploaded: {meta['url']}")
    if meta["privacy"] != status["privacyStatus"]:
        print(f"warning: asked for {status['privacyStatus']}, got {meta['privacy']}"
              " - the API project may need the YouTube API Services audit")
    print(f"studio:   https://studio.youtube.com/video/{vid}/edit")

    thumb = args.folder / "output" / "thumbnail.png"
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/png")).execute()
        print("thumbnail: set")
    except HttpError as e:
        print(f"thumbnail: not set ({e.resp.status} {e.reason}) - upload it in YouTube Studio on a computer")


if __name__ == "__main__":
    main()
