import requests
from bs4 import BeautifulSoup
import re
from .base import extract_price, parse_date

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

        for row in rows:
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