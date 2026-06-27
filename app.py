import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from automation_scripts import move_jpgs, extract_emails, scrape_title

app = Flask(__name__, template_folder='templates', static_folder='static')

# Secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-key-for-autopy-playground')

# ==========================================================================
# In-Memory Database Fallback Mock Classes (For offline / Vercel usage)
# ==========================================================================
class MockCollection:
    def __init__(self):
        self.data = []
        
    def find_one(self, query):
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return item
        return None
        
    def insert_one(self, doc):
        self.data.append(doc)
        return doc
        
    def find(self, query=None):
        if not query:
            return self.data
        results = []
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                results.append(item)
        return MockCursor(results)

    def create_index(self, *args, **kwargs):
        pass

class MockCursor:
    def __init__(self, data):
        self.data = data
        
    def sort(self, key, direction=1):
        # Sort by timestamp descending
        if key == "timestamp" or key == "timestamp":
            self.data.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=(direction == -1))
        return self
        
    def limit(self, num):
        self.data = self.data[:num]
        return self
        
    def __iter__(self):
        return iter(self.data)

# MongoDB Connection Initialization
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
mongo_connected = False
users_col = None
history_col = None

try:
    # Set timeout to 2000ms so it doesn't block server startup indefinitely if MongoDB is offline
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    # Trigger a connection check
    mongo_client.server_info()
    db = mongo_client['autopy_db']
    users_col = db['users']
    history_col = db['execution_history']
    
    # Ensure indexes for uniqueness and fast queries
    users_col.create_index("username", unique=True)
    history_col.create_index([("username", 1), ("timestamp", -1)])
    
    mongo_connected = True
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Warning: Could not connect to MongoDB: {str(e)}")
    print("Falling back to In-Memory Database Mode.")
    users_col = MockCollection()
    history_col = MockCollection()
    mongo_connected = False

@app.route('/')
def index():
    return render_template('index.html')

# Authentication API Routes

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400
        
    if len(username) < 3:
        return jsonify({"success": False, "error": "Username must be at least 3 characters long."}), 400
        
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400
        
    try:
        # Check if username exists
        if users_col.find_one({"username": username}):
            return jsonify({"success": False, "error": "Username already exists."}), 400
            
        password_hash = generate_password_hash(password)
        users_col.insert_one({
            "username": username,
            "password_hash": password_hash,
            "created_at": datetime.utcnow()
        })
        return jsonify({"success": True, "message": "Registration successful! You can now log in."})
    except Exception as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400
        
    try:
        user = users_col.find_one({"username": username})
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"success": False, "error": "Invalid username or password."}), 400
            
        session['username'] = username
        return jsonify({"success": True, "message": f"Welcome back, {username}!"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route('/api/user-status', methods=['GET'])
def user_status():
    username = session.get('username')
    return jsonify({
        "authenticated": username is not None,
        "username": username,
        "db_connected": mongo_connected
    })

# Demo Workspace Route (Requires Authentication)

@app.route('/api/setup-demo', methods=['POST'])
def setup_demo():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "error": "Unauthorized. Please log in first."}), 401
        
    logs = []
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        demo_dir = os.path.join(base_dir, 'demo_workspace')
        
        # 1. Create structure
        source_jpg_dir = os.path.join(demo_dir, 'source_jpgs')
        dest_jpg_dir = os.path.join(demo_dir, 'dest_jpgs')
        input_data_dir = os.path.join(demo_dir, 'input_data')
        output_data_dir = os.path.join(demo_dir, 'output_data')
        
        for folder in [source_jpg_dir, dest_jpg_dir, input_data_dir, output_data_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)
                logs.append(f"Created folder: {os.path.relpath(folder, base_dir)}")
            else:
                logs.append(f"Folder already exists: {os.path.relpath(folder, base_dir)}")

        # 2. Create dummy JPG/non-JPG files in source
        dummy_jpgs = [
            ("sunset.jpg", "Dummy sunset image data"),
            ("avatar.jpeg", "Dummy avatar image data"),
            ("banner.JPG", "Dummy banner image data"),
            ("notes.txt", "This is a text file. It should NOT be moved."),
            ("report.pdf", "This is a PDF file. It should NOT be moved.")
        ]
        
        for filename, content in dummy_jpgs:
            file_path = os.path.join(source_jpg_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logs.append(f"Created demo source file: source_jpgs/{filename}")

        # 3. Create dummy text file with email addresses
        emails_file_path = os.path.join(input_data_dir, 'raw_text_emails.txt')
        dummy_emails_content = """
========================================
Welcome to the Task Automation Demo!
========================================
This is a sample document that contains various text content along with email addresses.
The python script will search for email patterns using Regular Expressions (re) and extract them.

Support Team:
- Primary: support.team@service-provider.com
- Backup: backup_support@service-provider.com

Developer Contacts:
- John Doe (Lead): john.doe@company.org
- Jane Smith (UX): jane_smith@designhouse.co.uk
- Invalid email test: invalid-email@notadomain (should not match if we require 2+ char TLD)
- Another invalid: @no-username.com
- Another invalid: validusername@.com

Duplicate email test:
- John Doe again: john.doe@company.org (will be deduplicated)
- Primary support again: support.team@service-provider.com (will be deduplicated)

Marketing:
- info@marketing-pros.net
- newsletter@marketing-pros.net
        """
        with open(emails_file_path, 'w', encoding='utf-8') as f:
            f.write(dummy_emails_content.strip())
        logs.append("Created demo email source file: input_data/raw_text_emails.txt")

        # Return details
        return jsonify({
            "success": True,
            "message": "Demo workspace successfully set up!",
            "logs": logs,
            "paths": {
                "source_jpg_dir": source_jpg_dir,
                "dest_jpg_dir": dest_jpg_dir,
                "emails_input_file": emails_file_path,
                "emails_output_file": os.path.join(output_data_dir, 'extracted_emails.txt'),
                "scraper_output_file": os.path.join(output_data_dir, 'scraped_title.txt')
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "logs": [f"Error setting up demo: {str(e)}"]
        }), 500

# Task Execution Route (Requires Authentication)

@app.route('/api/run-task', methods=['POST'])
def run_task():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "error": "Unauthorized. Please log in first."}), 401
        
    data = request.json or {}
    task_name = data.get('task')
    params = data.get('params', {})

    if not task_name:
        return jsonify({"success": False, "error": "No task specified"}), 400

    success = False
    logs = []
    result_data = None

    if task_name == 'move_jpgs':
        source_dir = params.get('source_dir')
        dest_dir = params.get('dest_dir')
        if not source_dir or not dest_dir:
            return jsonify({"success": False, "error": "Missing source_dir or dest_dir parameters"}), 400
        success, logs = move_jpgs(source_dir, dest_dir)

    elif task_name == 'extract_emails':
        source_file = params.get('source_file')
        dest_file = params.get('dest_file')
        if not source_file or not dest_file:
            return jsonify({"success": False, "error": "Missing source_file or dest_file parameters"}), 400
        success, logs = extract_emails(source_file, dest_file)

    elif task_name == 'scrape_title':
        url = params.get('url')
        dest_file = params.get('dest_file')
        if not url or not dest_file:
            return jsonify({"success": False, "error": "Missing url or dest_file parameters"}), 400
        success, logs, title = scrape_title(url, dest_file)
        result_data = {"title": title}

    else:
        return jsonify({"success": False, "error": f"Unknown task: '{task_name}'"}), 400

    # Save execution logs and details to database/mock collection
    if username:
        try:
            history_col.insert_one({
                "username": username,
                "task": task_name,
                "params": params,
                "success": success,
                "logs": logs,
                "timestamp": datetime.utcnow()
            })
        except Exception as err:
            print(f"Failed to record run history: {str(err)}")

    response_payload = {"success": success, "logs": logs}
    if result_data:
        response_payload.update(result_data)

    return jsonify(response_payload)

# Execution History Route (Requires Authentication)

@app.route('/api/history', methods=['GET'])
def get_history():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "error": "Unauthorized. Please log in first."}), 401
        
    try:
        runs = list(history_col.find({"username": username}).sort("timestamp", -1).limit(50))
        
        serialized_runs = []
        for r in runs:
            serialized_runs.append({
                "id": str(r.get('_id', id(r))),
                "task": r.get('task'),
                "params": r.get('params'),
                "success": r.get('success'),
                "logs": r.get('logs', []),
                "timestamp": r.get('timestamp').strftime('%Y-%m-%d %H:%M:%S') if r.get('timestamp') else None
            })
        return jsonify({"success": True, "history": serialized_runs})
    except Exception as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
