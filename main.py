import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import dotenv

from utilities import (
    combine_lists,
    parse_sg_releases,
    parse_cos_releases
)

dotenv.load_dotenv()

BOT_TOKEN = os.getenv('BOT_ID')
MAX_MESSAGE_LENGTH = 3500


async def parse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    messages = await get_message()
    for message in messages:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )


async def get_message():
    cos_releases = await parse_cos_releases()
    sg_releases = await parse_sg_releases()
    merged_list = combine_lists(cos_releases, sg_releases)
    result = []
    for item in merged_list:
        if not result or len(result[-1]) >= MAX_MESSAGE_LENGTH:
            result.append(f'{item[0].title()} - {item[1].title()} \n')
        else:
            result[-1] += f'{item[0].title()} - {item[1].title()} \n'
    return result


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('parse', parse_handler))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
