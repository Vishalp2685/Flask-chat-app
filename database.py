from sqlalchemy import create_engine,text

engine = create_engine("mysql+pymysql://root:151432@127.0.0.1:3306/chat_app_database?charset=utf8mb4")

def validate(email,password):
    query = text("SELECT * FROM users WHERE email = :email AND password = :password")

    with engine.connect() as conn:
        result = conn.execute(query, {"email": email, "password": password}).fetchone()
        return result if result else None
    

def register_user(first_name,last_name,email,password):
    already_exist = text("""
                SELECT * FROM users WHERE email = :email
                         """)
    query = text("""
         INSERT INTO login__info (first_name, last_name, email, password)
         VALUES (:first_name, :last_name, :email, :password)
     """)
    
    with engine.connect() as conn:
        user_exist = conn.execute(already_exist,{"email":email}).fetchone()
        if user_exist == None:
            return False

    with engine.connect() as conn:
        result = conn.execute(query,{
            "first_name":first_name,
            "last_name":last_name,
            "email":email,
            "password":password
            })
        conn.commit()
        print(result)
        return True