import requests
from bs4 import BeautifulSoup
import re
from .base import extract_price, parse_date

def crawl_quasarzone():
    print("퀘이사존 크롤링 시작...")
    url = "https://quasarzone.com/bbs/qb_saleinfo"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    deals = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        items = soup.select('div.market-info-list')

        for item in items:
            try:
                title_tag = item.select_one('span.ellipsis-with-reply-cnt')
                if not title_tag: continue
                title = title_tag.get_text(strip=True)

                link_tag = item.select_one('a.subject-link')
                href = link_tag.get('href')
                if not href: continue
                detail_url = f"https://quasarzone.com{href}"

                # 가격 추출 강화
                price = 0
                # 1. 공식 가격 태그 (text-orange)
                price_tag = item.select_one('span.text-orange')
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    # 숫자만 추출
                    price = int(re.sub(r'[^0-9]', '', price_text))
                
                # 2. 태그 없으면 제목에서 추출 (extract_price 사용)
                if price == 0:
                    price = extract_price(title)
                
                # 3. 그래도 없으면 'KRW'나 '원'이 포함된 텍스트 찾기 (보조)
                if price == 0:
                    for span in item.select('span'):
                        text = span.get_text(strip=True)
                        if 'KRW' in text or '원' in text:
                            try:
                                price = int(re.sub(r'[^0-9]', '', text))
                                if price > 0: break
                            except: pass

                img_url = ''
                thumb_link = item.select_one('a.thumb')
                if thumb_link:
                    style = thumb_link.get('style', '')
                    if 'url(' in style:
                        img_url = style.split('url(')[1].split(')')[0].replace("'", "").replace('"', "")
                    else:
                        img_tag = thumb_link.select_one('img')
                        if img_tag:
                            img_url = img_tag.get('src')

                likes = 0
                likes_tag = item.select_one('span.num')
                if likes_tag:
                    likes_text = likes_tag.get_text(strip=True)
                    likes = int(re.sub(r'[^0-9]', '', likes_text)) if any(c.isdigit() for c in likes_text) else 0

                date_tag = item.select_one('span.date')
                date_str = date_tag.get_text(strip=True) if date_tag else ''

                deals.append({
                    'title': title,
                    'url': detail_url,
                    'price': price,
                    'site': '퀘이사존',
                    'likes': likes,
                    'img': img_url,
                    'posted_at': parse_date(date_str)
                })
            except Exception:
                continue

    except Exception as e:
        print(f"퀘이사존 오류: {e}")
    
    return deals
