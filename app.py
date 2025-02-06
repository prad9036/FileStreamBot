import streamlit as st
import subprocess
import platform
import os
# Streamlit App Title
st.title("Streamlit CodeShell (Bash-like)")

# Detect operating system
os_type = platform.system()

# Display the operating system
st.write(f"Operating System: {os_type}")

# Multi-line text area for variables
st.subheader("Environment Variables")
variables = st.text_area(
    "Enter your environment variables here (key=value format, one per line):",
    "",
    placeholder="API_ID=123456\nAPI_HASH=abcdef...\nBOT_TOKEN=xyz...",
)

# Input area for the shell command
st.subheader("Shell Command")
command = st.text_input("Enter your shell command:", "")

# Button to execute the command
if st.button("Run Command"):
    if command:
        try:
            # Parse and set environment variables from input
            env_vars = {}
            for line in variables.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

            # Execute the shell command with environment variables
            result = subprocess.run(
                command,
                shell=True,  # Use shell=True for compatibility
                text=True,
                capture_output=True,
                env={**env_vars, **os.environ},  # Combine custom vars with system env
            )

            # Display the output
            st.subheader("Output:")
            st.text(result.stdout)

            # Display errors if any
            if result.stderr:
                st.subheader("Error:")
                st.text(result.stderr)
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a command to run.")
