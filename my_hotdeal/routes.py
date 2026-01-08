from flask import render_template, request, redirect, url_for, flash, g, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from . import hotdeal_bp
from .database import get_db_connection
from .models import User
from .forms import LoginForm, RegisterForm, KeywordForm, EditProfileForm

@hotdeal_bp.before_request
def before_request_hook():
    g.unread_notifications = 0
    if current_user.is_authenticated:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM matched_deals WHERE user_id = %s AND is_read = FALSE",
                    (current_user.id,)
                )
                result = cursor.fetchone()
                if result:
                    g.unread_notifications = result['COUNT(*)']
        finally:
            conn.close()

@hotdeal_bp.route('/', methods=['GET', 'POST'])
def index():
    # 1. 페이지네이션
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # 2. 폼 생성 (로그인, 회원가입, 키워드)
    login_form = LoginForm()
    register_form = RegisterForm()
    keyword_form = KeywordForm()

    conn = get_db_connection()
    deals = []
    keywords = []
    total = 0
    
    try:
        with conn.cursor() as cursor:
            # 전체 딜 개수
            cursor.execute("SELECT COUNT(*) FROM deal_summary where is_deleted = FALSE")
            total = cursor.fetchone()['COUNT(*)']

            # 딜 목록 조회
            sql = "SELECT * FROM deal_summary where is_deleted = FALSE ORDER BY posted_at DESC LIMIT %s OFFSET %s"
            cursor.execute(sql, (per_page, offset))
            deals = cursor.fetchall()

            # 로그인한 경우 키워드 목록 조회
            if current_user.is_authenticated:
                cursor.execute("SELECT * FROM keywords WHERE user_id = %s", (current_user.id,))
                keywords = cursor.fetchall()
    finally:
        conn.close()

    last_page = (total + per_page - 1) // per_page

    return render_template('list.html',
                           deals=deals,
                           keywords=keywords,
                           current_page=page,
                           last_page=last_page,
                           login_form=login_form,
                           register_form=register_form,
                           keyword_form=keyword_form)

@hotdeal_bp.route('/login', methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get(form.user_id.data)
        if user:
            # 비밀번호 검증
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT password FROM users WHERE user_id = %s", (form.user_id.data,))
                    result = cursor.fetchone()
                    if result and check_password_hash(result['password'], form.password.data):
                        login_user(user)
                        return redirect(url_for('my_hotdeal.index'))
            finally:
                conn.close()
        
        flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return redirect(url_for('my_hotdeal.index'))

@hotdeal_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('my_hotdeal.index'))

@hotdeal_bp.route('/register', methods=['POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 중복 아이디 체크
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (form.user_id.data,))
                if cursor.fetchone():
                    flash('이미 존재하는 아이디입니다.')
                    return redirect(url_for('my_hotdeal.index'))

                # 유저 저장
                sql = """
                    INSERT INTO users (user_id, password, name, email, phone, role, birth_date, gender)
                    VALUES (%s, %s, %s, %s, %s, 'USER', %s, %s)
                """
                cursor.execute(sql, (
                    form.user_id.data, hashed_password, form.name.data,
                    form.email.data, form.phone.data, form.birth_date.data, form.gender.data
                ))
                conn.commit()
                flash('회원가입이 완료되었습니다! 로그인해주세요.')
        except Exception as e:
            conn.rollback()
            flash(f'회원가입 오류: {e}')
        finally:
            conn.close()
    else:
        # 폼 에러 메시지 출력
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}")

    return redirect(url_for('my_hotdeal.index'))

@hotdeal_bp.route('/keyword/add', methods=['POST'])
@login_required
def add_keyword():
    form = KeywordForm()
    if form.validate_on_submit():
        keyword = form.keyword.data.strip()
        if keyword:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    # 중복 키워드 체크
                    cursor.execute("SELECT * FROM keywords WHERE user_id = %s AND keyword = %s", (current_user.id, keyword))
                    if cursor.fetchone():
                        flash('이미 등록된 키워드입니다.')
                        return redirect(url_for('my_hotdeal.index'))

                    # 키워드 저장
                    cursor.execute("insert into keywords (user_id, keyword) values (%s, %s)", (current_user.id, keyword))
                    new_keyword_id = cursor.lastrowid # 추가된 키워드의 id 가져오기

                    # 기존 모든 핫딜과 새 키워드 매칭 시도
                    cursor.execute("select deal_id, title from deal_summary")
                    all_deals = cursor.fetchall()

                    for deal in all_deals:
                        if keyword.lower() in deal['title'].lower():
                            cursor.execute(
                                """
                                insert ignore into matched_deals
                                (user_id, deal_id, keyword_id) values (%s, %s, %s)
                                """, (current_user.id, deal['deal_id'], new_keyword_id)
                            )
                    
                    conn.commit()
                    flash(f"'{keyword}' 키워드가 추가되었습니다.")
            except Exception as e:
                conn.rollback()
                flash(f"키워드 추가 중 오류 발생: {e}")
            finally:
                conn.close()
    return redirect(url_for('my_hotdeal.index'))

@hotdeal_bp.route('/keyword/delete/<int:keyword_id>')
@login_required
def delete_keyword(keyword_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM keywords WHERE keyword_id = %s AND user_id = %s", (keyword_id, current_user.id))
            conn.commit()
    finally:
        conn.close()
    return redirect(url_for('my_hotdeal.index'))

@hotdeal_bp.route('/matched')
@login_required
def matched_deals():
    conn = get_db_connection()
    deals = []
    keywords = []
    
    keyword_form = KeywordForm()
    register_form = RegisterForm()
    login_form = LoginForm()

    try:
        with conn.cursor() as cursor:
            # 매칭된 딜 목록 가져오기
            sql = """
                SELECT ds.*
                FROM deal_summary ds
                JOIN matched_deals md ON ds.deal_id = md.deal_id
                WHERE md.user_id = %s and md.is_deleted = FALSE
                ORDER BY ds.posted_at DESC
            """
            cursor.execute(sql, (current_user.id,))
            deals = cursor.fetchall()

            # 사이드바에 표시할 키워드 목록 가져오기
            cursor.execute("SELECT * FROM keywords WHERE user_id = %s", (current_user.id,))
            keywords = cursor.fetchall()

            # 알림 '읽음' 처리
            update_sql = "UPDATE matched_deals SET is_read = TRUE WHERE user_id = %s"
            cursor.execute(update_sql, (current_user.id,))
            conn.commit()
            
            g.unread_notifications = 0
    except Exception as e:
        conn.rollback()
        flash(f"매칭된 딜을 불러오는 중 오류 발생: {e}")
    finally:
        conn.close()

    return render_template(
        'matched_list.html', 
        deals=deals, 
        keywords=keywords,
        keyword_form=keyword_form,
        register_form=register_form,
        login_form=login_form
    )

@hotdeal_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm(obj=current_user) # 폼 안에 유저 정보 채우기

    if form.validate_on_submit():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    UPDATE users 
                    SET name = %s, email = %s, phone = %s
                    WHERE user_id = %s
                """
                cursor.execute(sql, (
                    form.name.data,
                    form.email.data,
                    form.phone.data,
                    current_user.id
                ))
                conn.commit()
            flash('회원 정보가 수정되었습니다.')
            return redirect(url_for('my_hotdeal.profile'))
        except Exception as e:
            conn.rollback()
            flash(f'오류가 발생했습니다: {e}')
        finally:
            conn.close()
    
    return render_template('edit_profile.html', form=form)

@hotdeal_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'ADMIN':        # 관리자 권한 확인
        abort(403)                          # 권한 없음 오류

    conn = get_db_connection()
    users = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("select * from users order by created_at desc")
            users = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('admin_users.html', users=users)

# 핫딜 삭제 (관리자 전용)
@hotdeal_bp.route('/deal/delete/<int:deal_id>')
@login_required
def delete_deal(deal_id):
    if current_user.role != 'ADMIN':
        abort(403)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("update deal_summary set is_deleted = TRUE WHERE deal_id = %s", (deal_id,))
            cursor.execute("update matched_deals set is_deleted = TRUE WHERE deal_id = %s", (deal_id,))
            conn.commit()
        flash('핫딜이 삭제되었습니다.')
    except Exception as e:
        conn.rollback()
        flash(f'삭제 중 오류 발생: {e}')
    finally:
        conn.close()

    return redirect(request.referrer or url_for('my_hotdeal.index'))

# 사용자 매칭 핫딜 삭제
@hotdeal_bp.route('/matched/delete/<int:deal_id>')
@login_required
def delete_matched_deal(deal_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 내 매칭 정보만 삭제 처리
            cursor.execute(
                "update matched_deals set is_deleted = true where deal_id = %s and user_id = %s",
                (deal_id, current_user.id)
            )
            conn.commit()
        flash('목록에서 삭제되었습니다.')
    finally:
        conn.close()
    return redirect(url_for('my_hotdeal.matched_deals'))



