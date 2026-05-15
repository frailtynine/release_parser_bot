import os
import re
import atexit
import asyncio
import logging
from datetime import datetime, timedelta
from io import BytesIO
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)
import dotenv

from utilities import (
    combine_lists,
    parse_sg_releases,
    parse_cos_releases
)
from consts import MM_TEXTS
from get_links import get_releases

dotenv.load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_ID')
MUSIKLINK_KEY = os.getenv('MUSICLINK_KEY')
MAX_MESSAGE_LENGTH = 3500
MM_TEXT = ': столько дней мы продержались, не упоминая Modest Mouse.'
SPOTIFY_URL_PATTERN = r'https?://open\.spotify\.com/[^\s]+'


def cleanup():
    if 'BOT_ID' in os.environ:
        del os.environ['BOT_ID']
    logger.info("Environment cleaned up!")


async def parse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_parse = context.application.bot_data.get('last_parse_time')
    current_time = datetime.now()
    if last_parse and (current_time - last_parse) < timedelta(minutes=5):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Подожди пять минут, а. Уже спрашивали."
        )
        return
    context.application.bot_data['last_parse_time'] = current_time
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Парсю релизы, подожди немного..."
    )
    releases = await get_message()
    releases = releases.get_releases(title=True)
    message = ''
    for band, album in sorted(releases.items()):
        if len(message) < 3800:
            message += f'{band} — {album}\n'
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message
            )
            message = ''
    if message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )


async def get_message():
    cos_releases = await parse_cos_releases()
    sg_releases = await parse_sg_releases()
    logger.info("Fetched releases successfully.")
    return combine_lists(cos_releases, sg_releases)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received message from user: %s", update.effective_user.id)
    if (
        update.message
        and update.message.from_user.id != context.bot.id
        and update.message.text
    ):
        for mm_text in MM_TEXTS:
            if mm_text in update.message.text.lower():
                mm_days = context.application.bot_data.get('mm_days')
                mm_overall = context.application.bot_data.get('mm_overall', 0)
                if not mm_days:
                    context.application.bot_data['mm_days'] = datetime.now()
                else:
                    days_passed = datetime.now() - mm_days
                    context.application.bot_data['mm_overall'] = mm_overall + 1
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=(
                            f"{days_passed.days}{MM_TEXT}"
                            f"\n\nВсего упоминаний Modest Mouse: "
                            f"{mm_overall + 1}"
                        )
                    )
                    context.application.bot_data['mm_days'] = datetime.now()


async def spotify_links_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if (
        not update.message
        or update.message.from_user.id == context.bot.id
        or not update.message.text
    ):
        return

    spotify_urls = [
        url.rstrip('.,!?)]>')
        for url in re.findall(SPOTIFY_URL_PATTERN, update.message.text)
    ]
    unique_spotify_urls = list(dict.fromkeys(spotify_urls))

    for spotify_url in unique_spotify_urls:
        release_links = await asyncio.to_thread(
            get_releases,
            spotify_url,
            MUSIKLINK_KEY
        )
        logger.info(release_links)
        streaming_links = [
            f'Spotify: {release_links.spotify_url}',
        ]
        if release_links.apple_music_url:
            streaming_links.append(
                f'Apple Music: {release_links.apple_music_url}'
            )
        if release_links.deezer_url:
            streaming_links.append(
                f'Deezer: {release_links.deezer_url}'
            )
        if release_links.tidal_url:
            streaming_links.append(
                f'Tidal: {release_links.tidal_url}'
            )

        caption = (
            f'{release_links.artist_name} — {release_links.album_name}\n\n'
            + '\n'.join(streaming_links)
        )
        response = requests.get(release_links.image_url, timeout=10)
        response.raise_for_status()
 
        photo = BytesIO(response.content)
        photo.name = "cover.jpg"

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo,
            caption=caption
        )


def main():
    logger.info("Starting bot...")
    atexit.register(cleanup)
    persistence = PicklePersistence(filepath='bot_data.pickle')
    app = Application.builder().token(
        BOT_TOKEN
    ).persistence(
        persistence
    ).build()
    app.add_handler(CommandHandler('parse', parse_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(SPOTIFY_URL_PATTERN),
        spotify_links_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handler
    ), group=1)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot is now polling for updates.")


if __name__ == '__main__':
    main()
