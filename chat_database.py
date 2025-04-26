from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import mysql.connector

engine = create_engine(
    "mysql+pymysql://root:151432@127.0.0.1:3306/chat_app_database?charset=utf8mb4"
)

def get_friends(user_id):
    # print(user_id)
    friend_query = """
    SELECT 
        u.user_id AS friend_id,
        u.first_name,
        u.last_name,
        u.profile_pic
    FROM user_friends uf
    JOIN users u ON u.user_id = uf.friend_user_id
    WHERE uf.user_id = :user_id;
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(friend_query), {"user_id": user_id}).fetchall()
            return [
                {
                    "friend_id": r[0],
                    "first_name": r[1],
                    "last_name": r[2],
                    "profile_pic": r[3]
                }
                for r in rows
            ]
    except SQLAlchemyError as e:
        print("Database error:", e)
        return []

def get_name(user_id):
    query = "Select first_name,last_name from users where user_id = :user_id"
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {"user_id": user_id}).fetchone()
            return result[0] + " "+result[1] if result else None
    except SQLAlchemyError as e:
        print("Database error:", e)
        return None

def get_user_id_by_email(email):
    query = "SELECT user_id FROM users WHERE email = :email;"
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {"email": email}).fetchone()
            return result[0] if result else None
    except SQLAlchemyError as e:
        print("Database error:", e)
        return None


def get_chats(user_id, friend_id):
    # print(user_id)
    chat_query = """
    SELECT m.id, m.sender_id, u.first_name, u.last_name, m.content, m.created_at
    FROM user_friends uf
    JOIN messages m ON m.chat_id = uf.chat_id
    JOIN users u ON u.user_id = m.sender_id
    WHERE 
        (uf.user_id = :user_id AND uf.friend_user_id = :friend_id)
    ORDER BY m.created_at ASC;
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(chat_query), {
                "user_id": user_id,
                "friend_id": friend_id
            }).fetchall()
            return [
                {
                    "message_id": r[0],
                    "sender_id": r[1],
                    "sender_name": f"{r[2]} {r[3]}",
                    "content": r[4],
                    "created_at": r[5]
                }
                for r in rows
            ]
    except SQLAlchemyError as e:
        print("Database error:", e)
        return []




def get_messages_by_chat_id(chat_id):
    query = """
    SELECT 
        m.id,
        m.sender_id,
        u.first_name,
        u.last_name,
        m.content,
        m.created_at
    FROM messages m
    JOIN users u ON u.user_id = m.sender_id
    WHERE m.chat_id = :chat_id
    ORDER BY m.created_at ASC;
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(query), {"chat_id": chat_id}).fetchall()
            return [
                {
                    "message_id": r[0],
                    "sender_id": r[1],
                    "sender_name": f"{r[2]} {r[3]}",
                    "content": r[4],
                    "created_at": r[5]
                }
                for r in rows
            ]
    except SQLAlchemyError as e:
        return []


def get_chat_id(user_id, friend_id):
    query = """
    SELECT chat_id
    FROM user_friends
    WHERE user_id = :user_id AND friend_user_id = :friend_id;
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {
                "user_id": user_id,
                "friend_id": friend_id
            }).fetchone()
            return result[0] if result else None
    except SQLAlchemyError as e:
        print("Database error:", e)
        return None
    


def send_message(sender_id,chat_id,content):

    db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '151432',
    'database': 'chat_app_database'
}
    connection = mysql.connector.connect(**db_config)

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Prepare SQL INSERT statement
        insert_query = """
            INSERT INTO messages (chat_id, sender_id, content, created_at)
            VALUES (%s, %s, %s, %s);
            """
        val = (chat_id,sender_id,content,datetime.now())  # Replace with your values

        # Execute the query
        cursor.execute(insert_query, val)

        # Commit the changes
        connection.commit()
        print(cursor.rowcount, "record inserted.")
        return True

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return False
    finally:
        # Close cursor and connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    
# print(get_chats(1,2))
# # Example usage
# for info in get_friends(1):
#     print(info)
