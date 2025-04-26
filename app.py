from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit, join_room, leave_room # Import leave_room if needed later
from database import validate, register_user
from chat_database import get_friends, get_chats, get_user_id_by_email, get_name, get_chat_id, send_message

app = Flask(__name__)
# Make sure secret key is strong and ideally from env var
app.secret_key = 'your_super_secret_key_please_change_me'
socketio = SocketIO(app)

# --- User Session Management ---
# Helper to check if user is logged in
def is_logged_in():
    return 'user_id' in session

@app.before_request
def check_login_except_for_auth_routes():
    # Redirect to login if not logged in and not accessing login/signup
    if not is_logged_in() and request.endpoint not in ['login', 'sign_up', 'static']:
        return redirect(url_for('login'))

# --- Routes ---

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        # Add validation here (e.g., check if fields are empty, email format, password strength)
        success = register_user(f_name, l_name, email, password)
        if success:
            flash("Account created successfully! Please log in.", 'success')
            return redirect(url_for('login'))
        else:
            # Assuming register_user returns False on failure (e.g., email exists)
            flash("Registration failed. Email might already be in use.", 'danger')
            return render_template('signup.html') # Stay on signup page
    return render_template('signup.html')

@app.route('/loadchat/<int:friend_id>', methods=['GET']) # Use GET for loading data typically
def load_messages(friend_id):
    # Check login status (already handled by before_request, but good practice)
    if not is_logged_in():
        return redirect(url_for('login'))

    user_id = session['user_id']
    session['friend_id'] = friend_id # Store current friend context in session

    friends = get_friends(user_id)
    messages = get_chats(user_id, friend_id)
    name = "Unknown User" # Default name
    for friend in friends:
        if friend.get('friend_id') == friend_id:
            name = f"{friend.get('first_name', '')} {friend.get('last_name', '')}".strip()
            break

    # *** IMPORTANT: Calculate chat_id here ***
    chat_id = get_chat_id(user_id, friend_id)
    if chat_id is None:
        # Handle case where chat doesn't exist (maybe create it?)
        # For now, flash a message or handle appropriately
        flash("Could not determine chat ID.", "warning")
        # Decide where to redirect, maybe back to a default state?
        # return redirect(url_for('show_chats')) # Assuming you have a route to show just the list

    # *** Pass chat_id and friend_id explicitly to the template for JS ***
    return render_template('chat.html',
                           friends=friends,
                           having_friends=len(friends) > 0,
                           messages=messages,
                           name=name,
                           current_chat_id=chat_id, # Pass chat_id
                           current_friend_id=friend_id # Pass friend_id clearly
                          )

@app.route('/logout')
def logout():
    session.clear() # Clear all session data
    flash("You have been logged out.", 'info')
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def login():
    if is_logged_in(): # If already logged in, redirect to chat or dashboard
         user_id = session['user_id']
         friends = get_friends(user_id)
         if friends:
             # Maybe redirect to the first friend's chat or a general chat view
             # For simplicity, let's reload the chat template without a specific friend selected yet
              return render_template('chat.html', friends=friends, user_id=user_id, name="Select a Chat", messages=[], current_chat_id=None, current_friend_id=None)
         else:
              return render_template('add_new_friends.html', user_id=user_id)


    if request.method == 'POST':
        # Simplified login/signup logic
        if 'Sign_in' in request.form:
            email = request.form.get('email')
            password = request.form.get('password')
            if validate(email, password):
                user_id = get_user_id_by_email(email)
                session['user_id'] = user_id
                session['user_name'] = get_name(user_id=user_id) # Assuming get_name gets the full name
                session['username'] = email # Keep email if needed elsewhere

                # Redirect to chat view after successful login
                friends = get_friends(user_id)
                if friends:
                    # Redirect to a general chat view state initially
                    return render_template('chat.html', friends=friends, user_id=user_id, name="Select a Chat", messages=[], current_chat_id=None, current_friend_id=None)
                else:
                    return render_template('add_new_friends.html', user_id=user_id)
            else:
                flash("Invalid login credentials. Please try again.", 'danger')
                return render_template('login.html', Invalid=True) # Pass flag if needed by template
        elif 'sign-up' in request.form:
             # This button likely submits the form, handle signup logic if needed
             # Or redirect if it's just a link
             return redirect(url_for('sign_up')) # Assuming it's a redirect button

    # Default: Show login page if GET request or failed POST
    return render_template('login.html')

# --- SocketIO Events ---

@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    if user_id:
        print(f"Client connected: {request.sid}, User ID: {user_id}")
        # You could potentially join a user-specific room here if needed
        # join_room(f'user_{user_id}')
    else:
        print(f"Client connected: {request.sid}, but User ID not found in session.")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    # You might want to handle leaving rooms here if necessary

@socketio.on('join')
def on_join(data):
    """Client requests to join a room."""
    user_id = session.get('user_id')
    if not user_id:
        print("Join attempt failed: No user ID in session.")
        return # Or emit an error back to client

    room = data.get('room')
    if room:
        join_room(room)
        print(f"User {user_id} (SID: {request.sid}) joined room: {room}")
        # Optionally emit a confirmation back to the client
        # emit('joined_room', {'room': room}, room=request.sid)
    else:
        print(f"User {user_id} (SID: {request.sid}) attempted to join without specifying a room.")


@socketio.on('leave') # Optional: If you want clients to explicitly leave
def on_leave(data):
    """Client requests to leave a room."""
    user_id = session.get('user_id')
    room = data.get('room')
    if room and user_id:
        leave_room(room)
        print(f"User {user_id} (SID: {request.sid}) left room: {room}")

@socketio.on('send_message')
def handle_send_message(data):
    """Handles receiving a message from a client and broadcasting it."""
    user_id = session.get('user_id')
    if not user_id:
        print("Message send failed: No user ID in session.")
        # emit('error', {'message': 'Authentication required'}, room=request.sid)
        return

    friend_id_str = data.get('friend_id') # Comes from client JS
    message_content = data.get('content')

    if not friend_id_str or not message_content:
        print(f"Message send failed: Missing friend_id or content from user {user_id}.")
        # emit('error', {'message': 'Invalid message format'}, room=request.sid)
        return

    try:
        friend_id = int(friend_id_str)
    except ValueError:
        print(f"Message send failed: Invalid friend_id format '{friend_id_str}' from user {user_id}.")
        return

    chat_id = get_chat_id(user_id, friend_id)
    if chat_id is None:
        print(f"Message send failed: Could not find chat_id between user {user_id} and friend {friend_id}.")
        # emit('error', {'message': 'Chat room not found'}, room=request.sid)
        return

    # 1. Save message to database (use the correct variable names)
    message_saved = send_message(sender_id=user_id, chat_id=chat_id, content=message_content)

    if message_saved:
        # 2. Prepare data for emission (use keys the client expects)
        message_data_to_emit = {
            'content': message_content,
            'sender_id': user_id,
            'recipient_id': friend_id, # The friend is the recipient in this context
            'chat_id': chat_id # Optionally include chat_id if needed on client
            # 'timestamp': get_current_timestamp() # Add timestamp if desired
        }

        # 3. Determine the room name
        room_name = f'chat_{chat_id}'

        # 4. Emit the message *only* to the specific chat room
        # Use `to=room_name` or `room=room_name`
        print(f"Emitting message to room {room_name}: {message_data_to_emit}")
        socketio.emit('receive_message', message_data_to_emit, to=room_name)
    else:
        print(f"Failed to save message for chat_id {chat_id} from user {user_id}.")
        # emit('error', {'message': 'Failed to save message'}, room=request.sid)


if __name__ == '__main__':
    # Use host='0.0.0.0' to make it accessible on your network if needed
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)