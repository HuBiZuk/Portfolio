# -*- coding: utf-8 -*-
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from .base import extract_price, parse_date

def crawl_ppomppu():
    print("뽐뿌 핫딜 크롤링 시작 (Selenium)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    deals = []
    driver = None

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = "https://www.ppomppu.co.kr/hotdeal/"
        driver.get(url)
        time.sleep(3)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        items = soup.select('ul#hotdeal li.item')
        print(f"뽐뿌 핫딜 아이템 개수: {len(items)}")

        for item in items:
            try:
                # 제목 찾기
                title_span = None
                spans = item.select('p a span')
                for span in spans:
                    if not span.get('class') or 'mall' not in span.get('class'):
                        title_span = span
                        break
                
                if not title_span: continue
                title = title_span.get_text(strip=True)
                
                # 링크
                link_tag = title_span.find_parent('a')
                href = link_tag.get('href')
                if not href: continue
                detail_url = href

                # 가격
                price = 0
                ps = item.select('p')
                for p in ps:
                    spans = p.find_all('span', recursive=False)
                    for span in spans:
                        text = span.get_text(strip=True)

                        # 원과 숫자가 포함되면
                        if '원' in text and any(c.isdigit() for c in text):
                            price_text = re.sub(r'[^0-9]', '', text)
                            if price_text:
                                price = int(price_text)
                                break
                    if price > 0: break
                
                if price == 0:
                    price = extract_price(title)
                
                if price > 100000000: price = 0

                # [수정] 가격이 0이면 수집 제외
                if price == 0:
                    continue

                # 이미지
                img_url = ''
                view_div = item.select_one('div.view a')
                if view_div:
                    style = view_div.get('style', '')
                    if 'url(' in style:
                        if '"' in style:
                            raw_url = style.split('url("')[1].split('")')[0]
                        elif "'" in style:
                            raw_url = style.split("url('")[1].split("')")[0]
                        else:
                            raw_url = style.split('url(')[1].split(')')[0]
                        
                        if raw_url.startswith('//'):
                            img_url = 'https:' + raw_url
                        else:
                            img_url = raw_url

                date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                deals.append({
                    'title': title,
                    'url': detail_url,
                    'price': price,
                    'site': '뽐뿌',
                    'likes': 0,
                    'img': img_url,
                    'posted_at': date_str
                })
            except Exception:
                continue

    except Exception as e:
        print(f"뽐뿌 전체 오류: {e}")
    finally:
        if driver:
            driver.quit()
    
    return deals
