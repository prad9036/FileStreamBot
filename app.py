import streamlit as st
import subprocess
import os
import time
import json
import hashlib
import requests
from user_agents import parse

st.set_page_config(layout="wide")

SESSION_FILE = "session_data.json"
SERVICES_TRACK_FILE = ".services_started"

# --- Function to get user's IP and Browser details ---
def get_user_info():
    try:
        ip = requests.get("https://api64.ipify.org").text  # Get Public IP
    except:
        ip = "Unknown"

    user_agent = st.query_params.get("user-agent", "Unknown")
    parsed_ua = parse(user_agent)
    browser = f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}"
    
    return ip, browser

# --- Function to check stored sessions ---
def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_sessions(sessions):
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f)

# --- Function to hash IP & browser for privacy ---
def generate_session_key(ip, browser):
    return hashlib.sha256(f"{ip}-{browser}".encode()).hexdigest()

# --- Function to start services only once ---
def start_services():
    if not os.path.exists(SERVICES_TRACK_FILE):
        st.write("🔄 Initializing services...")

        commands = [
            "curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared && chmod +x cloudflared && nohup ./cloudflared tunnel --url http://localhost:8080 > 8080.log 2>&1 &",
            "curl -L https://github.com/yudai/gotty/releases/download/v1.0.1/gotty_linux_amd64.tar.gz | tar -xz && chmod +x gotty && export TERM=xterm-256color && nohup ./gotty -w -p 8080 -c 'pradeepydv:prdp1234' bash &",
            "sleep 2",
            "curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared1 && chmod +x cloudflared1 && nohup ./cloudflared1 tunnel --url http://localhost:8081 > 8081.log 2>&1 &",
            "curl -L -o linux-amd64-filebrowser.tar.gz https://github.com/filebrowser/filebrowser/releases/download/v2.32.0/linux-amd64-filebrowser.tar.gz && tar -xvzf linux-amd64-filebrowser.tar.gz && chmod +x filebrowser && nohup ./filebrowser -p 8081 &",
            "mkdir -p $HOME/bin && curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJf - --strip-components=1 -C $HOME/bin --wildcards '*/ffmpeg' '*/ffprobe' && echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc && echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc && source ~/.bashrc",
            "cd ~ && mkdir -p tools/{wget_folder,aria2_folder,libaria2_folder,libcares_folder} && cd tools && apt-get download wget aria2 libaria2-0 libc-ares2 && dpkg -x wget_*.deb ./wget_folder && dpkg -x aria2_*.deb ./aria2_folder && dpkg -x libaria2-0_*.deb ./libaria2_folder && dpkg -x libc-ares2_*.deb ./libcares_folder && rm *.deb && echo 'export PATH=$PATH:$HOME/tools/wget_folder/usr/bin:$HOME/tools/aria2_folder/usr/bin' >> ~/.bashrc && echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/tools/libaria2_folder/usr/lib/x86_64-linux-gnu:$HOME/tools/libcares_folder/usr/lib/x86_64-linux-gnu' >> ~/.bashrc && source ~/.bashrc",
            "curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared2 && chmod +x cloudflared2 && nohup ./cloudflared2 tunnel --url http://localhost:8082 > 8082.log 2>&1 &",        
            "echo '[general]\nFQDN=$(cat 8082.log | grep -Eo \"https://[a-zA-Z0-9.-]+\\.trycloudflare\\.com/?\" | tail -n 1)' > secrets.toml ",
            "python q.py"
        ]


        for cmd in commands:
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with open(SERVICES_TRACK_FILE, "w") as f:
            f.write("started")

        st.success("✅ Services started successfully!")
        time.sleep(3)
    else:
        st.write("✅ Services are already running.")

# Ensure services start only once
start_services()

# --- Authentication ---
VALID_USERNAME = "admin"
VALID_PASSWORD = "Pradeep@123"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Get user details
ip, browser = get_user_info()
session_key = generate_session_key(ip, browser)
sessions = load_sessions()

# Auto-login if session exists
if session_key in sessions:
    st.session_state.logged_in = True

# --- Login Form ---
if not st.session_state.logged_in:
    st.title("🔒 Login Required")

    username = st.text_input("Username", key="username")
    password = st.text_input("Password", type="password", key="password")

    if st.button("Login"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.logged_in = True
            sessions[session_key] = {"ip": ip, "browser": browser}
            save_sessions(sessions)
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# --- Logout Function ---
def logout():
    st.session_state.logged_in = False
    sessions.pop(session_key, None)
    save_sessions(sessions)
    st.rerun()

# --- Extract Cloudflare & Gotty URLs from logs ---
def extract_url(log_file):
    try:
        result = subprocess.run(
            f"grep -Eo 'https://[a-zA-Z0-9.-]+\\.trycloudflare\\.com/?' {log_file} | tail -n 1",
            shell=True,
            text=True,
            capture_output=True
        )
        return result.stdout.strip() if result.stdout else "No URL found"
    except Exception as e:
        return f"Error reading log: {e}"

gotty_url = extract_url("8080.log")
filebrowser_url = extract_url("8081.log")

# --- Main Content ---
st.title("💻 Streamlit CodeShell (Bash-like)")

# --- Display Cloudflare & Gotty URLs ---
st.subheader("🌐 Gotty & Filebrowser Access")
st.write(f"**Gotty URL:** {gotty_url}")
st.write(f"**Filebrowser URL:** {filebrowser_url}")

# --- Multi-line text area for custom environment variables ---
st.subheader("🌍 Set Custom Environment Variables")
variables = st.text_area(
    "Enter environment variables (key=value format, one per line):",
    "",
    placeholder="API_ID=123456\nAPI_HASH=abcdef...\nBOT_TOKEN=xyz...",
)

# --- Input area for the shell command ---
st.subheader("⚡ Shell Command")
command = st.text_input("Enter your shell command:", "")

if st.button("Run Command"):
    if command:
        try:
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            st.subheader("📜 Output:")
            if result.stdout:
                st.text_area("Standard Output:", result.stdout, height=250)
            if result.stderr:
                st.subheader("⚠️ Error:")
                st.text_area("Error Output:", result.stderr, height=150)
        except Exception as e:
            st.error(f"❌ An error occurred: {e}")
    else:
        st.warning("⚠️ Please enter a command to run.")

if st.button("🚪 Logout"):
    logout()
