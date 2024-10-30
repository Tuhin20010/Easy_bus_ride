from bson import ObjectId
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for, session
from pymongo import MongoClient
import os
from models import Bus
import bcrypt
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=5) 

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['bus_timetable']

# search suggesations

# Home Page - Display navbar, offers, and links to search/admin pages
@app.route('/')
def home():
    return render_template('home.html')

# Registration Page
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('registration'))

        # Hash the password for storage using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert user into the database
        user = {
            "name": name,
            "email": email,
            "mobile": mobile,
            "password": hashed_password.decode('utf-8')  # Store as string
        }
        db.users.insert_one(user)  # Collection name is 'users'
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))  # Redirect to login page

    return render_template('registration.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']  # Can be email or mobile
        password = request.form['password']

        user = db.users.find_one({'$or': [{'email': identifier}, {'mobile': identifier}]})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = str(user['_id'])  # Store user ID in session
            flash("Login successful!", "success")
            return redirect(url_for('admin_dashboard'))

        flash("Invalid email/mobile or password.", "error")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    session.permanent = True
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})

    # Fetch buses added by the logged-in user
    buses = db.buses.find({'user_id': user_id})  # Assuming you have 'user_id' in your bus documents
    
    # Pass user name to the template
    return render_template('admin_dashboard.html', buses=buses, user_name=user['name'])


@app.route('/logout')
def logout():
    session.pop('user', None)  # Clear the session
    return redirect(url_for('login'))  # Redirect to login after logout

# Admin Page - Add Bus
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        bus_number = request.form['bus_number']
        bus_name = request.form['bus_name']
        route = request.form.getlist('route[]')
        time = request.form.getlist('time[]')

        route_list = [{"stop": stop, "time": time[i]} for i, stop in enumerate(route)]

        # Insert the bus with the user_id
        db.buses.insert_one({
            "bus_number": bus_number,
            "bus_name": bus_name,
            "route": route_list,
            "user_id": session['user_id']  # Save the ID of the user who added the bus
        })
        flash('Bus details added successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('admin.html')

# Search Page
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        
        # Query for buses that have both source and destination in the route
        buses = db.buses.find({
            "route.stop": {"$all": [source, destination]}
        })

        results = []
        for bus in buses:
            filtered_route = filter_route(bus['route'], source, destination)
            if filtered_route:  # Only add if a valid route is found
                results.append({
                    "bus_name": bus['bus_name'],
                    "bus_number": bus['bus_number'],
                    "filtered_route": filtered_route
                })
                
        return render_template('results.html', buses=results, source=source, destination=destination)
    return render_template('search.html')

# Helper function to filter route between source and destination
def filter_route(route, source, destination):
    source_index = next((i for i, stop in enumerate(route) if stop['stop'] == source), None)
    destination_index = next((i for i, stop in enumerate(route) if stop['stop'] == destination), None)

    if source_index is not None and destination_index is not None and source_index < destination_index:
        return route[source_index:destination_index + 1]  # Subset from source to destination
    return []

# Update Bus Timetable
@app.route('/update_timetable', methods=['GET', 'POST'])
def update_timetable():
    if request.method == 'POST':
        bus_number = request.form.get('bus_number')  # Use .get() to avoid KeyError

        if bus_number:  # Check if bus_number is present
            bus = db.buses.find_one({'bus_number': bus_number})
            if bus:
                # Process the update logic here
                if request.form.get('update'):
                    new_stops = request.form.getlist('stop[]')
                    new_times = request.form.getlist('time[]')

                    # Update logic here...
                    
                return render_template('update_timetable.html', bus=bus)
            else:
                flash('This bus is not registered yet!', 'error')
                return redirect(url_for('update_timetable'))  # Redirect back to the update page
        else:
            flash('Bus number is required!', 'error')
            return redirect(url_for('update_timetable'))  # Redirect back to the update page

    return render_template('update_timetable.html')

# Update Profile
@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})

    if request.method == 'POST':
        # Get the updated profile details from the form
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']

        # Update the user's profile in the database
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'name': name,
                'email': email,
                'mobile': mobile
            }}
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard after update

    return render_template('update_profile.html', user=user)


if __name__ == '__main__':
    app.run(debug=True)
