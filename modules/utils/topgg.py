import os
import sys
import threading

import requests

from modules.utils.data_store import read_json
from modules.utils.logger import get_logger

logger = get_logger('top.gg')

_lock = threading.Lock()
_stop = threading.Event()

BROWSERS = [
    ('chrome-win64', 'chrome.exe'),
    ('chrome-win32', 'chrome.exe'),
    ('chrome-linux64', 'chrome'),
    ('chrome-linux', 'chrome'),
    ('chrome-mac-arm64', 'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
    ('chrome-mac-x64', 'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
    ('chrome', 'chrome.exe'),
    ('chrome', 'chrome'),
    ('chrome', 'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
]

# Fallback for a system-installed browser. Not used for voting anymore (that
# moved to the separate vote-service), but kept for app.py's /api/debug/chrome
# diagnostic route.
SYSTEM_BROWSER_PATHS = [
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
]

# The actual voting (puppeteer-extra + stealth plugin, to get past
# Cloudflare's bot check on top.gg) runs on a separate Render service instead
# of in this process - a full Chrome instance is memory-heavy, and sharing
# this container's RAM with the Discord bot + dashboard was reliably causing
# OOM crashes that took farming down too, not just the vote. Splitting it out
# gives voting its own memory budget, still triggered/controlled from here.
VOTE_SERVICE_URL = os.environ.get('VOTE_SERVICE_URL')
VOTE_SERVICE_SECRET = os.environ.get('VOTE_SERVICE_SECRET')


def stop():
    _stop.set()


def clear_stop():
    _stop.clear()


def find_browser():
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    for folder, binary in BROWSERS:
        path = os.path.join(base, folder, binary)
        if os.path.isfile(path):
            return path
    for path in SYSTEM_BROWSER_PATHS:
        if os.path.isfile(path):
            return path
    return None


def _vote(bot_id, token):
    if not VOTE_SERVICE_URL:
        logger.error('VOTE_SERVICE_URL is not set - the vote service is not configured, skipping vote')
        return False

    settings = read_json('data/settings.json', {}) or {}
    captchaly_key = (settings.get('captchaly') or {}).get('api_key')

    logger.info(f'Voting for bot {bot_id} (via vote service)')

    try:
        resp = requests.post(
            f'{VOTE_SERVICE_URL.rstrip("/")}/vote',
            json={'token': token, 'botId': bot_id, 'captchalyApiKey': captchaly_key},
            headers={'x-vote-secret': VOTE_SERVICE_SECRET or ''},
            timeout=200,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f'Could not reach vote service: {e}')
        return False

    try:
        result = resp.json()
    except ValueError:
        logger.error(f'Vote service returned invalid response (status {resp.status_code}): {resp.text[:500]!r}')
        return False

    if result.get('success'):
        logger.info(f'Vote: {result.get("message")}')
        return True

    logger.warning(f'Vote failed: {result.get("message")}')
    return False


def vote(bot_id, token):
    with _lock:
        if _stop.is_set():
            logger.warning('Vote skipped (stop requested)')
            return False
        return _vote(bot_id, token)
