import asyncio
import random

from modules.utils import topgg


class Vote:
    @staticmethod
    async def vote(client):
        if not client.can_run():
            return
        bot_id = getattr(client.owo_bot, 'id', None)
        if not bot_id:
            return
        cookie = client.config.get('vote_cookie')
        if not cookie:
            client.logger.warning('No vote_cookie configured for this account, skipping vote (see data/owo.json)')
            await asyncio.sleep(3600)
            return
        client.logger.info('Voting on top.gg')
        if await asyncio.to_thread(topgg.vote, bot_id, cookie, 'vote_cookie'):
            client.logger.info('Voted (next in 12h)')
            await asyncio.sleep(12 * 3600)
        else:
            wait = random.randint(600, 1200)
            client.logger.warning(f'Vote failed, retry in {wait}s')
            await asyncio.sleep(wait)