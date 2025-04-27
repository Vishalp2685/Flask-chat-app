from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, join_room, leave_room 
from chat_database import get_friends, get_chats, get_user_id_by_email, get_name, get_chat_id, send_message,validate, register_user

app = Flask(__name__)
app.secret_key = 'secret_key'
socketio = SocketIO(app)

def is_logged_in():
    return 'user_id' in session

@app.before_request
def check_login_except_for_auth_routes():
    if not is_logged_in() and request.endpoint not in ['login', 'sign_up', 'static']:
        return redirect(url_for('login'))


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_pass = request.form.get('Confirm_password')
        if password != confirm_pass or len(password) < 8:
            return render_template('signup.html',user_exist = True,correct_pass = False)
        success = register_user(f_name, l_name, email, password)
        if success:
            flash("Account created successfully! Please log in.", 'success')
            return redirect(url_for('login'))
        else:
            print("user already exist")
            flash("Registration failed. Email might already be in use.", 'danger')
            return render_template('signup.html',user_exist=False,correct_pass = True)
    return render_template('signup.html',user_exist=True,correct_pass = True)

@app.route('/loadchat/<int:friend_id>', methods=['GET'])
def load_messages(friend_id):
    if 'logout' in request.form:
        session.clear()
        return redirect(url_for('login'))

    if not is_logged_in():
        return redirect(url_for('login'))
    user_id = session['user_id']
    session['friend_id'] = friend_id

    friends = get_friends(user_id)
    messages = get_chats(user_id, friend_id)
    name = "Unknown User"
    for friend in friends:
        if friend.get('friend_id') == friend_id:
            name = f"{friend.get('first_name', '')} {friend.get('last_name', '')}".strip()
            break

    chat_id = get_chat_id(user_id, friend_id)
    if chat_id is None:
        flash("Could not determine chat ID.", "warning")
    return render_template('chat.html',
                           friends=friends,
                           having_friends=len(friends) > 0,
                           messages=messages,
                           name=name,
                           current_chat_id=chat_id, 
                           current_friend_id=friend_id 
                          )

@app.route('/logout')
def logout():
    session.clear() # Clear all session data
    flash("You have been logged out.", 'info')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        user_id = session['user_id']
        friends = get_friends(user_id)
        return render_template('chat.html', friends=friends, user_id=user_id, name="Select a Chat", messages=[], current_chat_id=None, current_friend_id=None)

    if request.method == 'POST':
        print(request.form)
        if 'Sign_in' in request.form:
            email = request.form.get('email')
            password = request.form.get('password')
            if validate(email, password):
                user_id = get_user_id_by_email(email)
                session['user_id'] = user_id
                session['user_name'] = get_name(user_id=user_id) 
                session['username'] = email 
                friends = get_friends(user_id)
                if friends:
                    return render_template('chat.html', friends=friends, user_id=user_id, name="Select a Chat", messages=[], current_chat_id=None, current_friend_id=None)
            else:
                flash("Invalid login credentials. Please try again.", 'danger')
                return render_template('login.html', Invalid=True)
        elif 'sign-up' in request.form:
             return redirect(url_for('sign_up')) 

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