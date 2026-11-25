#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
import requests

CHANNELS = [
    "v2ray_phoenix",
    "ghand_sheken",
    "IRAN_V2PING",
    "V2ray_confiig",
   "vpnsal",

]
STATE_FILE = "state.json"
OUTPUT_FILE = "sub.txt"
KEEP_HOURS = 48

CONFIG_RE = re.compile(r'(?:vless|vmess|trojan|ss|hysteria2|hy2|tuic)://[^\s<>"\']+', re.IGNORECASE)
MESSAGE_SPLIT_RE = re.compile(r'(<div[^>]*class="[^"]*tgme_widget_message_wrap[^"]*"[^>]*>.*?</div>\s*</div>|<div[^>]*class="[^"]*tgme_widget_message[^"]*"[^>]*>.*?</div>)', re.IGNORECASE | re.DOTALL)
TIME_RE = re.compile(r'<time[^>]*datetime="([^"]+)"', re.IGNORECASE)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def clean_link(link):
    link = html.unescape(link).strip()
    while link and link[-1] in '.,;:!?)]}\'"<>':
        link = link[:-1]
    return link

def parse_iso(ts):
    try:
        if ts.endswith("Z"): ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except: return None

def fetch_channel(channel):
    url = f"https://t.me/s/{channel}"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[!] Error fetching {channel}: {e}")
        return None

def extract_from_html(text):
    results = []
    blocks = MESSAGE_SPLIT_RE.findall(text)
    if not blocks: blocks = [text]
    for block in blocks:
        times = TIME_RE.findall(block)
        if not times: continue
        msg_ts = parse_iso(times[0])
        if not msg_ts: continue
        for m in CONFIG_RE.finditer(block):
            link = clean_link(m.group(0))
            if link: results.append((link, msg_ts))
    return results

def load_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)

def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=KEEP_HOURS)
    state = load_state()
    state = {k: v for k, v in state.items() if isinstance(v, str)}
    fetched_ok, new_count = 0, 0
    
    for channel in CHANNELS:
        html_text = fetch_channel(channel)
        if not html_text: continue
        fetched_ok += 1
        pairs = extract_from_html(html_text)
        for link, ts in pairs:
            iso = ts.isoformat()
            if link not in state:
                state[link] = iso
                new_count += 1
            else:
                prev = parse_iso(state[link])
                if not prev or ts < prev: state[link] = iso

    cleaned = {}
    for link, iso in state.items():
        ts = parse_iso(iso)
        if ts and ts >= cutoff: cleaned[link] = iso
    state = cleaned
    save_state(state)

    lines = sorted(state.keys())
    plain = "\n".join(lines)
    encoded = base64.b64encode(plain.encode("utf-8")).decode("ascii")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f: f.write(encoded)

if __name__ == "__main__":
    main()
