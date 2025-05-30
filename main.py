import os
import atexit
import logging
from datetime import datetime, timedelta

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

dotenv.load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_ID')
MAX_MESSAGE_LENGTH = 3500
MM_TEXT = ': столько дней мы продержались, не упоминая Modest Mouse.'


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
        filters.TEXT & ~filters.COMMAND,
        message_handler
    ))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot is now polling for updates.")


if __name__ == '__main__':
    main()
