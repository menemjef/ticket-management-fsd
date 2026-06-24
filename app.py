import os
import json
from flask import Flask
import firebase_admin
from firebase_admin import credentials

startup_error = None
try:
    # Initialize Firebase before loading routes
    firebase_cred_json = os.environ.get("FIREBASE_CREDENTIALS")
    if firebase_cred_json:
        # Vercel preserves the JSON exactly, so we just parse it directly.
        # strict=False allows literal control characters just in case Vercel stripped the escapes
        cred_dict = json.loads(firebase_cred_json, strict=False)
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("firebase.json")
        
    firebase_admin.initialize_app(cred)
    
    from routes.main import main_bp
except Exception as e:
    import traceback
    startup_error = f"{str(e)}<br><pre>{traceback.format_exc()}</pre>"

from flask import Flask
app = Flask(__name__)

# If there's a startup error, hijack the root route to display it instead of crashing
if startup_error:
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return f"<h1>App Crashed on Startup</h1><p><b>Error:</b> {startup_error}</p>", 200
else:
    # Register the blueprint only if no errors
    app.register_blueprint(main_bp)

# --- FIXED: REMOVED GLOBAL COOP AFTER_REQUEST INTERCEPTOR ---
# (The global same-origin rule was severing browser contexts and killing the cookie path)

if __name__ == "__main__":
    app.run(debug=True)