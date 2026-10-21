import subprocess
import sys

print("Running sam validate --lint...")
result = subprocess.run(
    ["sam", "validate", "--lint"],
    capture_output=True,
    text=True,
    timeout=180,
    cwd=r"C:\Users\accli\Documents\Project\policy-assistant"
)

with open("validate_results.txt", "w") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\nReturn code: {result.returncode}\n")

print(f"Return code: {result.returncode}")
print("Results saved to validate_results.txt")