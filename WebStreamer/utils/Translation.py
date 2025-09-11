# This file is a part of FileStreamBot

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from WebStreamer.vars import Var

class Language:
    def __new__(self, message: Message):
        if getattr(message.from_user, 'language_code', 'Unknown') in self.available:
            return getattr(self, getattr(message.from_user, 'language_code', "en"), self.en)
        else:
            return self.en

    available = ['en', 'language_code']

    class en:
        START_TEXT: str = """
<i>👋 Hello, {}!</i>\n
<i>I'm your friendly Telegram File Streaming Bot and Direct Link Generator.</i>\n
<i>Click <b>Help</b> to see what I can do for you!</i>\n
<i><u>⚠️ NOTE:</u></i>\n
<b>Adult content is not allowed and may result in a permanent ban.</b>\n\n"""

        HELP_TEXT: str = """
<i>Here’s how to use me:</i>
<i>• Send me any file or media from Telegram.</i>
<i>• I will provide a fast, external direct download link.</i>
<i>• You can also watch media online instantly!</i>
<u>⚠️ IMPORTANT:</u>\n
<b>Adult content is strictly prohibited and may get you banned.</b>\n
<i>Need help? Contact the developer here:</i> <b><a href='https://t.me/{}'>Click Here</a></b>"""

        ABOUT_TEXT: str = """
<b>🤖 Bot Name:</b> Public Link Generator
<b>🔸 Version:</b> {}
<b>🔹 Last Updated:</b> 05-Nov-2023, 12:55 PM"""

        STREAM_MSG_TEXT: str = """
<i><u>🎉 Your Link is Ready!</u></i>\n
<b>📂 File Name:</b> <i>{}</i>\n
<b>📦 File Size:</b> <i>{}</i>\n
<b>📥 Download Link:</b> <i>{}</i>\n
<b>🖥 Watch Online:</b> <i>{}</i>\n
<b>Generated via:</b> <a href='https://t.me/{}'>{}</a>"""

        BAN_TEXT: str = "__Oops! You’re banned from using me.__\n\n" \
                        "**Please contact the developer:** [Click Here](tg://user?id={})"

        LINK_LIMIT_EXCEEDED: str = "You’ve reached your maximum number of generated links for now. Try again later!"

        INFO_TEXT: str = """<b>Your Account Info:</b>
User ID: <code>{}</code>
Plan: <code>{}</code>
Links Used: <code>{}</code>
Links Left: <code>{}</code>"""

    class language_code:
        # Placeholder for custom language translations
        START_TEXT = "Your translated start text here"
        HELP_TEXT = "Your translated help text here"
        ABOUT_TEXT = "Your translated about text here"
        STREAM_MSG_TEXT = "Your translated stream message here"
        BAN_TEXT = "Your translated ban text here"


# ----------------------------- BUTTONS ----------------------------- #

class BUTTON:
    START_BUTTONS = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('📖 Help', callback_data='help'),
                InlineKeyboardButton('ℹ️ About', callback_data='about'),
                InlineKeyboardButton('❌ Close', callback_data='close')
            ],
            [InlineKeyboardButton("📢 Bot Channel", url=f'https://t.me/{Var.UPDATES_CHANNEL}')]
        ]
    )

    HELP_BUTTONS = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('🏠 Home', callback_data='home'),
                InlineKeyboardButton('ℹ️ About', callback_data='about'),
                InlineKeyboardButton('❌ Close', callback_data='close')
            ],
            [InlineKeyboardButton("📢 Bot Channel", url=f'https://t.me/{Var.UPDATES_CHANNEL}')]
        ]
    )

    ABOUT_BUTTONS = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('🏠 Home', callback_data='home'),
                InlineKeyboardButton('📖 Help', callback_data='help'),
                InlineKeyboardButton('❌ Close', callback_data='close')
            ],
            [InlineKeyboardButton("📢 Bot Channel", url=f'https://t.me/{Var.UPDATES_CHANNEL}')]
        ]
    )
