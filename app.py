# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
import os
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/your_database'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'

client = MongoClient(app.config['MONGO_URI'])
db = client.get_default_database()

login_manager = LoginManager(app)
login_manager.login_view = 'login'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            login_user(User(user))
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        existing_user = db.users.find_one({'$or': [{'username': username}, {'email': email}]})
        if existing_user:
            flash('Username or email already exists')
        else:
            hashed_password = generate_password_hash(password)
            db.users.insert_one({'username': username, 'email': email, 'password': hashed_password})
            flash('Account created successfully')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = db.users.find_one({'email': email})
        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Password Reset Request',
                          sender='your_email@gmail.com',
                          recipients=[email])
            msg.body = f'Click the following link to reset your password: {reset_url}'
            mail.send(msg)
            flash('Password reset instructions sent to your email')
        else:
            flash('Email not found')
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('The password reset link is invalid or has expired')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['password']
        hashed_password = generate_password_hash(new_password)
        db.users.update_one({'email': email}, {'$set': {'password': hashed_password}})
        flash('Your password has been updated')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/add_contact', methods=['GET', 'POST'])
@login_required
def add_contact():
    if request.method == 'POST':
        contact = {
            'user_id': current_user.id,
            'mobile': request.form['mobile'],
            'email': request.form['email'],
            'address': request.form['address'],
            'registration_number': request.form['registration_number']
        }
        db.contacts.insert_one(contact)
        flash('Contact added successfully')
        return redirect(url_for('dashboard'))
    return render_template('add_contact.html')

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        registration_number = request.form['registration_number']
        contact = db.contacts.find_one({'user_id': current_user.id, 'registration_number': registration_number})
        return render_template('search_results.html', contact=contact)
    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True)