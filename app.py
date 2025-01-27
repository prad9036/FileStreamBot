import streamlit as st
import subprocess
import sys

def run_webstreamer():
    try:
        # Run `python -m WebStreamer` as a subprocess
        result = subprocess.run([sys.executable, "-m", "WebStreamer"], capture_output=True, text=True)
        
        # Output the result to the Streamlit interface
        if result.returncode == 0:
            st.success("WebStreamer started successfully!")
            st.text(result.stdout)  # Show the standard output of the command
        else:
            st.error("Error running WebStreamer.")
            st.text(result.stderr)  # Show the error output
    except Exception as e:
        st.error(f"An error occurred: {e}")

def main():
    st.title("Run WebStreamer")

    if st.button("Start WebStreamer"):
        run_webstreamer()

if __name__ == "__main__":
    main()
