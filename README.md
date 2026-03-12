## Smart Attendance System (QR & Face Recognition Demo)

This is a simple smart attendance web application built with **Python (Flask)** and **SQLite**.

- **Students** can register, log in, and mark attendance using:
  - **QR code scanning** (scan with a phone camera, then log in)
  - **Face recognition demo** (one-click, no real camera processing)
- **Admins** can:
  - Create time-limited **attendance sessions** that generate a QR code
  - View **attendance records**
  - See an **attendance matrix report** (students × sessions)

### 1. Requirements

- Python 3.10+ installed on your machine
- On Windows PowerShell, run commands from the project folder:
  `c:\Users\Rohith Roblelal\OneDrive\Desktop\protfolio\Smart Attendance System`

### 2. Setup

```bash
cd "c:\Users\Rohith Roblelal\OneDrive\Desktop\protfolio\Smart Attendance System"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the app

```bash
cd "c:\Users\Rohith Roblelal\OneDrive\Desktop\protfolio\Smart Attendance System"
.venv\Scripts\activate
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

### 4. Default admin login

- **Email**: `admin@example.com`
- **Password**: `admin123`

This user is created automatically the first time the app runs.

### 5. Usage flows

- **Student**
  1. Go to `/register`, create a student account.
  2. Log in and open the **Student Dashboard** (`/dashboard`).
  3. When the teacher shows a QR on screen, scan it with your phone camera.
  4. The link opens in the browser; log in if needed and your attendance is recorded.
  5. Alternatively, click **“Mark via Face Recognition (Demo)”** on the dashboard
     to mark attendance for the latest active session.

- **Admin**
  1. Log in with the admin account.
  2. Open the **Admin Dashboard**.
  3. Create an **attendance session** (title + duration).
  4. Open the session details and project/show the generated **QR code**.
  5. Students scan the QR to mark their attendance.
  6. Use **Attendance Records** and **Attendance Report** to review attendance.

### 6. Notes about face recognition

- The `/attend/face` endpoint and `face_attendance.html` are implemented as a **demo stub**:
  - It does **not** perform real face recognition.
  - It assumes identity is already verified (logged-in student) and simply marks
    attendance for the latest active session.
- To upgrade this to real face recognition, you can:
  - Capture a frame from the webcam on the client (JavaScript + `getUserMedia`)
  - Send the image to the backend
  - Use libraries such as `opencv-python` or `face_recognition` to compare faces

