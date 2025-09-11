# This file is a part of FileStreamBot

import aiohttp
import aiofiles
import urllib.parse
from WebStreamer.vars import Var
from WebStreamer.utils.database import Database
from WebStreamer.utils.human_readable import humanbytes

db = Database(Var.DATABASE_URL, Var.SESSION_NAME)

async def render_page(db_id):
    # Fetch file info from database
    file_data = await db.get_file(db_id)
    mime_main_type = file_data['mime_type'].split('/')[0].strip()
    
    # Properly encode filename for URL
    encoded_file_name = urllib.parse.quote(file_data['file_name'])

    # Final source URL with filename
    src = f"{Var.URL}dl/{file_data['_id']}/{encoded_file_name}"

    # Title for the page
    if mime_main_type == 'video':
        heading = f"Watch {file_data['file_name']}"
        template_path = 'WebStreamer/template/req.html'
        media_tag = 'video'
    elif mime_main_type == 'audio':
        heading = f"Listen {file_data['file_name']}"
        template_path = 'WebStreamer/template/req.html'
        media_tag = 'audio'
    else:
        heading = f"Download {file_data['file_name']}"
        template_path = 'WebStreamer/template/dl.html'
        media_tag = None

    # Load and fill the template
    async with aiofiles.open(template_path) as template_file:
        template_content = await template_file.read()
        
        if media_tag:
            # req.html: Replace 'tag' placeholder with video/audio
            template_content = template_content.replace('tag', media_tag)
            html = template_content % (heading, file_data['file_name'], src)
        else:
            # dl.html: Add size using HEAD request
            async with aiohttp.ClientSession() as session:
                async with session.head(src) as response:
                    file_size = humanbytes(int(response.headers.get('Content-Length', 0)))
                    html = template_content % (heading, file_data['file_name'], src, file_size)

    return html
