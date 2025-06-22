# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import random
import time
from datetime import datetime, timedelta
from sms_sdk import SmsGatewayClient

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# SMS Gateway configuration
API_URL = "http://192.168.95.187:5001"
API_KEY = "5f427c4bc12f35af8648807151aa2742f5a98a929feebc8827162cc6885a9394"
client = SmsGatewayClient(API_URL, API_KEY)

# In-memory storage for OTPs (use database in production)
otp_storage = {}

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def is_otp_valid(phone_number):
    """Check if OTP is still valid (not expired)"""
    if phone_number not in otp_storage:
        return False
    
    otp_data = otp_storage[phone_number]
    expiry_time = otp_data['timestamp'] + timedelta(minutes=5)
    return datetime.now() < expiry_time

@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'authenticated' in session and session['authenticated']:
        return render_template('dashboard.html', phone=session.get('phone'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Phone number entry page"""
    if request.method == 'POST':
        phone_number = request.form.get('phone_number', '').strip()
        
        if not phone_number:
            flash('Please enter a valid phone number', 'error')
            return render_template('login.html')
        
        # Generate and store OTP
        otp = generate_otp()
        otp_storage[phone_number] = {
            'otp': otp,
            'timestamp': datetime.now(),
            'attempts': 0
        }
        
        # Send OTP via SMS
        try:
            message = f"{otp}"
            result = client.send_sms(phone_number, message)
            print(f"SMS sent successfully to {phone_number}. OTP: {otp}")  # For debugging
            
            # Store phone number in session
            session['phone_number'] = phone_number
            flash('OTP sent successfully! Please check your phone.', 'success')
            return redirect(url_for('verify_otp'))
            
        except Exception as e:
            print(f"Failed to send SMS: {e}")
            flash('Failed to send OTP. Please try again.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """OTP verification page"""
    phone_number = session.get('phone_number')
    
    if not phone_number:
        flash('Please enter your phone number first', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        
        if not entered_otp:
            flash('Please enter the OTP', 'error')
            return render_template('verify_otp.html', phone=phone_number)
        
        # Check if OTP exists and is valid
        if phone_number not in otp_storage:
            flash('OTP expired or invalid. Please request a new one.', 'error')
            return redirect(url_for('login'))
        
        otp_data = otp_storage[phone_number]
        
        # Check if OTP is expired
        if not is_otp_valid(phone_number):
            del otp_storage[phone_number]
            flash('OTP has expired. Please request a new one.', 'error')
            return redirect(url_for('login'))
        
        # Check attempt limit
        if otp_data['attempts'] >= 3:
            del otp_storage[phone_number]
            flash('Too many failed attempts. Please request a new OTP.', 'error')
            return redirect(url_for('login'))
        
        # Verify OTP
        if entered_otp == otp_data['otp']:
            # Successful login
            session['authenticated'] = True
            session['phone'] = phone_number
            del otp_storage[phone_number]  # Clean up
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Increment failed attempts
            otp_storage[phone_number]['attempts'] += 1
            remaining_attempts = 3 - otp_storage[phone_number]['attempts']
            flash(f'Invalid OTP. {remaining_attempts} attempts remaining.', 'error')
    
    return render_template('verify_otp.html', phone=phone_number)

@app.route('/dashboard')
def dashboard():
    """Protected dashboard page"""
    if 'authenticated' not in session or not session['authenticated']:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', phone=session.get('phone'))

@app.route('/resend-otp')
def resend_otp():
    """Resend OTP to the same phone number"""
    phone_number = session.get('phone_number')
    
    if not phone_number:
        flash('Please enter your phone number first', 'error')
        return redirect(url_for('login'))
    
    # Generate new OTP
    otp = generate_otp()
    otp_storage[phone_number] = {
        'otp': otp,
        'timestamp': datetime.now(),
        'attempts': 0
    }
    
    # Send OTP via SMS
    try:
        message = f"{otp}"
        result = client.send_sms(phone_number, message)
        print(f"SMS resent successfully to {phone_number}. OTP: {otp}")  # For debugging
        
        flash('New OTP sent successfully!', 'success')
        return redirect(url_for('verify_otp'))
        
    except Exception as e:
        print(f"Failed to resend SMS: {e}")
        flash('Failed to resend OTP. Please try again.', 'error')
        return redirect(url_for('verify_otp'))

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5003)
