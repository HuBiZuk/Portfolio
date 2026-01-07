from flask import Blueprint
from flask_login import LoginManager
import pymysql
from .database import get_db_connection

# 플루 프린트 생성
hotdeal_bp = Blueprint('my_hotdeal', __name__, template_folder='templates')

# 로그인 매니저 설정
login_manager = LoginManager()
login_manager.login_view = 'my_hotdeal.login'

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.get(user_id)

# 라우트 등록
from . import routes