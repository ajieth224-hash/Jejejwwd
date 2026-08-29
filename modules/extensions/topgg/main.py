import logging
import threading
import time

from modules.utils import topgg

logger = logging.getLogger('top.gg')

running = False
stop_event = threading.Event()

POLL_INTERVAL = 3600


def read_accounts():
    """Each line is '<bot_id> <cookie>' - only the first space splits the
    line, since a real cookie header string contains spaces of its own."""
    accounts = []
    try:
        with open('data/topgg.txt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.lstrip().startswith('#'):
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    accounts.append((parts[0], parts[1]))
    except FileNotFoundError:
        logger.warning('Top.gg data file not found: data/topgg.txt')
    return accounts


def vote_account(bot_id, cookie):
    logger.info(f'Voting for bot {bot_id}')
    if topgg.vote(bot_id, cookie, source='topgg.txt'):
        logger.info('Voted (next in 12h)')
        return 12 * 3600
    return 0


def main():
    global running
    accounts = read_accounts()
    if not accounts:
        running = False
        return
    logger.info(f'Loaded {len(accounts)} account(s)')
    schedule = [[bot_id, cookie, 0.0] for bot_id, cookie in accounts]
    cycle = 0
    while running:
        cycle += 1
        logger.info(f'-- Vote cycle #{cycle} --')
        for i, entry in enumerate(schedule, 1):
            if not running:
                break
            bot_id, cookie, next_at = entry
            if time.time() < next_at:
                continue
            logger.info(f'Voting ({i}/{len(accounts)})')
            retry = vote_account(bot_id, cookie)
            entry[2] = time.time() + (retry or POLL_INTERVAL)
        next_due = min(max(1.0, e[2] - time.time()) for e in schedule)
        if stop_event.wait(next_due):
            break
    running = False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    running = True
    stop_event.clear()
    main()