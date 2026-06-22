from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'nigerian_school_attendance_key'

def get_db():
    # If running on Vercel, build/connect to an isolated memory block
    if os.environ.get('VERCEL'):
        conn = sqlite3.connect(':memory:')
    else:
        conn = sqlite3.connect('database.db')
        
    conn.row_factory = sqlite3.Row
    
    # Run structural schema generation immediately on every connection call
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Students (
        admission_no TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        class_arm TEXT NOT NULL,
        fingerprint_id TEXT UNIQUE NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_no TEXT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (admission_no) REFERENCES Students(admission_no)
    )''')
    
    # Always seed operational defaults so they exist across stateless instances
    cursor.execute("INSERT OR IGNORE INTO Users (username, password, role) VALUES ('teacher', 'school123', 'Form Teacher')")
    
    # Check if empty before running heavy seeding batches (crucial for local storage persistence)
    check_students = cursor.execute("SELECT COUNT(*) FROM Students").fetchone()[0]
    if check_students == 0:
        large_student_batch = [
            ('ADM/2026/001', 'Abubakar Aliyu', 'JSS 1 Gold', 'FP-001'),
            ('ADM/2026/002', 'Adebayo Olusegun', 'JSS 2 Blue', 'FP-002'),
            ('ADM/2026/003', 'Chinedu Okafor', 'JSS 3 Silver', 'FP-003'),
            ('ADM/2026/004', 'Chioma Nwachukwu', 'SSS 1 Science', 'FP-004'),
            ('ADM/2026/005', 'Emeka Nwosu', 'SSS 1 Commercial', 'FP-005'),
            ('ADM/2026/006', 'Fatima Ibrahim', 'SSS 2 Arts', 'FP-006'),
            ('ADM/2026/007', 'Funmi Balogun', 'SSS 2 Science B', 'FP-007'),
            ('ADM/2026/008', 'Ibrahim Musa', 'SSS 3 Science A', 'FP-008'),
            ('ADM/2026/009', 'Ngozi Ezekwesili', 'SSS 3 Arts', 'FP-009'),
            ('ADM/2026/010', 'Oluwaseun Ajayi', 'SSS 3 Commercial A', 'FP-010'),
            ('ADM/2026/011', 'Tunde Bakare', 'JSS 1 Green', 'FP-011'),
            ('ADM/2026/012', 'Yusuf Garba', 'JSS 2 Gold', 'FP-012'),
            ('ADM/2026/013', 'Zainab Bello', 'JSS 3 Blue', 'FP-013'),
            ('ADM/2026/014', 'Amara Okoye', 'SSS 1 Science', 'FP-014'),
            ('ADM/2026/015', 'Bola Tinubu', 'SSS 2 Commercial', 'FP-015'),
            ('ADM/2026/016', 'Damilola Adeyemi', 'SSS 2 Arts', 'FP-016'),
            ('ADM/2026/017', 'Efe Omonigho', 'SSS 3 Science B', 'FP-017'),
            ('ADM/2026/018', 'Kemi Adeosun', 'SSS 3 Science A', 'FP-018'),
            ('ADM/2026/019', 'Mustapha Umar', 'SSS 3 Arts', 'FP-019'),
            ('ADM/2026/020', 'Olumide Popoola', 'SSS 3 Commercial B', 'FP-020'),
        ]
        cursor.executemany("INSERT OR IGNORE INTO Students VALUES (?, ?, ?, ?)", large_student_batch)
    
    conn.commit()
    return conn

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Teacher Portal Password!', 'danger')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'register':
            adm_no = request.form['admission_no']
            name = request.form['name']
            class_arm = request.form['class_arm']
            f_id = request.form['fingerprint_id']
            try:
                conn.execute('INSERT INTO Students VALUES (?, ?, ?, ?)', (adm_no, name, class_arm, f_id))
                conn.commit()
                flash(f'Student {name} successfully added to register.', 'success')
            except sqlite3.IntegrityError:
                flash('Error: Admission Number or Fingerprint ID already exists!', 'danger')
                
        elif action == 'attend':
            f_id = request.form['scanned_fingerprint_id']
            student = conn.execute('SELECT * FROM Students WHERE fingerprint_id = ?', (f_id,)).fetchone()
            
            if student:
                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%I:%M %p")
                
                already_marked = conn.execute('SELECT * FROM Attendance WHERE admission_no = ? AND date = ?', 
                                             (student['admission_no'], date_str)).fetchone()
                if not already_marked:
                    conn.execute('INSERT INTO Attendance (admission_no, date, time, status) VALUES (?, ?, ?, ?)',
                                 (student['admission_no'], date_str, time_str, 'Present'))
                    conn.commit()
                    flash(f'Biometric Match Confirmed! {student["name"]} marked PRESENT.', 'success')
                else:
                    flash(f'{student["name"]} is already marked present for today.', 'warning')
            else:
                flash('Biometric Match Failed: Fingerprint unverified!', 'danger')

    students_list = conn.execute('SELECT * FROM Students ORDER BY name ASC').fetchall()
    date_today = datetime.now().strftime("%Y-%m-%d")
    present_today = [row['admission_no'] for row in conn.execute('SELECT admission_no FROM Attendance WHERE date = ?', (date_today,)).fetchall()]
    
    conn.close()
    return render_template('dashboard.html', students=students_list, present_today=present_today)

@app.route('/report')
def report():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    date_today = datetime.now().strftime("%Y-%m-%d")
    
    all_students = conn.execute('SELECT * FROM Students ORDER BY name ASC').fetchall()
    attendance_today = conn.execute('SELECT * FROM Attendance WHERE date = ?', (date_today,)).fetchall()
    present_map = {row['admission_no']: row['time'] for row in attendance_today}
    
    full_report_ledger = []
    for student in all_students:
        adm_no = student['admission_no']
        if adm_no in present_map:
            status = 'Present'
            time_logged = present_map[adm_no]
        else:
            status = 'Absent'
            time_logged = '-- : --'
            
        full_report_ledger.append({
            'admission_no': adm_no,
            'name': student['name'],
            'class_arm': student['class_arm'],
            'date': date_today,
            'time': time_logged,
            'status': status
        })
        
    conn.close()
    return render_template('report.html', logs=full_report_ledger, date_today=date_today)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)