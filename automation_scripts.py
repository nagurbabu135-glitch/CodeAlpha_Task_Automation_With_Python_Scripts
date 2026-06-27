import os
import shutil
import re
import requests

def move_jpgs(source_dir, dest_dir):
    """
    Moves all .jpg and .jpeg files from source_dir to dest_dir.
    Returns (success, logs)
    """
    logs = []
    success = False
    try:
        logs.append(f"Starting task: Move JPG files.")
        logs.append(f"Source folder: {source_dir}")
        logs.append(f"Destination folder: {dest_dir}")

        if not os.path.exists(source_dir):
            logs.append(f"Error: Source directory '{source_dir}' does not exist.")
            return False, logs

        # Normalize paths
        source_dir = os.path.abspath(source_dir)
        dest_dir = os.path.abspath(dest_dir)

        if source_dir == dest_dir:
            logs.append("Error: Source and destination directories are the same.")
            return False, logs

        # Create destination directory if it doesn't exist
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            logs.append(f"Created destination directory: {dest_dir}")

        # Scan for JPG files
        files = os.listdir(source_dir)
        jpg_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg'))]

        logs.append(f"Found {len(jpg_files)} JPG file(s) in source directory.")

        if len(jpg_files) == 0:
            logs.append("No files to move.")
            return True, logs

        moved_count = 0
        for filename in jpg_files:
            src_path = os.path.join(source_dir, filename)
            dest_path = os.path.join(dest_dir, filename)

            # Handle name collision by appending _1, _2 etc.
            final_dest_path = dest_path
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(final_dest_path):
                final_dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                counter += 1

            shutil.move(src_path, final_dest_path)
            logs.append(f"Moved: '{filename}' -> '{os.path.basename(final_dest_path)}'")
            moved_count += 1

        logs.append(f"Successfully moved {moved_count} file(s).")
        success = True
    except Exception as e:
        logs.append(f"Unexpected error: {str(e)}")
        success = False

    return success, logs

def extract_emails(source_file, dest_file):
    """
    Extracts all email addresses from source_file and saves them to dest_file.
    Returns (success, logs)
    """
    logs = []
    success = False
    try:
        logs.append(f"Starting task: Extract Email Addresses.")
        logs.append(f"Source file: {source_file}")
        logs.append(f"Destination file: {dest_file}")

        if not os.path.exists(source_file):
            logs.append(f"Error: Source file '{source_file}' does not exist.")
            return False, logs

        # Ensure destination directory exists
        dest_dir = os.path.dirname(os.path.abspath(dest_file))
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            logs.append(f"Created directory for output file: {dest_dir}")

        logs.append("Reading source file content...")
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Regular expression for email extraction
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, content)

        logs.append(f"Found {len(emails)} email address match(es) in raw content.")

        # Write to destination file
        logs.append(f"Writing emails to output file...")
        with open(dest_file, 'w', encoding='utf-8') as f:
            for email in emails:
                f.write(email + '\n')

        for idx, email in enumerate(emails[:10]):
            logs.append(f"  [{idx+1}] {email}")
        if len(emails) > 10:
            logs.append(f"  ... and {len(emails) - 10} more.")

        logs.append(f"Successfully saved emails to: {dest_file}")
        success = True
    except Exception as e:
        logs.append(f"Unexpected error: {str(e)}")
        success = False

    return success, logs

def scrape_title(url, dest_file):
    """
    Scrapes the title of webpage at url and saves it to dest_file.
    Returns (success, logs, title)
    """
    logs = []
    success = False
    title = None
    try:
        logs.append(f"Starting task: Scrape Webpage Title.")
        logs.append(f"Target URL: {url}")
        logs.append(f"Destination file: {dest_file}")

        # Basic URL format validation
        if not (url.startswith('http://') or url.startswith('https://')):
            logs.append("Invalid URL format. Appending 'https://' prefix.")
            url = 'https://' + url

        logs.append(f"Sending GET request to {url}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        logs.append(f"HTTP response code: {response.status_code}")

        if response.status_code != 200:
            logs.append(f"Error: Received non-200 status code ({response.status_code}).")
            return False, logs, None

        # Extract title using regex
        html_content = response.text
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)

        if not title_match:
            logs.append("Warning: Could not find <title> tag in the page source.")
            title = "No title found"
        else:
            title = title_match.group(1).strip()
            # Clean HTML entities if any
            title = re.sub(r'\s+', ' ', title)
            logs.append(f"Successfully extracted title: '{title}'")

        # Ensure destination directory exists
        dest_dir = os.path.dirname(os.path.abspath(dest_file))
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            logs.append(f"Created directory for output file: {dest_dir}")

        # Write to destination file
        logs.append(f"Writing title to output file...")
        with open(dest_file, 'w', encoding='utf-8') as f:
            f.write(title + '\n')

        logs.append(f"Successfully saved webpage title to: {dest_file}")
        success = True
    except requests.exceptions.RequestException as re_err:
        logs.append(f"Network error requesting page: {str(re_err)}")
        success = False
    except Exception as e:
        logs.append(f"Unexpected error: {str(e)}")
        success = False

    return success, logs, title
