import streamlit as st
import subprocess
import platform

# Streamlit App Title
st.title("Streamlit CodeShell (Bash-like)")

# Detect operating system
os_type = platform.system()
st.write(f"Operating System: {os_type}")

# Input area for the shell command
command = st.text_area("Enter your shell command (supports multiline):", "")

# Button to execute the command
if st.button("Run Command"):
    if command:
        try:
            # Choose the shell environment based on the OS
            if os_type == "Windows":
                # Use PowerShell for advanced commands on Windows
                shell_cmd = ["powershell.exe", "-Command", command]
            else:
                # Use Bash for Unix-like systems
                shell_cmd = ["/bin/bash", "-c", command]
            
            # Execute the command and capture the output
            result = subprocess.run(
                shell_cmd, text=True, capture_output=True
            )
            
            # Display the output
            st.subheader("Output:")
            st.text(result.stdout.strip())
            
            # Display errors if any
            if result.stderr:
                st.subheader("Error:")
                st.text(result.stderr.strip())
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a command to run.")
