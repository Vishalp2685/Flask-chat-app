from flask import Flask, render_template,request,redirect,url_for,session
from database import validate,register_user
from chat_database import get_friends,get_chats,get_user_id_by_email,get_name,get_chat_id,send_message
app = Flask(__name__)
# implement wrong username password logic

app.secret_key = 'your_super_secret_key'

@app.route('/sign-up',methods = ['GET','POST'])
def sign_up():
    if request.method == 'POST' :
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        a = register_user(f_name,l_name,email,password)
        if a:
            return redirect(url_for('login'))
    else:
        return render_template('signup.html')

@app.route('/loadchat/<int:friend_id>', methods = ['POST','GET'])
def load_messages(friend_id):
    session['friend_id'] = friend_id
    user_id = session.get('user_id')
    print("Request.form: ",request.form)
    if 'message' in request.form:
        # logic for gettin+g message and updating it into the db
        message = request.form.get('message')
        chat_id = get_chat_id(user_id,friend_id)
        send_message(user_id,chat_id,message)
        print("message:",message)
    friends = get_friends(user_id)
    messages = get_chats(user_id,friend_id)
    for i in friends:
        if i.get('friend_id') == friend_id:
            name = i.get('first_name') + " " + i.get('last_name')
    print(friends)
    print('friendid:',friend_id)
    return render_template('chat.html',friends = friends,having_friends=len(friends)>0,messages=messages,name=name)

@app.route('/',methods = ['POST','GET'])
def login():
    wrong_password = False
    if request.method == 'POST':
        if 'Sign_in' in request.form:
            username = request.form.get('email')
            password = request.form.get('password')
            session['username'] = username
            session['password'] = password
            if validate(username,password):
                user_id = get_user_id_by_email(username)
                session['user_id'] = user_id
                user_name = get_name(user_id=user_id)
                session['user_name'] = user_name
                friends = get_friends(user_id) 
                having_friends=len(friends) > 0
                if having_friends:
                    return render_template('chat.html', friends=friends,user_id=user_id,name="")
                else:
                    return render_template('add_new_friends.html',user_id=user_id)
            else:
                wrong_password = True
                return render_template('login.html',Invalid = wrong_password)   
        elif 'sign-up' in request.form:
            return redirect(url_for('sign_up'))
    else:
        if session:
            friends = get_friends(session.get('user_id')) 
            having_friends=len(friends) > 0
            user_id = session.get('user_id')
            if having_friends:
                return render_template('chat.html', friends=friends,user_id=user_id,name="")
            else:
                return render_template('add_new_friends.html',user_id=user_id)
        else:
            return render_template('login.html')
if __name__ == '__main__':
    app.run(debug=True)