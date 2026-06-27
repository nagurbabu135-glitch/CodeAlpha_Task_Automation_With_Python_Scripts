import os
from automation_scripts import move_jpgs, extract_emails, scrape_title

print("=== Testing move_jpgs ===")
# Setup dummy src and dest
src = "demo_workspace/source_jpgs"
dest = "demo_workspace/dest_jpgs"
# Ensure folders exist
os.makedirs(src, exist_ok=True)
os.makedirs(dest, exist_ok=True)
with open(os.path.join(src, "test.jpg"), "w") as f:
    f.write("test")

success, logs = move_jpgs(src, dest)
print(f"Success: {success}")
print("Logs:")
for l in logs:
    print(f"  {l}")

print("\n=== Testing extract_emails ===")
email_src = "demo_workspace/input_data/raw_text_emails.txt"
email_dest = "demo_workspace/output_data/extracted_emails.txt"
os.makedirs(os.path.dirname(email_src), exist_ok=True)
os.makedirs(os.path.dirname(email_dest), exist_ok=True)
with open(email_src, "w") as f:
    f.write("test@example.com, test2@example.com")

success, logs = extract_emails(email_src, email_dest)
print(f"Success: {success}")
print("Logs:")
for l in logs:
    print(f"  {l}")

print("\n=== Testing scrape_title ===")
url = "https://news.ycombinator.com"
title_dest = "demo_workspace/output_data/scraped_title.txt"
success, logs, title = scrape_title(url, title_dest)
print(f"Success: {success}")
print(f"Title: {title}")
print("Logs:")
for l in logs:
    print(f"  {l}")
