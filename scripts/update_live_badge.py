"""Run locally to update the two-state live badge; failed checks leave it unchanged."""

from http.client import HTTPException
import json
from pathlib import Path
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOM_ID = 7013636
OWNER_UID = 230632
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "live-status.svg"
STATES = {
    0: ("", "#9b8cff", "直播间：未开播"),
    1: ("配信中", "#ec6c9b", "直播间：配信中"),
}


def parse_status(payload):
    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise ValueError("Bilibili did not return a successful room response")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Room data is missing")
    if data.get("room_id") != ROOM_ID or data.get("uid") != OWNER_UID:
        raise ValueError("Room identity does not match the profile")
    status = data.get("live_status")
    if type(status) is not int or status not in (0, 1, 2):
        raise ValueError("Room live status is missing or unknown")
    # Only an active broadcast is live; Bilibili's recorded replay is not live.
    return 1 if status == 1 else 0


def fetch_status():
    request = Request(
        f"https://api.live.bilibili.com/room/v1/Room/room_init?id={ROOM_ID}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://live.bilibili.com/{ROOM_ID}"},
    )
    with urlopen(request, timeout=15) as response:
        return parse_status(json.loads(response.read(16384)))


def render_badge(status):
    label, color, title = STATES[status]
    width = 117 if status == 1 else 55
    indicator = ""
    if status == 1:
        indicator = f'''<path d="M55 0h62v20H55z" fill="{color}" />
  <g font-family="Microsoft YaHei,Noto Sans CJK SC,sans-serif" font-size="10" fill="white">
    <circle cx="65" cy="10" r="3">
      <animate attributeName="opacity" values="1;0.35;1" dur="1.6s" repeatCount="indefinite" />
    </circle>
    <text x="90" y="14" text-anchor="middle">{label}</text>
  </g>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" viewBox="0 0 {width} 20" role="img" aria-labelledby="title">
  <title id="title">{title}</title>
  <rect width="55" height="20" fill="#9b8cff" />
  <g fill="none" stroke="white" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="6" y="6" width="12" height="9" rx="1" />
    <path d="m9 3 3 3 3-3M9.5 9.5v2m5-2v2" />
  </g>
  <text x="36" y="14" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="10" fill="white">LIVE</text>
{indicator}
</svg>
'''


def main():
    try:
        status = fetch_status()
    except (HTTPException, URLError, TimeoutError, OSError, ValueError) as error:
        print(f"Live status unavailable ({type(error).__name__}); badge left unchanged.", file=sys.stderr)
        return 1
    svg = render_badge(status)
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != svg:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Bilibili room {ROOM_ID}: {'live' if status == 1 else 'not live'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
