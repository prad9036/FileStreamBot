import time
import math
import logging
import mimetypes
import traceback
import urllib.parse
import re
import PTN

from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from pymongo import MongoClient
from bson.objectid import ObjectId

from WebStreamer.bot import multi_clients, work_loads, StreamBot
from WebStreamer.vars import Var
from WebStreamer.server.exceptions import FIleNotFound, InvalidHash
from WebStreamer import utils, StartTime, __version__
from WebStreamer.utils.render_template import render_page

# ── MongoDB Setup ──
import os
from pymongo import MongoClient

mongo_client = MongoClient(os.environ.get("DATABASE_URL"))

db = mongo_client["F2LxBot"]
videos = db["file"]

# ── Config ──
import os

FQDN = os.environ.get("FQDN", "localhost:8080")
BASE_URL = f"https://{FQDN}/dl"


def format_movie(doc):
    return {
        "title": doc["file_name"],
        "url": f"{BASE_URL}/{doc['_id']}/{urllib.parse.quote(doc['file_name'])}"
    }

# ── Aiohttp App ──
routes = web.RouteTableDef()

@routes.get("/latest")
async def latest(request):
    doc = videos.find_one(sort=[("time", -1)])
    if not doc:
        return web.json_response({"_id": None, "time": 0})
    return web.json_response({"_id": str(doc["_id"]), "time": doc["time"]})

@routes.get("/featured")
async def featured(request):
    docs = videos.find().sort("time", -1).limit(10)
    return web.json_response({"movies": [format_movie(doc) for doc in docs]})

@routes.get("/search")
async def search(request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.json_response({"movies": []})
    regex = ".*".join(re.escape(w) for w in q.lower().split())
    docs = videos.find({"file_name": {"$regex": regex, "$options": "i"}}).sort("time", -1).limit(30)
    return web.json_response({"movies": [format_movie(doc) for doc in docs]})

@routes.get("/play")
async def play(request):
    vid = request.query.get("id")
    if not vid:
        return web.Response(text="Missing video ID", status=400)
    doc = videos.find_one({"_id": ObjectId(vid)}) if ObjectId.is_valid(vid) else videos.find_one({"_id": vid})
    if not doc:
        return web.Response(text="Video not found", status=404)
    fname = doc["file_name"]
    return web.HTTPFound(location=f"{BASE_URL}/{doc['_id']}/{urllib.parse.quote(fname)}")

@routes.get("/parse")
async def parse_handler(request):
    q = request.query.get("q")
    if not q:
        return web.json_response({"error": "Missing ?q= parameter"}, status=400)
    return web.json_response(PTN.parse(q))

@routes.get("/status", allow_head=True)
async def status_route_handler(_):
    return web.json_response({
        "server_status": "running",
        "uptime": utils.get_readable_time(time.time() - StartTime),
        "telegram_bot": "@" + StreamBot.username,
        "connected_bots": len(multi_clients),
        "loads": {
            f"bot{c+1}": l for c, (_, l) in enumerate(sorted(work_loads.items(), key=lambda x: x[1], reverse=True))
        },
        "version": __version__,
    })

@routes.get("/watch/{path}", allow_head=True)
async def watch_route_handler(request):
    try:
        html = await render_page(request.match_info["path"])
        return web.Response(text=html, content_type="text/html")
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e)
        logging.debug(traceback.format_exc())
        raise web.HTTPInternalServerError(text=str(e))

@routes.get("/dl/{path}/{filename}", allow_head=True)
async def dl_route_handler(request):
    try:
        return await media_streamer(request, request.match_info["path"], request.match_info["filename"])
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e)
        logging.debug(traceback.format_exc())
        raise web.HTTPInternalServerError(text=str(e))

# ── Media Streaming Logic ──
class_cache = {}

async def media_streamer(request, path, filename):
    range_header = request.headers.get("Range", "")
    idx = min(work_loads, key=work_loads.get)
    client = multi_clients[idx]
    if Var.MULTI_CLIENT:
        logging.info(f"Client {idx} serving {request.remote}")
    if client in class_cache:
        conn = class_cache[client]
    else:
        conn = utils.ByteStreamer(client)
        class_cache[client] = conn

    file_id = await conn.get_file_properties(path, multi_clients)
    file_size = file_id.file_size

    if range_header:
        try:
            parts = range_header.replace("bytes=", "").split("-")
            from_b = int(parts[0]) if parts[0] else 0
            to_b = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        except (IndexError, ValueError):
            from_b, to_b = 0, file_size - 1
    else:
        from_b, to_b = 0, file_size - 1

    if to_b > file_size or from_b < 0 or to_b < from_b:
        return web.Response(status=416, text="Range Not Satisfiable", headers={"Content-Range": f"bytes */{file_size}"})

    chunk = 1024 * 1024
    offset = from_b - (from_b % chunk)
    first_cut = from_b - offset
    last_cut = to_b % chunk + 1
    length = to_b - from_b + 1
    parts_count = math.ceil(to_b / chunk) - math.floor(offset / chunk)

    body = conn.yield_file(file_id, idx, offset, first_cut, last_cut, parts_count, chunk)
    ctype = file_id.mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    headers = {
        "Content-Type": ctype,
        "Content-Range": f"bytes {from_b}-{to_b}/{file_size}",
        "Content-Length": str(length),
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
    }
    return web.Response(status=206 if range_header else 200, body=body, headers=headers)

import asyncio
import subprocess
import re

@routes.get("/insta")
async def insta_handler(request):
    reel_url = request.query.get("url")
    if not reel_url:
        return web.json_response({"error": "Missing ?url parameter"}, status=400)

    curl_cmd = [
        "curl", "https://bestmediatool.com/",
        "-H", "authority: bestmediatool.com",
        "-H", "accept: text/x-component",
        "-H", "accept-language: en-GB,en-US;q=0.9,en;q=0.8,hi;q=0.7",
        "-H", "content-type: text/plain;charset=UTF-8",
        "-H", "cookie: NEXT_LOCALE=en",
        "-H", "dnt: 1",
        "-H", "next-action: f87b40794a0dc15dbcbc778d5d915b41d9954cb1",
        "-H", "next-router-state-tree: %5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22en%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2F%22%2C%22refresh%22%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D%5D",
        "-H", "origin: https://bestmediatool.com",
        "-H", "referer: https://bestmediatool.com/",
        "-H", 'sec-ch-ua: "Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        "-H", "sec-ch-ua-mobile: ?0",
        "-H", 'sec-ch-ua-platform: "Windows"',
        "-H", "sec-fetch-dest: empty",
        "-H", "sec-fetch-mode: cors",
        "-H", "sec-fetch-site: same-origin",
        "-H", "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "--data-raw", f"[\"{reel_url}\"]",
        "--compressed"
    ]

    try:
        # Run curl in async way
        process = await asyncio.create_subprocess_exec(
            *curl_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return web.json_response({"error": stderr.decode().strip()}, status=500)

        output = stdout.decode()

        match = re.search(r'https[^"\']+\.mp4[^"\']*', output)
        if match:
            return web.json_response({"mp4": match.group(0)})
        else:
            return web.json_response({"error": "No .mp4 found in response"}, status=404)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ── Run App ──
def run_app():
    app = web.Application()
    app.add_routes(routes)
    return app

if __name__ == "__main__":
    web.run_app(run_app(), host="0.0.0.0", port=Var.PORT)
