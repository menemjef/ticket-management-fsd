import os
import json
from flask import Flask
import firebase_admin
from firebase_admin import credentials

# Initialize Firebase before loading routes
firebase_cred_json = os.environ.get("FIREBASE_CREDENTIALS")
if firebase_cred_json:
    cred_dict = json.loads(firebase_cred_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("firebase.json")
    
firebase_admin.initialize_app(cred)

from routes.main import main_bp

app = Flask(__name__)

# Register the blueprint
app.register_blueprint(main_bp)

# --- FIXED: REMOVED GLOBAL COOP AFTER_REQUEST INTERCEPTOR ---
# (The global same-origin rule was severing browser contexts and killing the cookie path)

if __name__ == "__main__":
    app.run(debug=True)