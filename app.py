from flask import Flask, render_template,request,redirect,url_for

app = Flask(__name__)
# implement wrong username password logic
database = {
    'user_name' : "password"
}

@app.route('/sign-up',methods = ['GET','POST'])
def sign_up():
    if request.method == 'GET':
        return render_template('signup.html')

@app.route('/',methods = ['POST','GET'])
def login():
    user_not_found = False
    wrong_password = False
    if request.method == 'POST':
        if 'Sign_in' in request.form:
            username = request.form.get('email')
            if username in database:
                password = request.form.get('password')
                if database[username] == password:
                    print('success')
                    return render_template('chat.html')
                else:
                    wrong_password = True
                    return render_template('login.html',wrong_password = wrong_password)   
            else:
                user_not_found = True
                return render_template('login.html',user_not_found = user_not_found)
        elif 'sign-up' in request.form:
            print(request.form)
            return redirect(url_for('sign_up'))
    return render_template('login.html',user_not_found = user_not_found,wrong_password = wrong_password)

if __name__ == '__main__':
    app.run(debug=True)