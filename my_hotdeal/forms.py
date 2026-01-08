from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    user_id = StringField('아이디', validators=[DataRequired()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    submit = SubmitField('로그인')

class RegisterForm(FlaskForm):
    user_id = StringField('아이디', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('비밀번호', validators=[DataRequired(), Length(min=4)])
    confirm_password = PasswordField('비밀번호 확인', validators=[DataRequired(), EqualTo('password', message='비밀번호가 일치하지 않습니다.')])
    name = StringField('이름', validators=[DataRequired()])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    phone = StringField('전화번호', validators=[DataRequired()])
    birth_date = DateField('생년월일', format='%Y-%m-%d', validators=[DataRequired()])
    gender = RadioField('성별', choices=[('M', '남성'), ('F', '여성')], validators=[DataRequired()])
    submit = SubmitField('회원가입')

class KeywordForm(FlaskForm):
    keyword = StringField('키워드', validators=[DataRequired()])
    submit = SubmitField('추가')

class EditProfileForm(FlaskForm):
    name = StringField('이름', validators=[DataRequired()])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    phone = StringField('전화번호', validators=[DataRequired()])
    submit = SubmitField('수정')

