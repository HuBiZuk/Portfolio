# -*- coding: utf-8 -*-
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def crawl_naver():
    print("네이버 '오늘의 혜택' 크롤링 시작 (Selenium)...")

    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    deals = []
    driver = None

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })

        url = "https://shopping.naver.com/ns/home/today-event"
        driver.get(url)
        time.sleep(3)
        
        # 스크롤을 충분히 내려서 데이터 로딩
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        potential_cards = soup.select('li')
        product_cards = []
        
        for li in potential_cards:
            if len(str(li)) < 300: continue
            if not li.select_one('img'): continue
            text = li.get_text()
            if not any(char.isdigit() for char in text): continue
            product_cards.append(li)

        print(f"네이버 상품 카드 후보 개수: {len(product_cards)}")

        for card in product_cards:
            try:
                title_tag = card.select_one('strong') or card.select_one('h3') or card.select_one('[class*="title"]')
                if not title_tag: continue
                title = title_tag.get_text(strip=True)
                
                # [필터링] 블로그, 리뷰, 후기 제외
                if any(keyword in title for keyword in ['블로그', '리뷰', '후기']):
                    continue

                price = 0
                price_tags = card.select('[class*="price"], strong, span')
                for tag in price_tags:
                    text = tag.get_text(strip=True).replace(',', '').replace('원', '')
                    if text.isdigit() and int(text) > 100:
                        price = int(text)
                        break
                
                if price == 0: continue

                img_tag = card.select_one('img')
                img_url = ''
                if img_tag:
                    img_url = img_tag.get('src') or img_tag.get('data-src') or ''

                link_tag = card.select_one('a')
                href = link_tag.get('href') if link_tag else ''
                if href and not href.startswith('http'):
                    from urllib.parse import urljoin
                    href = urljoin(driver.current_url, href)
                
                # [필터링] 링크가 블로그나 카페면 제외
                if 'blog.naver.com' in href or 'cafe.naver.com' in href:
                    continue

                deals.append({
                    'title': title, 'url': href, 'price': price, 'site': '네이버',
                    'likes': 0, 'img': img_url, 'posted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            except Exception:
                continue

    except Exception as e:
        print(f"네이버 크롤링 오류: {e}")
    finally:
        if driver:
            driver.quit()

    print(f"네이버 수집 완료: {len(deals)} 건")
    return deals
