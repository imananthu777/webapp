from flask import Flask, render_template, request, redirect, url_for, session, make_response
import pdfkit
import hashlib
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key!

USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def hash_string(text):
    return hashlib.sha256(str(text).encode()).hexdigest()

def encrypt_mobile(mobile):
    return hash_string(mobile)[:12]  # Take first 12 chars of hash for shorter id

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        mobile = request.form['mobile']
        password = request.form['password']

        users = load_users()
        encrypted_mobile = encrypt_mobile(mobile)
        if encrypted_mobile in users and users[encrypted_mobile]['password'] == hash_string(password):
            session['logged_in'] = True
            session['mobile'] = encrypted_mobile #Store encrypted mobile in session
            return redirect(url_for('welcome'))

        error = "Invalid mobile number or password. Please try again."
        return render_template('login.html', error=error)

    return render_template('login.html', error=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        password = request.form['password']
        email = request.form.get('email', '')

        users = load_users()
        encrypted_mobile = encrypt_mobile(mobile)
        if encrypted_mobile in users:
            return "Mobile number already registered!"

        users[encrypted_mobile] = {
            'password': hash_string(password),
            'name': name,
            'email': email
        }
        save_users(users)

        return redirect(url_for('home'))

    return render_template('register.html')

def load_transactions(mobile):
    try:
        with open(f'transactions_{mobile}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_transactions(mobile, transactions):
    with open(f'transactions_{mobile}.json', 'w') as f:
        json.dump(transactions, f)

@app.route('/welcome')
def welcome():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
        
    encrypted_mobile = session.get('mobile')
    users = load_users()
    user = users.get(encrypted_mobile, {})
    
    transactions = load_transactions(encrypted_mobile)
    
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    
    # Prepare chart data
    expense_categories = {}
    for t in transactions:
        if t['type'] == 'expense':
            expense_categories[t['description']] = expense_categories.get(t['description'], 0) + t['amount']
    
    chart_data = {
        'labels': list(expense_categories.keys()),
        'values': list(expense_categories.values())
    }
    
    return render_template('welcome.html',
                         name=user.get('name'),
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         chart_data=chart_data)

@app.route('/export_pdf')
def export_pdf():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
        
    encrypted_mobile = session.get('mobile')
    users = load_users()
    user = users.get(encrypted_mobile, {})
    
    transactions = load_transactions(encrypted_mobile)
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    
    html = render_template('pdf_template.html',
                         name=user.get('name'),
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses)
    
    pdf = pdfkit.from_string(html, False)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.pdf'
    return response

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
        
    encrypted_mobile = session.get('mobile')
    
    transaction = {
        'type': request.form['type'],
        'description': request.form['description'],
        'amount': float(request.form['amount']),
        'date': datetime.now().strftime('%dth %B %Y %I:%M %p') + ' IST'
    }
    
    transactions = load_transactions(encrypted_mobile)
    transactions.append(transaction)
    save_transactions(encrypted_mobile, transactions)
    
    return redirect(url_for('welcome'))

@app.route('/cancel_last')
def cancel_last():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
        
    encrypted_mobile = session.get('mobile')
    transactions = load_transactions(encrypted_mobile)
    
    if transactions:
        transactions.pop()  # Remove the last transaction
        save_transactions(encrypted_mobile, transactions)
    
    return redirect(url_for('welcome'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)