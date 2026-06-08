#!/usr/bin/env python3
"""
IPTV807 Token Refresh Script
Scrapes fresh tokens from iptv807.com category pages and updates channels.js
"""
import re
import subprocess
import time
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
BASE_URL = 'https://iptv807.com'
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_JS = os.path.join(PROJECT_DIR, 'js', 'channels.js')
PLAYER_BASE = os.path.join(PROJECT_DIR, 'player')

# All 11 categories with their display names
CATEGORIES = {
    'itv': '綜合',
    'ty': '體育',
    'ys': '央視',
    'ws': '衛視',
    'gt': '港澳台',
    'other': '其他',
    'movie': '電影',
    'migu': '咪咕視頻',
    'fjitv': '福建移動IPTV',
    'hlitv': '黑龍江移動IPTV',
    'ipv6': 'IPv6網絡電視',
}


def fetch_category_page(tid):
    """Fetch category page and extract channel data."""
    url = f'{BASE_URL}/?act=category&tid={tid}'
    try:
        result = subprocess.run(
            ['curl', '-s', '-A', UA, url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0 or not result.stdout:
            print(f'  ✗ Failed to fetch {tid}: curl error')
            return []
        
        html = result.stdout
        # Parse: token=XXX&tid=YYY&id=ZZZ">ChannelName</a>
        matches = re.findall(
            r'token=([a-f0-9]{32})&tid=\w+&id=(\d+)"[^>]*>([^<]+)',
            html
        )
        
        channels = []
        for token, ch_id, name in matches:
            channels.append({
                'id': int(ch_id),
                'name': name.strip(),
                'token': token
            })
        
        return channels
    
    except subprocess.TimeoutExpired:
        print(f'  ✗ Timeout fetching {tid}')
        return []
    except Exception as e:
        print(f'  ✗ Error fetching {tid}: {e}')
        return []


def generate_channels_js(all_data):
    """Generate the channels.js file content."""
    lines = ['var CHANNELS_DATA = {']
    
    cat_items = list(CATEGORIES.items())
    for i, (tid, cat_name) in enumerate(cat_items):
        channels = all_data.get(tid, [])
        comma = ',' if i < len(cat_items) - 1 else ''
        
        lines.append(f"    '{tid}': {{ name: '{cat_name}', channels: [")
        for j, ch in enumerate(channels):
            ch_comma = ',' if j < len(channels) - 1 else ''
            # Escape single quotes in channel name
            safe_name = ch['name'].replace("'", "\\'")
            lines.append(f"        {{ id: {ch['id']}, name: '{safe_name}', token: '{ch['token']}' }}{ch_comma}")
        lines.append(f'    ] }}{comma}')
    
    lines.append('};')
    return '\n'.join(lines)


def clean_player_page(html):
    if not html or len(html) < 1000:
        return None
    
    # Fix pvjs.js path to absolute
    html = re.sub(r'src="/pvjs\.js\?t=(\d+)"', r'src="https://iptv807.com/pvjs.js?t=\1"', html)
    
    # Remove Cloudflare challenge script
    html = re.sub(r'<script>\(function\(\){function c\(\).*?document\.onreadystatechange.*?</script>', '', html, flags=re.DOTALL)
    
    # Remove ad link
    html = re.sub(r'<center><a href="https://d\.2026016\.xyz/down\.php"[^>]*>.*?</a></center>', '', html, flags=re.DOTALL)
    
    # Remove 51.la analytics
    html = re.sub(r'<script[^>]*src="//js\.users\.51\.la[^"]*"[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    
    # Remove gtag script
    html = re.sub(r"<script[^>]*src='https://www\.googletagmanager\.com[^']*'[^>]*>.*?</script>", '', html, flags=re.DOTALL)
    
    # Remove dataLayer script (specific match)
    html = re.sub(r'<script>\s+window\.dataLayer\s*=\s*window\.dataLayer.*?</script>', '', html, flags=re.DOTALL)
    
    # Remove hidden span
    html = re.sub(r'<span style="display:none">.*?从缓存读取内容.*?</span>', '', html, flags=re.DOTALL)
    
    return html


def fetch_single_page(ch, tid, ua):
    ch_id = ch['id']
    token = ch['token']
    name = ch['name']
    url = f'{BASE_URL}/?act=play&token={token}&tid={tid}&id={ch_id}'
    
    try:
        result = subprocess.run(
            ['curl', '-s', '-A', ua, url],
            capture_output=True, text=True, timeout=20
        )
        html = result.stdout
        cleaned = clean_player_page(html)
        return (ch_id, name, cleaned, None)
    except Exception as e:
        return (ch_id, name, None, str(e))


def refresh_category_pages(tid, channels):
    cat_dir = os.path.join(PLAYER_BASE, tid)
    os.makedirs(cat_dir, exist_ok=True)
    
    # 港澳台 needs iOS UA, others work with any UA
    ua = UA if tid == 'gt' else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    success = 0
    errors = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_single_page, ch, tid, ua): ch for ch in channels}
        for future in as_completed(futures):
            ch_id, name, cleaned, err = future.result()
            if err:
                errors.append(f"ID {ch_id} ({name}): {err}")
            elif cleaned is None:
                errors.append(f"ID {ch_id} ({name}): page too short")
            else:
                filepath = os.path.join(cat_dir, f'{ch_id}.html')
                with open(filepath, 'w') as f:
                    f.write(cleaned)
                success += 1
    
    return success, errors


def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'=== IPTV807 Token Refresh ===')
    print(f'Time: {now}')
    print()
    
    # Step 1: Scrape all categories
    print('Step 1: Fetching category pages...')
    all_data = {}
    total_channels = 0
    
    for tid, cat_name in CATEGORIES.items():
        channels = fetch_category_page(tid)
        all_data[tid] = channels
        count = len(channels)
        total_channels += count
        status = '✓' if count > 0 else '✗'
        print(f'  {status} {cat_name} ({tid}): {count} channels')
        time.sleep(0.5)  # Rate limit
    
    print(f'\nTotal: {total_channels} channels across {len(CATEGORIES)} categories')
    
    # Step 2: Generate channels.js
    print('\nStep 2: Generating channels.js...')
    js_content = generate_channels_js(all_data)
    
    with open(CHANNELS_JS, 'w') as f:
        f.write(js_content)
    
    file_size = os.path.getsize(CHANNELS_JS)
    print(f'  ✓ Written to {CHANNELS_JS} ({file_size:,} bytes)')
    
    print('\nStep 3: Refreshing player pages for all categories...')
    total_pages = 0
    total_errors = 0
    
    for tid, cat_name in CATEGORIES.items():
        channels = all_data.get(tid, [])
        if not channels:
            print(f'  ✗ {cat_name} ({tid}): no channels')
            continue
        
        success, errors = refresh_category_pages(tid, channels)
        total_pages += success
        total_errors += len(errors)
        status = '✓' if success == len(channels) else '~'
        print(f'  {status} {cat_name} ({tid}): {success}/{len(channels)} pages')
        if errors:
            for e in errors[:2]:
                print(f'    {e}')
        time.sleep(0.3)
    
    print(f'\nTotal: {total_pages} pages generated, {total_errors} errors')
    
    print(f'\n=== Done! ===')
    return 0


if __name__ == '__main__':
    sys.exit(main())
