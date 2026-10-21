import re

with open('docs/FCAJ_FINAL_READINESS_AUDIT.md', 'r') as f:
    content = f.read()

# Pattern to match table rows with requirement ID and status
pattern = r'\|\s*([A-Z0-9\-\.]+)\s*\|\s*([^|]+)\s*\|\s*(✅\s*COMPLETE|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*NOT\s+VERIFIED|✅\s*COMPLETE|✅\s*PASS|⚠️\s*NOT\s+VERIFIED|❌\s*MISSING|✅\s*EXISTS|✅\s*PASS)\s*\|'

matches = re.findall(r'\|\s*([A-Z0-9\-\.]+)\s*\|\s*([^|]+)\s*\|\s*(✅\s*COMPLETE|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*NOT\s+VERIFIED|✅\s*COMPLETE|✅\s*PASS|⚠️\s*NOT\s+VERIFIED|❌\s*MISSING|✅\s*EXISTS|✅\s*PASS)\s*\|', content)

print(f"Total requirement rows: {len(matches)}")

status_counts = {}
req_ids = set()
for req_id, desc, status in re.findall(r'\|\s*([A-Z0-9\-\.]+)\s*\|\s*([^|]+)\s*\|\s*(✅\s*COMPLETE|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*NOT\s+VERIFIED|✅\s*COMPLETE|✅\s*PASS|⚠️\s*NOT\s+VERIFIED|❌\s*MISSING|✅\s*EXISTS|✅\s*PASS)\s*\|', content):
    status = status.strip()
    req_id = req_id.strip()
    print(f"  {req_id}: {status}")

print(f"\nTotal rows: {len(matches)}")

# Count unique requirement IDs
req_ids = set()
for req_id, desc, status in re.findall(r'\|\s*([A-Z0-9\-\.]+)\s*\|\s*([^|]+)\s*\|\s*(✅\s*COMPLETE|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*NOT\s+VERIFIED|✅\s*COMPLETE|✅\s*PASS|⚠️\s*NOT\s+VERIFIED|❌\s*MISSING|✅\s*EXISTS|✅\s*PASS)\s*\|', content):
    req_ids.add(req_id.strip())

print(f"Unique requirement IDs: {len(req_ids)}")
for rid in sorted(req_ids):
    print(f"  {rid}")

# Count by status
status_counts = {}
for req_id, desc, status in re.findall(r'\|\s*([A-Z0-9\-\.]+)\s*\|\s*([^|]+)\s*\|\s*(✅\s*COMPLETE|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*PARTIAL|❌\s*MISSING|⚠️\s*NOT\s+VERIFIED|✅\s*COMPLETE|✅\s*PASS|⚠️\s*NOT\s+VERIFIED|❌\s*MISSING|✅\s*EXISTS|✅\s*PASS)\s*\|', content):
    status = status.strip()
    print(f"  {status}: {status_counts.get(status, 0) + 1}")

print("\nDone")