from flask_login import UserMixin
from .database import get_db_connection

class User(UserMixin):
    def __init__(self, user_id, name, email, roll='USER'):
        self.id = user_id
        self.name = name
        self.email = email
        self.roll = roll

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = "select * from users where user_id = %s"
                cursor.execute(sql, (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    return User(
                        user_id=user_data['user_id'],
                        name=user_data['name'],
                        email=user_data['email'],
                        roll=user_data['role']
                    )
        finally:
            conn.close()
        return None

