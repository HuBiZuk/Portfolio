from flask import Flask, render_template
from config import Config
from my_hotdeal import hotdeal_bp, login_manager
from apscheduler.schedulers.background import BackgroundScheduler
from my_hotdeal.crawler_main import run_all_crawlers

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 로그인 매니저 초기화
    login_manager.init_app(app)

    # 블루프린트 등록
    app.register_blueprint(hotdeal_bp, url_prefix='/hotdeal')

    # 메인 라우트
    @app.route('/')
    def index():
        return render_template('index.html')

    # 스케쥴러 설정
    run_all_crawlers()  # 시작하자마자 최초 1회 실행
    scheduler = BackgroundScheduler(daemon=True)    # daemon=True : 메인쓰레드가 종료되면 스케쥴러도 함꼐 종료
    scheduler.add_job(run_all_crawlers, 'interval', minutes=15)     # 15분마다 실행
    scheduler.start()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)