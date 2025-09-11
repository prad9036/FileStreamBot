import logging
import math
import re
import base64
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from WebStreamer.vars import Var
from WebStreamer.utils.database import Database
from WebStreamer.utils.Translation import Language, BUTTON
from WebStreamer.utils.bot_utils import is_user_accepted_tos, validate_user
from WebStreamer.server.exceptions import FIleNotFound
import datetime
from WebStreamer.utils.bot_utils import file_format
from WebStreamer.utils.human_readable import humanbytes
db = Database(Var.DATABASE_URL, Var.SESSION_NAME)

# Set up logging for this file
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Filter to handle only the specific callbacks for this file
general_callback_filter = filters.regex(r'^(home|help|about|N/A|close|msgdelconf2|msgdelyes|userfiles|myfile|accepttos|sendfile).*$')

@Client.on_callback_query(general_callback_filter)
async def cb_data(bot: Client, update: CallbackQuery):
    logger.info(f"User {update.from_user.id} clicked a button. Callback data: {update.data}")
    lang = Language(update)
    usr_cmd = update.data.split("_")
    if usr_cmd[0] == "home":
        await update.message.edit_text(
            text=lang.START_TEXT.format(update.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=BUTTON.START_BUTTONS
        )
    elif usr_cmd[0] == "help":
        await update.message.edit_text(
            text=lang.HELP_TEXT.format(Var.UPDATES_CHANNEL),
            disable_web_page_preview=True,
            reply_markup=BUTTON.HELP_BUTTONS
        )
    elif usr_cmd[0] == "about":
        await update.message.edit_text(
            text=lang.ABOUT_TEXT.format(__version__),
            disable_web_page_preview=True,
            reply_markup=BUTTON.ABOUT_BUTTONS
        )
    elif usr_cmd[0] == "N/A":
        await update.answer("N/A", True)
    elif usr_cmd[0] == "close":
        await update.message.delete()
    elif usr_cmd[0] == "msgdelconf2":
        await update.message.edit_caption(
            caption= "<b>Do You Want to Delete the file<b>\n" + update.message.caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data=f"msgdelyes_{usr_cmd[1]}_{usr_cmd[2]}"), InlineKeyboardButton("No", callback_data=f"myfile_{usr_cmd[1]}_{usr_cmd[2]}")]])
        )
    elif usr_cmd[0] == "msgdelyes":
        await delete_user_file(usr_cmd[1], update)
        return
    elif usr_cmd[0] == "userfiles":
        # Correctly unpacking all three values: file_list, total_files, and total_pages
        file_list, total_files, total_pages = await gen_file_list_button(int(usr_cmd[1]), update.from_user.id)
        await update.message.edit_caption(
            caption="Total files: {}".format(total_files),
            reply_markup=InlineKeyboardMarkup(file_list)
        )
    elif usr_cmd[0] == "myfile":
        # Check for optional search query
        if len(usr_cmd) > 3:
            await gen_file_menu(usr_cmd[1], usr_cmd[2], update, search_query=usr_cmd[3])
        else:
            await gen_file_menu(usr_cmd[1], usr_cmd[2], update)
        return
    elif usr_cmd[0] == "accepttos":
        await db.agreed_tos(int(usr_cmd[1]))
        await update.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ I accepted the TOS", callback_data="N/A")]]))
    elif usr_cmd[0] == "sendfile":
        myfile = await db.get_file(usr_cmd[1])
        await update.answer(f"Sending File {myfile['file_name']}")
        await update.message.reply_cached_media(myfile['file_id'])

async def gen_file_list_button(file_list_no: int, user_id: int):
    """
    Generate file list buttons for a given page and user.
    """
    # Correctly passing the page number and unpacking all three values returned by db.find_files
    user_files, total_files, total_pages = await db.find_files(user_id, page=file_list_no, limit=10)
    
    file_list=[]
    for x in user_files:
        file_list.append([InlineKeyboardButton(x["file_name"], callback_data=f"myfile_{x['_id']}_{file_list_no}")])
    
    if total_files > 10:
        file_list.append(
            [
                InlineKeyboardButton("<<", callback_data="{}".format("userfiles_"+str(file_list_no-1) if file_list_no > 1 else 'N/A')),
                InlineKeyboardButton(f"{file_list_no}/{total_pages}", callback_data="N/A"),
                InlineKeyboardButton(">>", callback_data="{}".format("userfiles_"+str(file_list_no+1) if file_list_no < total_pages else 'N/A'))
            ]
        )
    if not file_list:
        file_list.append([InlineKeyboardButton("Empty", callback_data="N/A")])
    # Now returning the file list, total file count, and total pages for the calling function
    return file_list, total_files, total_pages

async def gen_file_menu(_id, file_list_no, update: CallbackQuery, search_query=None):
    try:
        myfile_info = await db.get_file(_id)
    except FIleNotFound:
        await update.answer("File Not Found")
        return

    file_type = file_format(myfile_info['file_id'])

    # ⬇️ Updated stream & page links
    file_name_encoded = myfile_info['file_name'].replace(" ", "%20")
    page_link = f"{Var.URL}watch/{myfile_info['_id']}"
    stream_link = f"{Var.URL}dl/{myfile_info['_id']}/{file_name_encoded}"

    TiMe = myfile_info['time']
    if isinstance(TiMe, float):
        date = datetime.datetime.fromtimestamp(TiMe)
    
    # Dynamically set the back button based on the search_query parameter
    back_button_callback = f"userfiles_{file_list_no}"
    if search_query:
        back_button_callback = f"search-{search_query}-{file_list_no}"

    await update.edit_message_caption(
        caption="Name: {}\nFile Size: {}\nType: {}\nCreated at: {}\nTime: {}".format(
            myfile_info['file_name'],
            humanbytes(int(myfile_info['file_size'])),
            file_type,
            TiMe if isinstance(TiMe, str) else date.date(),
            "N/A" if isinstance(TiMe, str) else date.time().strftime("%I:%M:%S %p %Z")
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Back", callback_data=back_button_callback),
                    InlineKeyboardButton("Delete Link", callback_data=f"msgdelconf2_{myfile_info['_id']}_{file_list_no}")
                ],
                [
                    InlineKeyboardButton("🖥STREAM", url=page_link),
                    InlineKeyboardButton("Dᴏᴡɴʟᴏᴀᴅ 📥", url=stream_link)
                ],
                [InlineKeyboardButton("Get File", callback_data=f"sendfile_{myfile_info['_id']}")]
            ]
        )
    )

async def delete_user_file(_id, update:CallbackQuery):
    try:
        myfile_info=await db.get_file(_id)
    except FIleNotFound:
        await update.answer("File Not Found")
        return

    await db.delete_one_file(myfile_info['_id'])
    await update.message.edit_caption(
        caption= "<b>Deleted Link Successfully<b>\n" + update.message.caption.replace("Do You Want to Delete the file", ""),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"userfiles_1")]])
    )

