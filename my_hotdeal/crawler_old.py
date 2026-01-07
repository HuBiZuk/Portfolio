# -*- coding: utf-8 -*-

from distutils.command.check import check
from http.client import responses

import requests                     # HTTP 요청 (웹페이지 가져오기)
from bs4 import BeautifulSoup       # HTML 파싱
import time                         # 시간 관련 기능
import re                           # 정규식(가격, 숫자 추출)
import pymysql                      # MySQL DB 연동
from datetime import datetime       # 날짜 시간 처리

# 초기 크롤러 파일 ( 지금은 안씀 )



# ===================== [DB 설정] =======================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345',
    'db': 'my_hotdeal',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor   # 결과를 dicr 형태로 받음
}

# =================== [공통 함수] =====================
def get_db_connection():
    return pymysql.connect(**DB_CONFIG)     # DB_CONFIG 딕셔너리를 출어서 mysql 연결 생성

def extract_price(text):    # 가격을 찾기위한 정규식 패턴 함수
    patterns = [
        r'(\d{1,3}(?:,\d{3})+)원',       # 10,000원
        r'(\d+)원',                     # 10000원
        r'\[(\d{1,3}(?:,\d{3})+)\]',     # [10,000]
        r'\((\d{1,3}(?:,\d{3})+)\)',     # (10,000)
    ]

    for pattern in patterns:                                            # 모든 패턴을 하나씩 검사
        match = re.search(pattern, text)                                # 제목에서 해당 패턴 검색
        if match:
            price_str = match.group(1).replace(',','')      # 콤마 제거
            try:
                price = int(price_str)                                  # 문자열 -> 숫자 변환
                if 100 < price < 10000000:                              # 비정상 가격 필터링
                    return price
            except:
                pass

    return 0        # 가격 못찾으면 0으로 반환

def parse_date(date_str):
    # 사이트별로 다른 날짜 문자열 통일 함수
    now = datetime.now()                                            # 현재 날짜/시간

    if ':' in date_str and '-' not in date_str:                     # 시간만 있는 경우 (ex: 14:23)
        return now.strftime('%Y%m%d') + ' ' + date_str + ':00'

    elif '-' in date_str and len(date_str) == 5:                    # 월-일 형태 (ex: 09-21)
        parts = date_str.split('-')
        return f"{now.year}-{parts[0]}-{parts[1]} 00:00:00"

    elif '/' in date_str and len(date_str) <= 5:                    # 월/일 형태 (ex: 9/21)
        parts = date_str.split('/')
        return f"{now.year}-{parts[0].zfill(2)}-{parts[1].zfill(2)} 00:00:00"

    return now.strftime('%Y-%m-%d %H:%M:%S')                        # 그외 현재시각 반환

# =============== [DB 저장 / 매칭] ========

def load_all_keywords(conn):

    # 모든 사용자의 키워드를 미리 메모리에 로드. 매 딜마다 DB를 조회하는 것보다 효율적
    # 활성화 유져의 키워드 조회
    sql = """                                           
        SELECT k.keyword_id, k.user_id, k.keyword 
        FROM keywords k
        JOIN users u ON k.user_id = u.user_id
        WHERE u.status = 'ACTIVE'
    """
    with conn.cursor() as cursor:   # db 커서 생성
        cursor.execute(sql)         # sql 실행
        return cursor.fetchall()    # 결과 전체 반환

def process_deals_to_db(conn, deals, all_keywords):
    # 중복확인 후 신규 딜 저장 키워드 매칭 수행
    new_count = 0
    match_count = 0
    print(f" 딜 매칭 처리중...")

    for deal in deals:                                  # 크롤링된 딜 하나씩 처리
        try:
            with conn.cursor() as cursor:
                check_sql = """
                    select deal_id
                    from deal_summary
                    where url = %s
                    limit 1
                """                                     # url 기준 중복 체크
                cursor.execute(check_sql, (deal['url'],))
                existing_deal = cursor.fetchone()

                deal_id = None

                if existing_deal:   # 기존 딜
                    deal_id = existing_deal['deal_id']
                    update_sql = """
                    UPDATE deal_summary
                    set likes = %s,
                        price = %s,
                        last_validated = now()
                    where deal_id = %s
                    """
                    cursor.execute(update_sql, (
                        deal['like'],
                        deal['price'],
                        deal_id
                    ))

                else:   # 신규 딜
                    insert_sql = """
                    INSERT INTO deal_summary
                    (title, url, price, site, likes, img, posted_at)
                    VALUES (%s, %s, %s, %s, %s,%s, %s)
                    """
                    cursor.execute(insert_sql, (
                        deal['title'],
                        deal['url'],
                        deal['price'],
                        deal['site'],
                        deal['likes'],
                        deal['img'],
                        deal['posted_at']
                    ))
                    deal_id = cursor.lastrowid      # 마지막 삽입된 딜 ID
                    new_count += 1                  # 딜아이디 +1

                    for kw in all_keywords:                                     # 모든 키워드와 비교
                        if kw['keyword'].lower() in deal['title'].lower():      # 제목에 키워드 있으면
                            match_sql = """
                                insert ignore into matched_deals
                                (user_id, deal_id, keyword_id)
                                values (%s, %s, %s)
                            """
                            cursor.execute(match_sql, (
                                kw['user_id'],
                                deal_id,
                                kw['keyword_id']
                            ))
                            if cursor.rowcount > 0:
                                match_count += 1

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"DB 오류e: {e}")

    print(f"저장 완료: 신규{new_count} 건 / 매칭 {match_count}건")


    # =============== [크롤러] ==============================


def crawl_dealbada():
    print("\n" + "=" * 50)
    print("딜바다 크롤링 시작")
    print("=" * 50)

    url = "https://www.dealbada.com/bbs/board.php?bo_table=deal_domestic"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    deals = []

    try:
        response = requests.get(url, headers=headers, timeout=10)   # html 요청
        response.encoding = 'utf-8'                                 # 응답 html 인코딩 지정
        soup = BeautifulSoup(response.text, 'html.parser')  #  HTML 문자열을 BeautifulSoup 객체로 파싱
        rows = soup.select('table tbody tr')                        # 게시글이 들어있는 테이블의 모든 행 선택

        for row in rows[:20]:  # 상위 20개만
            # 제목 링크 찾기
            title_link = row.select_one('td.td_subject a[href*="wr_id"]')
            if not title_link: continue

            # 이미지 url 찾기
            img_tag = row.select_one('img')
            img_url = ''
            if img_tag:
                src_val = img_tag.get('src')
                if src_val:
                    if src_val.startswith('//'):
                        img_url = 'https:' + src_val
                    elif src_val.startswith('/'):
                        img_url = 'https://www.dealbada.com' + src_val
                    else:
                        img_url = src_val

            title = title_link.get_text(strip=True)
            title = re.sub(r'\s*\[d+\]$', '', title)    # 댓글수 제거

            href = title_link.get('href')
            if href.startswith('//'):
                detail_url = 'https:' + href
            elif href.startswith('/'):
                detail_url = 'https://www.dealbada.com' + href
            else:
                detail_url = href

            # 날짜
            date_td = row.select_one('td.td_date')
            if not date_td:
                date_td = row.select_one('td:nth-last-child(2)')

            date_str = date_td.get_text(strip=True) if date_td else ""

            deals.append({
                'title': title,
                'url': detail_url,
                'price': extract_price(title),
                'site': '딜바다',
                'likes': 0,
                'img': img_url,
                'posted_at': parse_date(date_str)
            })
    except Exception as e:
        print(f"딜바다 오류: {str(e)}")
    return deals


def crawl_ppomppu():
    print("\n" + "=" * 50)
    print("뽐뿌 크롤링 시작")
    print("=" * 50)

    url = "http://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.ppomppu.co.kr/'}
    deals = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table[class*="list"] tr')

        for row in rows[:20]:
            title_link = row.select_one('td.list_title a[href*="no="]')
            if not title_link: continue

            title = title_link.get_text(strip=True)
            href = title_link.get('href')
            detail_url = 'http://www.ppomppu.co.kr' + href if href.startswith('/') else href

            likes_td = row.select_one('td.list_voteup')
            likes = int(likes_td.get_text(strip=True)) if likes_td else 0

            date_td = row.select_one('td.list_time')
            date_str = date_td.get_text(strip=True) if date_td else ""

            deals.append({
                'title': title,
                'url': detail_url,
                'price': extract_price(title),  # 뽐뿌는 제목 의존
                'site': '뽐뿌',
                'likes': likes,
                'img': '',
                'posted_at': parse_date(date_str)
            })
    except Exception as e:
        print(f" 뽐뿌 오류: {str(e)}")
    return deals


def crawl_quasarzone():
    print("\n" + "=" * 50)
    print("퀘이사존 크롤링 시작")
    print("=" * 50)

    url = "https://quasarzone.com/bbs/qb_saleinfo"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quasarzone.com/'}
    deals = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.market-info-list-item')

        for item in items[:20]:
            title_link = item.select_one('a[href*="/bbs/qb_saleinfo/"]')
            if not title_link: continue

            # 제목 (span 태그 안쪽 텍스트)
            title_span = item.select_one('span.ellipsis-with-reply-cnt')
            title = title_span.get_text(strip=True) if title_span else title_link.get_text(strip=True)

            href = title_link.get('href')
            detail_url = 'https://quasarzone.com' + href if href.startswith('/') else href

            likes_elem = item.select_one('span.num.vote')
            likes = 0
            if likes_elem:
                likes = int(re.sub(r'[^0-9]', '', likes_elem.get_text(strip=True)))

            date_elem = item.select_one('span.date')
            date_str = date_elem.get_text(strip=True) if date_elem else ""

            # ★ [수정됨] 가격 정보 태그 우선 확인
            price = 0
            price_tag = item.select_one('div.market-info-sub span.text-orange')
            if price_tag:
                # "KRW 120,000" 같은 형태 처리
                price_text = price_tag.get_text(strip=True)
                price = int(re.sub(r'[^0-9]', '', price_text))

            # 태그에 없으면 기존 방식(제목) 사용
            if price == 0:
                price = extract_price(title)

            deals.append({
                'title': title,
                'url': detail_url,
                'price': price,
                'site': '퀘이사존',
                'likes': likes,
                'img': '',
                'posted_at': parse_date(date_str)
            })
    except Exception as e:
        print(f" 퀘이사존 오류: {str(e)}")
    return deals

# ===================== [메인 실행] ======================

if __name__ == '__main__':      # 메인 파일이 직접 실행될 때만 동작
    print("=" * 50)
    print(f"전체 사이트 크롤링 및 DB 저장 시작 ({datetime.now()})")
    print("=" * 50)

    conn = None

    try:
        conn = get_db_connection()
        print("DB 연결 성공")

        keywords = load_all_keywords(conn)
        print(f"키워드 {len(keywords)}개 로드")

        dealbada_deals = crawl_dealbada()
        process_deals_to_db(conn, dealbada_deals, keywords)

        ppomppu_deals = crawl_ppomppu()
        process_deals_to_db(conn, ppomppu_deals, keywords)

        quasar_deals = crawl_quasarzone()
        process_deals_to_db(conn, quasar_deals, keywords)

    except Exception as e:
        print(f"\n 크롤링 오류: {e}")
    finally:
        if conn:
            conn.close()
            print("DB 종료")
