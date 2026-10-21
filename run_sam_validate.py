import subprocess
import sys
import os

os.chdir(r"C:\Users\accli\Documents\Project\policy-assistant")

print("Running sam validate --lint...")
try:
    result = subprocess.run(
        ["powershell", "-Command", "sam validate --lint"],
        capture_output=True,
        text=True,
        timeout=180
    )
    with open("validate_results.txt", "w") as f:
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\nReturn code: {result.returncode}\n")
    print(f"Return code: {result.returncode}")
except subprocess.TimeoutExpired:
    with open("validate_results.txt", "w") as f:
        f.write("TIMEOUT\n")
    print("TIMEOUT")
except Exception as e:
    with open("validate_results.txt", "w") as f:
        f.write(f"ERROR: {e}\n")
    print(f"ERROR: {e}")