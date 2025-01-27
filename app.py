import streamlit as st
import os
from dotenv import load_dotenv
from WebStreamer import WebStreamer  # Adjust this import based on how WebStreamer is structured

# Load environment variables (if needed)
load_dotenv()

# Streamlit app UI setup
st.title("My Streamlit WebStreamer App")
st.write("This app runs WebStreamer in the background!")

# Button to trigger WebStreamer
if st.button('Run WebStreamer'):
    # Call the WebStreamer (ensure it's set up to run from this file)
    WebStreamer.run()  # Adjust based on how the WebStreamer module is set up

st.write("More information or status can be shown here.")
