import os
import requests
import traceback
# pyrefly: ignore [missing-import]
import mysql.connector
from flask import Blueprint, request, jsonify, render_template, make_response, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from firebase_admin import auth

from utils import db, sendEmail, UPLOADS_DIR

main_bp = Blueprint('main', __name__)

@main_bp.route("/download/<int:ticket_id>")
def download(ticket_id):

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute(
        """
        SELECT attachment_path
        FROM tickets
        WHERE id=%s
        """,
        (ticket_id,)
    )

    ticket = cursor.fetchone()

    cursor.close()
    conn.close()

    if not ticket:
        return jsonify({"success": False, "error": "Ticket not found"}), 404

    attachment_path = ticket.get("attachment_path")
    if not attachment_path:
        return render_template('admin_dashboard.html', atext="No attachments found.")

    # Try a few candidate locations: absolute path, uploads-relative paths, basename fallback
    candidates = []
    if os.path.isabs(attachment_path):
        candidates.append(attachment_path)
    else:
        candidates.append(os.path.join(UPLOADS_DIR, attachment_path))
        candidates.append(os.path.join(UPLOADS_DIR, os.path.basename(attachment_path)))

    found_path = None
    for p in candidates:
        try:
            p_abs = os.path.abspath(p)
        except Exception:
            continue
        # Security: ensure file is inside UPLOADS_DIR
        try:
            if os.path.isfile(p_abs) and os.path.commonpath([UPLOADS_DIR, p_abs]) == UPLOADS_DIR:
                found_path = p_abs
                break
        except ValueError:
            # different drives on Windows
            continue

    # If not found yet, try a best-effort search inside uploads for filenames containing the ticket id
    if not found_path:
        try:
            for fname in os.listdir(UPLOADS_DIR):
                if str(ticket_id) in fname:
                    candidate = os.path.join(UPLOADS_DIR, fname)
                    try:
                        cand_abs = os.path.abspath(candidate)
                    except Exception:
                        continue
                    try:
                        if os.path.isfile(cand_abs) and os.path.commonpath([UPLOADS_DIR, cand_abs]) == UPLOADS_DIR:
                            found_path = cand_abs
                            break
                    except ValueError:
                        continue
        except FileNotFoundError:
            found_path = None

    if not found_path:
        return jsonify({"success": False, "error": "No attachment available for this ticket"}), 404

    # If DB didn't already contain the absolute path, persist the discovered location for future fast access
    try:
        db_conn = mysql.connector.connect(**db)
        db_cursor = db_conn.cursor(buffered=True)
        basename = os.path.basename(found_path)
        db_cursor.execute("UPDATE tickets SET attachment_path = %s, attachment_name = %s WHERE id = %s", (found_path, basename, ticket_id))
        db_conn.commit()
        db_cursor.close()
        db_conn.close()
    except Exception as e:
        # Non-fatal: log and continue to send file
        print(f"Warning: failed to update ticket attachment_path in DB: {e}")

    return send_file(found_path, as_attachment=True)


@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/login')
def login_page():
    # Only add the popup opener header where it's actually required to support the Firebase iframe!
    response = make_response(render_template('login.html'))
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    return response

@main_bp.route('/register')
def register_page():
    response = make_response(render_template('register.html'))
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    return response
    
@main_bp.route('/logout', methods=["POST","GET"])
def logout():
    response = make_response(redirect(url_for("main.home")))
    response.set_cookie("firebase_token", "", expires=0, path='/')
    return response

@main_bp.route('/verify-token', methods=['POST'])
def verify_token():
    try:
        token = request.json.get("token")
        if not token:
            return jsonify({"success": False, "error": "Token missing from payload string"}), 400

        # 1. Cryptographically verify the token with Firebase
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]
        email = decoded.get("email", "no-email@example.com")
        # Fallback cleanly if 'name' property isn't found in the token payload
        name = decoded.get("name", email.split('@')[0]) 

        # 2. Database verification check
        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # Check by UID first
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        # If not found by UID, verify if they exist under that email from a legacy registration
        if not user:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                # Link their existing profile to their Firebase UID
                cursor.execute("UPDATE users SET firebase_uid = %s WHERE email = %s", (uid, email))
                conn.commit()
                print(f"DATABASE: Linked existing email user {email} to Firebase UID {uid}")

        # If they don't exist at all, create a fresh profile row safely
        if not user:
            print(f"AUTOMATION: Creating a completely fresh profile row for {email}...")
            cursor.execute(
                "INSERT INTO users (firebase_uid, username, email, role) VALUES (%s, %s, %s, %s)",
                (uid, name, email, "user")
            )
            conn.commit()
            
        cursor.close()
        conn.close()

        # 3. Drop the Secure Session Cookie down to the client browser
        response = make_response(jsonify({"success": True}))
        response.set_cookie(
            "firebase_token",
            token,
            httponly=True,
            samesite='Lax',
            path='/',
            secure=False  # Required for testing over unsecured http://localhost
        )
        return response

    except Exception as e:
        print("\n=== CRITICAL FLASK EXCEPTION AT TOKEN VERIFICATION ===")
        traceback.print_exc()  # Check your python terminal window for this trace!
        print("========================================================\n")
        return jsonify({"success": False, "error": str(e)}), 401

@main_bp.route('/register-user', methods=["POST"])
def register_user():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "Invalid JSON payload"}), 400
        token = data.get("token")
        username = data.get("username")
        
        if not token:
            return jsonify({"success": False, "error": "Token missing"}), 400

        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]
        email = decoded.get("email", "no-email@example.com")

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(buffered=True)

        cursor.execute(
            "INSERT INTO users (firebase_uid, username, email, role) VALUES (%s, %s, %s, %s)", 
            (uid, username, email, "user")
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/dashboard')
def dashboard_page():
    token = request.cookies.get("firebase_token")

    if not token:
        # Check your console terminal! If you see this statement print, the browser is hiding your cookie.
        print("REDIRECT DEBUG: Redirecting because the firebase_token cookie was missing from the request.")
        return redirect(url_for("main.login_page"))

    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)

        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            print(f"REDIRECT DEBUG: Verified Firebase UID {uid} but couldn't find a matching record in MySQL.")
            return redirect(url_for("main.login_page"))

        if user["role"] == "admin":
            cursor.execute("SELECT * FROM tickets;")
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template("admin_dashboard.html", username=user["username"], tickets=tickets, uid=uid)
        else:
            cursor.close()
            conn.close()
            return render_template("dashboard.html", username=user["username"])
            
    except Exception as e:
        print("CRITICAL ERROR: Token processing crashed inside the dashboard route.")
        traceback.print_exc()
        return redirect(url_for("main.login_page"))

@main_bp.route("/create-ticket", methods=["POST"])
def create_ticket():
    token = request.cookies.get("firebase_token")

    if not token:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        # Handle optional file upload (safe and after auth)
        upload_name = None
        upload_path = None
        file = request.files.get("attachment")
        if file and getattr(file, 'filename', None):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOADS_DIR, exist_ok=True)
            filepath = os.path.join(UPLOADS_DIR, filename)
            file.save(filepath)
            upload_name = filename
            upload_path = filepath

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)

        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Profile error"}), 404

        title = request.form.get('title', '')
        description = request.form.get('description', '')

        cursor.execute(
            "INSERT INTO tickets (title, description, status, user_id, attachment_name, attachment_path) VALUES (%s, %s, %s, %s, %s, %s)", 
            (title, description, "Open", user["id"], upload_name, upload_path)
        )
        ticket_id = cursor.lastrowid 

        cursor.execute("SELECT * FROM users WHERE role = %s", ("admin",))
        admins = cursor.fetchall()

        body = "New ticket #%s has been created by user id %s" % (
            ticket_id,
            user["id"]
        )   

        # Using INSERT IGNORE to prevent conflicts with the after_ticket_insert MySQL trigger
        cursor.execute(
            "INSERT IGNORE INTO tickethistory (id, title, description, status, user_id) VALUES (%s, %s, %s, %s, %s)", 
            (ticket_id, title, description, "Open", user["id"])
        )
        conn.commit()

        for admin in admins:
            try:
                sendEmail(admin["email"], "New Ticket", body)
            except Exception as email_err:
                print(f"Warning: Failed to send new ticket email to {admin['email']}: {email_err}")
        
        cursor.execute("SELECT * FROM tickethistory WHERE user_id = %s", (user["id"],))
        tickets = cursor.fetchall()
        
        cursor.close()
        conn.close()

        WEBHOOK_DESTINATION_URL = "https://webhook.site/6db9f14a-0392-4bcf-bbc8-3b58e4b28ed2"
        webhook_payload = {
            "event": "ticket_created",
            "ticket_id": ticket_id,
            "title": title,
            "status": "Open"
        }
        try:
            requests.post(WEBHOOK_DESTINATION_URL, json=webhook_payload, timeout=5)
        except Exception as webhook_err:
            print(f"Webhook connection error: {webhook_err}")

        return render_template(
            "dashboard.html",
            username=user["username"],
            uid=uid,
            tickets=tickets,
            text="Ticket Created!"
        )

    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route("/create-ticket-page")
def create_ticket_page():
    token = request.cookies.get("firebase_token")
    if not token:
        return redirect(url_for("main.login_page"))

    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()    
        cursor.close()
        conn.close()

        if not user:
            return redirect(url_for("main.login_page"))

        if user["role"] == "admin":
            return render_template("admin_dashboard.html", username=user["username"])

        return render_template("create_ticket.html", utext="Tickets:")
    except Exception as e:
        print(e)
        return redirect(url_for("main.login_page"))

@main_bp.route("/view-tickets", methods=["POST", "GET"])
def view_tickets():
    token = request.cookies.get("firebase_token")
    if not token:
        return redirect(url_for("main.login_page"))

    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]
        
        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return redirect(url_for("main.login_page"))

        if user["role"] == "admin":
            cursor.execute("SELECT * FROM tickets;")
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template("admin_dashboard.html", uid=uid, tickets=tickets, username=user["username"])
        else:
            cursor.execute("SELECT * FROM tickethistory WHERE user_id = %s", (user["id"],))
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template("dashboard.html", username=user["username"], tickets=tickets, uid=uid)   
    except Exception as e:
        print(e)
        return redirect(url_for("main.login_page"))  

@main_bp.route("/api/tickets")
def api_tickets():
    token = request.cookies.get("firebase_token")
    if not token:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "User not found"}), 404

        if user["role"] == "admin":
            cursor.execute("SELECT * FROM tickets")
        else:
            cursor.execute("SELECT * FROM tickethistory WHERE user_id = %s", (user["id"],))

        tickets = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "tickets": tickets})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/update-ticket/<int:ticket_id>", methods=["POST"])
def update_ticket(ticket_id):
    token = request.cookies.get("firebase_token")
    if not token:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        # get the ticket and the ticket owner's email
        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket_row = cursor.fetchone()

        if not ticket_row:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Ticket not found"}), 404

        owner_id = ticket_row.get("user_id")
        cursor.execute("SELECT * FROM users WHERE id = %s", (owner_id,))
        owner = cursor.fetchone()

        if not owner:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Ticket owner not found"}), 404

        user_email = owner.get("email")

        if not user: 
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Account unverified"}), 404

        data = request.json
        status = data.get('status')

        if user["role"] != "admin":
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Access denied"}), 403
        else:
            cursor.execute("UPDATE tickets SET status = %s WHERE id = %s", (status, ticket_id))
            cursor.execute("UPDATE tickethistory SET status = %s WHERE id = %s", (status, ticket_id))
            
            if status == "Closed":
                cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
                body = "Your ticket #%s has been resolved." % (ticket_id,)
            elif status == "In Progress":
                body = "Your ticket #%s is being worked on." % (ticket_id,)
            else:
                body = "Your ticket #%s status is now %s." % (ticket_id, status)
            
            # Commit the status update to DB FIRST before sending email
            conn.commit()
            
            try:
                sendEmail(user_email, "Ticket Updated", body)
            except Exception as email_err:
                print(f"Warning: Failed to send ticket update email to {user_email}: {email_err}")

            cursor.close()
            conn.close()

            WEBHOOK_DESTINATION_URL = "https://webhook.site/6db9f14a-0392-4bcf-bbc8-3b58e4b28ed2"
            webhook_payload = {
                "event": "ticket_status_updated",
                "ticket_id": ticket_id,
                "new_status": status
            }
            try:
                requests.post(WEBHOOK_DESTINATION_URL, json=webhook_payload, timeout=5)
            except Exception as webhook_err:
                print(f"Webhook failure: {webhook_err}")

            return jsonify({
                "success": True, 
                "new_status": status, 
                "message": "Status updated and webhook sent!"
            })
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 500
    
@main_bp.route("/delete-ticket/<int:ticket_id>", methods=["POST"])
def delete_ticket(ticket_id):
    token = request.cookies.get("firebase_token")
    if not token:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]

        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "User missing inside DB"}), 404

        if user["role"] != "admin":
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Access denied"}), 403
        else:
            # Fetch ticket to validate and get owner email
            cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
            ticket_row = cursor.fetchone()
            if not ticket_row:
                cursor.close()
                conn.close()
                return jsonify({"success": False, "error": "Ticket not found"}), 404

            owner_id = ticket_row.get("user_id")
            owner_email = None
            if owner_id is not None:
                cursor.execute("SELECT * FROM users WHERE id = %s", (owner_id,))
                owner = cursor.fetchone()
                if owner:
                    owner_email = owner.get("email")

            # Mark history as Trashed and remove from active tickets
            cursor.execute("UPDATE tickethistory SET status = %s WHERE id = %s", ("Trashed", ticket_id))
            cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
            conn.commit()
            cursor.close()
            conn.close()

            # Send email to owner if present
            if owner_email:
                try:
                    sendEmail(owner_email, "Ticket Deleted", f"Your ticket #{ticket_id} was deleted by an admin.")
                except Exception as email_err:
                    print(f"Failed to send deletion email: {email_err}")

            WEBHOOK_DESTINATION_URL = "https://webhook.site/6db9f14a-0392-4bcf-bbc8-3b58e4b28ed2"
            webhook_payload = {
                "event": "ticket_status_updated",
                "ticket_id": ticket_id,
                "new_status": "Trashed"
            }
            try:
                requests.post(WEBHOOK_DESTINATION_URL, json=webhook_payload, timeout=5)
            except Exception as webhook_err:
                print(f"Delivery tracing drop error: {webhook_err}")

            return jsonify({
                "success": True,
                "new_status": "Trashed",
                "message": "Ticket deleted and webhook sent!"
            })
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route("/test-email")
def test_email():
    try:
        from utils import sendEmail
        sendEmail("arjunkarthik1223@gmail.com", "Vercel Email Test", "This is a test from Vercel.")
        return "SUCCESS! Email sent.", 200
    except Exception as e:
        import traceback
        return f"FAILED!<br>Error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@main_bp.route("/view-ticket-history", methods=["POST", "GET"])
def view_ticket_history():
    is_history=True
    token = request.cookies.get("firebase_token")
    if not token:
        return redirect(url_for("main.login_page"))

    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        uid = decoded["uid"]
        
        conn = mysql.connector.connect(**db)
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE firebase_uid = %s", (uid,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return redirect(url_for("main.login_page"))

        if user["role"] == "admin":
            cursor.execute("SELECT * FROM tickethistory;")
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template("admin_dashboard.html", uid=uid, tickethistory=tickets, username=user["username"])
        else:
            cursor.execute("SELECT * FROM tickethistory WHERE user_id = %s", (user["id"],))
            tickets = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template("dashboard.html", username=user["username"], tickets=tickets, uid=uid)   
    except Exception as e:
        print(e)
        return redirect(url_for("main.login_page"))

