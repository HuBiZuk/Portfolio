# 공통 도구함

import re
from datetime import datetime

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
        return now.strftime('%Y-%m-%d') + ' ' + date_str + ':00'

    elif '-' in date_str and len(date_str) == 5:                    # 월-일 형태 (ex: 09-21)
        parts = date_str.split('-')
        return f"{now.year}-{parts[0]}-{parts[1]} 00:00:00"

    elif '/' in date_str and len(date_str) <= 5:                    # 월/일 형태 (ex: 9/21)
        parts = date_str.split('/')
        return f"{now.year}-{parts[0].zfill(2)}-{parts[1].zfill(2)} 00:00:00"

    return now.strftime('%Y-%m-%d %H:%M:%S')                        # 그외 현재시각 반환