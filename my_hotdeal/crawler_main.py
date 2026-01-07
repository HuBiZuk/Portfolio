from datetime import datetime
from database import get_db_connection
from crawlers.dealbada import crawl_dealbada
from crawlers.naver import crawl_naver
from crawlers.ppomppu import crawl_ppomppu
from crawlers.quasarzone import crawl_quasarzone

def load_all_keywords(conn):
    # 모든 사용자의 키워드를 미리 메모리에 로드
    sql = """                                           
        SELECT k.keyword_id, k.user_id, k.keyword 
        FROM keywords k
        JOIN users u ON k.user_id = u.user_id
        WHERE u.status = 'ACTIVE'
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()

def process_deals_to_db(conn, deals, all_keywords):
    new_count = 0
    match_count = 0
    print(f" 딜 매칭 처리중...")

    for deal in deals:
        try:
            with conn.cursor() as cursor:
                # URL 중복 체크
                check_sql = "SELECT deal_id FROM deal_summary WHERE url = %s LIMIT 1"
                cursor.execute(check_sql, (deal['url'],))
                existing_deal = cursor.fetchone()

                deal_id = None

                if existing_deal:
                    # 기존 딜 업데이트
                    deal_id = existing_deal['deal_id']
                    update_sql = """
                        UPDATE deal_summary
                        SET likes = %s, price = %s, last_validated = NOW()
                        WHERE deal_id = %s
                    """
                    cursor.execute(update_sql, (deal['likes'], deal['price'], deal_id))
                else:
                    # 신규 딜 저장
                    insert_sql = """
                        INSERT INTO deal_summary (title, url, price, site, likes, img, posted_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_sql, (
                        deal['title'], deal['url'], deal['price'], deal['site'],
                        deal['likes'], deal['img'], deal['posted_at']
                    ))
                    deal_id = cursor.lastrowid
                    new_count += 1

                    # 키워드 매칭
                    for kw in all_keywords:
                        if kw['keyword'].lower() in deal['title'].lower():
                            match_sql = """
                                INSERT IGNORE INTO matched_deals (user_id, deal_id, keyword_id)
                                VALUES (%s, %s, %s)
                            """
                            cursor.execute(match_sql, (kw['user_id'], deal_id, kw['keyword_id']))
                            if cursor.rowcount > 0:
                                match_count += 1

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"DB 오류: {e}")

    print(f"저장 완료: 신규 {new_count} 건 / 매칭 {match_count}건")

# 크롤링 로직을 함수로 묶기
def run_all_crawlers():
    print(f"--- 스케쥴러 크롤링 시작 ({datetime.now()}) ---")
    conn = get_db_connection()
    try:
        keywords = load_all_keywords(conn)
        print(f"키워드 {len(keywords)}개 로드")
        print("=" * 50)

        # 딜바다
        deals = crawl_dealbada()
        process_deals_to_db(conn, deals, keywords)
        print("=" * 50)

        # 뽐뿌
        deals = crawl_ppomppu()
        process_deals_to_db(conn, deals, keywords)
        print("=" * 50)

        # 퀘이사존
        deals = crawl_quasarzone()
        process_deals_to_db(conn, deals, keywords)

    except Exception as e:
        print(f"전체 오류 발생: {e}")
    finally:
        if conn:
            conn.close()
            print("--- 스케쥴러: DB 종료 ---")

if __name__ == '__main__':
    print(f"크롤링 시작 ({datetime.now()})")
    conn = get_db_connection()
    
    try:
        keywords = load_all_keywords(conn)
        print(f"키워드 {len(keywords)}개 로드")
        print("=" * 50)
        
        # 1. 딜바다
        deals = crawl_dealbada()
        process_deals_to_db(conn, deals, keywords)
        print("=" * 50)
        
        # 2. 뽐뿌
        deals = crawl_ppomppu()
        process_deals_to_db(conn, deals, keywords)
        print("=" * 50)

        # 3. 퀘이사존
        deals = crawl_quasarzone()
        process_deals_to_db(conn, deals, keywords)
        print("=" * 50)


    except Exception as e:
        print(f"전체 오류 발생: {e}")
    finally:
        if conn:
            conn.close()
            print("DB 종료")
