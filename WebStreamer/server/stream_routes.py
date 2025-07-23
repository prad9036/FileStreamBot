import time
import math
import logging
import mimetypes
import traceback
import urllib.parse
import re
import sqlite3
import os
import PTN

from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine

from WebStreamer.bot import multi_clients, work_loads, StreamBot
from WebStreamer.vars import Var
from WebStreamer.server.exceptions import FIleNotFound, InvalidHash
from WebStreamer import utils, StartTime, __version__
from WebStreamer.utils.render_template import render_page

# ── Config ──
DB_PATH = "video_files.db"
BASE_URL = "https://extent-gentleman-slot-skiing.trycloudflare.com/dl"

# ── SQLite helpers ──
def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def regexp(expr, item):
    if item is None:
        return False
    try:
        return re.search(expr, item, re.IGNORECASE) is not None
    except re.error:
        return False

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("REGEXP", 2, regexp)
    ensure_table_exists(conn)
    return conn

def ensure_table_exists(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            _id TEXT PRIMARY KEY,
            file_name TEXT,
            file_size INTEGER,
            mime_type TEXT,
            user_id INTEGER,
            file_unique_id TEXT,
            time REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON videos(file_name);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON videos(time);")
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
            _id UNINDEXED,
            file_name
        )
    """)
    conn.commit()

def format_movie(row):
    fname = row["file_name"]
    return {
        "title": fname,
        "url": f"{BASE_URL}/{row['_id']}/{urllib.parse.quote(fname)}"
    }

# ── Set up aiohttp app and routes ──
routes = web.RouteTableDef()

@routes.get("/latest")
async def latest(request):
    with get_db() as conn:
        row = conn.execute("SELECT _id, time FROM videos ORDER BY time DESC LIMIT 1").fetchone()
    if not row:
        return web.json_response({"_id": None, "time": 0})
    return web.json_response({"_id": row["_id"], "time": row["time"]})

@routes.post("/push")
async def push_entry(request):
    data = await request.json()
    if not data or any(field not in data for field in ["_id", "file_name", "file_size", "mime_type", "user_id", "file_unique_id", "time"]):
        return web.HTTPBadRequest(text="Missing required fields")

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO videos (_id, file_name, file_size, mime_type, user_id, file_unique_id, time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (data["_id"], data["file_name"], data["file_size"], data["mime_type"], data["user_id"], data["file_unique_id"], data["time"])
            )
            conn.execute("INSERT INTO videos_fts (_id, file_name) VALUES (?, ?)",
                         (data["_id"], data["file_name"]))
            conn.commit()
        return web.json_response({"status": "ok"}, status=201)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.post("/bulk_push")
async def bulk_push(request):
    data = await request.json()
    if not isinstance(data, list):
        return web.json_response({"error": "Expected a list of records"}, status=400)

    inserted = 0
    with get_db() as conn:
        for entry in data:
            if not all(k in entry for k in ["_id", "file_name", "file_size", "mime_type", "user_id", "file_unique_id", "time"]):
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO videos (_id, file_name, file_size, mime_type, user_id, file_unique_id, time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (entry["_id"], entry["file_name"], entry["file_size"], entry["mime_type"], entry["user_id"], entry["file_unique_id"], entry["time"])
                )
                conn.execute("INSERT INTO videos_fts (_id, file_name) VALUES (?, ?)",
                             (entry["_id"], entry["file_name"]))
                inserted += 1
            except:
                continue
        conn.commit()
    return web.json_response({"inserted": inserted, "total_received": len(data)}, status=201)

@routes.get("/featured")
async def featured(request):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY time DESC LIMIT 10").fetchall()
    return web.json_response({"movies": [format_movie(r) for r in rows]})

@routes.get("/search")
async def search(request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.json_response({"movies": []})
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT v.* FROM videos_fts f JOIN videos v ON f._id = v._id WHERE f.file_name MATCH ? ORDER BY v.time DESC LIMIT 30",
            (q,)
        ).fetchall()
    except sqlite3.OperationalError:
        regex = ".*".join(re.escape(w) for w in normalize(q).split())
        rows = conn.execute("SELECT * FROM videos WHERE file_name REGEXP ? ORDER BY time DESC LIMIT 30", (regex,)).fetchall()
    conn.close()
    return web.json_response({"movies": [format_movie(r) for r in rows]})

@routes.get("/play")
async def play(request):
    vid = request.query.get("id")
    if not vid:
        return web.Response(text="Missing video ID", status=400)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM videos WHERE _id = ?", (vid,)).fetchone()
    if not row:
        return web.Response(text="Video not found", status=404)
    fname = row["file_name"]
    return web.HTTPFound(location=f"{BASE_URL}/{vid}/{urllib.parse.quote(fname)}")

@routes.get("/parse")
async def parse_handler(request):
    q = request.query.get("q")
    if not q:
        return web.json_response({"error": "Missing ?q= parameter"}, status=400)
    return web.json_response(PTN.parse(q))

# ── Your existing async routes ──

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
        parts = range_header.replace("bytes=", "").split("-")
        from_b = int(parts[0])
        to_b = int(parts[1]) if parts[1] else file_size - 1
    else:
        from_b, to_b = 0, file_size - 1

    if to_b > file_size or from_b < 0 or to_b < from_b:
        return web.Response(status=416, text="Range Not Satisfiable", headers={"Content-Range": f"bytes */{file_size}"})

    chunk = 1024 * 1024
    to_b = min(to_b, file_size - 1)
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

# ── Run app ──
def run_app():
    app = web.Application()
    app.add_routes(routes)
    return app

if __name__ == "__main__":
    web.run_app(run_app(), host="0.0.0.0", port=Var.PORT)
