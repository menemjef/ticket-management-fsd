# Ticket Management System

This is a Flask-based Ticket Management System using Firebase for Authentication and MySQL for the database. 

To run this application locally or deploy it to a server, you must set up your own Database, Email sender, and Firebase project. Follow the guide below to set up your environment.

---

## 1. Database Setup
This project uses MySQL. You will need a MySQL server running locally or hosted on the cloud (e.g., Aiven, Clever Cloud).

1. Ensure your MySQL server is running.
2. The application uses an initialization script to automatically build tables and dummy data. 
3. Run `python init_db.py` to create the required tables (`users`, `tickets`, `tickethistory`).

---

## 2. Gmail & App Password Setup (For Email Notifications)
The system sends automatic email updates when a ticket is created or updated. To enable this, you must provide a Gmail account and a secure App Password.

### How to get an App Password:
1. **Create/Log in to a Gmail account**: It is recommended to create a dedicated Gmail account for your app (e.g., `your-app-name-noreply@gmail.com`).
2. **Turn on 2-Step Verification**: Go to your [Google Account Security Settings](https://myaccount.google.com/security) and enable 2-Step Verification.
3. **Generate App Password**: 
   - Once 2-Step Verification is on, search for "App passwords" in the Security settings search bar.
   - Enter a name for the app (e.g., "Ticket System") and click **Create**.
   - Google will generate a 16-character password (e.g., `abcd efgh ijkl mnop`). **Save this password!** You will need it later.

---

## 3. Firebase Setup (Authentication)
This application uses Firebase for user authentication (Login/Register via Email & Google).

### Step 3a: Create a Firebase Project
1. Go to the [Firebase Console](https://console.firebase.google.com/) and create a new project.
2. Go to **Build -> Authentication**, click **Get Started**, and enable:
   - **Email/Password**
   - **Google** (You will need to provide a support email).

### Step 3b: Get the Admin SDK (firebase.json)
The Python backend needs Admin privileges to verify login tokens securely.
1. In the Firebase Console, click the **Gear Icon (Project Settings)** -> **Service Accounts**.
2. Make sure "Node.js" or "Python" is selected, and click **Generate new private key**.
3. A `.json` file will download. 
   - **For local development:** Rename this file to `firebase.json` and place it in the root folder of this project.
   - **For deployment:** Copy the *entire contents* of this file and paste it into the `FIREBASE_CREDENTIALS` environment variable on your hosting platform.

---

## 4. Environment Variables
To keep your sensitive data secure, this app uses Environment Variables. You must set these up in your deployment platform (like Render or Heroku). For local testing, the app has fallback defaults in the code, but using a `.env` file is highly recommended.

**Required Environment Variables:**
*   `APP_EMAIL`: The Gmail address you created in Step 2.
*   `APP_PASSWORD`: The 16-character App Password from Step 2.
*   `DB_HOST`: Your MySQL host URL (e.g., `localhost` or a cloud URL).
*   `DB_USER`: Your MySQL username (e.g., `root`).
*   `DB_PASSWORD`: Your MySQL password.
*   `DB_NAME`: Your MySQL database name (e.g., `internship_db`).
*   `DB_PORT`: The MySQL port (usually `3306`).
*   `FIREBASE_CREDENTIALS`: (Production Only) The full JSON string from your `firebase.json` file.

---

## 5. Running the Application Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Make sure your `firebase.json` is in the root directory.
3. Initialize the database (only needed once):
   ```bash
   python init_db.py
   ```
4. Start the server:
   ```bash
   python app.py
   ```
