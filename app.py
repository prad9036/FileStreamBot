import streamlit as st
from WebStreamer import StreamBot, web_server, ping_server, initialize_clients

def run_streaming_bot():
    # Example: Initialize the bot and run it
    bot = StreamBot()
    bot.run()
    st.success("Streaming bot is running!")

def run_web_server():
    # Example: Initialize and start the web server
    server = web_server()
    server.start()
    st.success("Web server is running!")

def check_server_status():
    # Example: Ping the server to check if it’s active
    status = ping_server().check_status()
    if status:
        st.success("Server is up and running!")
    else:
        st.error("Server is down.")

def main():
    st.title("WebStreamer Streamlit App")

    # Add Streamlit interface for different actions
    st.sidebar.header("Choose Action:")
    choice = st.sidebar.radio("Select Action", ["Start Streaming Bot", "Start Web Server", "Check Server Status"])

    if choice == "Start Streaming Bot":
        run_streaming_bot()
    elif choice == "Start Web Server":
        run_web_server()
    elif choice == "Check Server Status":
        check_server_status()

if __name__ == "__main__":
    main()
