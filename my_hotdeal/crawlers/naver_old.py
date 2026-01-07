"""
네이버는 동적 렌더링(자바스크립트) 방식이라서 처음에 껍데기 html만 주고 실제 데이터는 나중에 채워넣는 방식
해결하기 위해서는 Selenium 을 써야함 - 실제 크롬 브라우저를 끠워서 사람이 접속한 것처럼 페이지를 다 로딩 한 다음에
데이터를 긁어 와야함

현재 코드 방식은 못 불러옴
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def crawl_naver():
    print("네이버 크롤링 시작...")
    url = "https://shopping.naver.com/home/p/index.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.naver.com/'
    }
    deals = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('a[data-shp-contents-dtl]')
        print(f"네이버 아이템 개수: {len(items)}") # 이게 0이면 선택자가 틀렸거나 차단당한 것

        for item in items[:20]:
            try:
                json_str = item.get('data-shp-contents-dtl')
                if not json_str: continue
                data_list = json.loads(json_str)
                data_dict = {d['key']: d['value'] for d in data_list}

                title = data_dict.get('chnl_prod_nm', '')
                price = int(data_dict.get('price', '0'))
                if not title: continue

                href = item.get('href')
                img_tag = item.select_one('img')
                img_url = img_tag.get('src') if img_tag else ''

                deals.append({
                    'title': title,
                    'url': href,
                    'price': price,
                    'site': '네이버',
                    'likes': 0,
                    'img': img_url,
                    'posted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except: continue
    except Exception as e:
        print(f"네이버 오류: {(e)}")
    return deals