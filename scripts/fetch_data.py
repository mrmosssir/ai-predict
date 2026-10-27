#!/usr/bin/env python3
"""
更新 2024 ~ 2026 台指期三大法人未平倉與加權指數歷史數據
"""
import urllib.request
import ssl
import json
import os
import datetime
from collections import defaultdict

def fetch_data():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    print(f'Fetching data up to {today_str}...')

    # 1. 抓取期貨三大法人部位
    url_fut = f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanFuturesInstitutionalInvestors&data_id=TX&start_date=2024-01-01&end_date={today_str}'
    req_fut = urllib.request.Request(url_fut, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_fut, context=ctx, timeout=25) as r:
        fut_data = json.loads(r.read().decode())['data']

    daily_oi = defaultdict(lambda: {'dealer': 0, 'it': 0, 'foreign': 0, 'total': 0})
    for row in fut_data:
        d = row['date']
        inv = row['institutional_investors']
        net = row['long_open_interest_balance_volume'] - row['short_open_interest_balance_volume']
        if '自營' in inv:
            daily_oi[d]['dealer'] += net
        elif '投信' in inv:
            daily_oi[d]['it'] += net
        elif '外資' in inv:
            daily_oi[d]['foreign'] += net
        daily_oi[d]['total'] += net

    # 2. 抓取加權指數 (TAIEX)
    url_taiex = f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=TAIEX&start_date=2024-01-01&end_date={today_str}'
    req_taiex = urllib.request.Request(url_taiex, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_taiex, context=ctx, timeout=25) as r:
        taiex_data = json.loads(r.read().decode())['data']

    taiex_map = {row['date']: row for row in taiex_data}

    # 合併
    all_dates = sorted(set(daily_oi.keys()).union(set(taiex_map.keys())))
    combined = []
    for d in all_dates:
        oi = daily_oi.get(d, {'dealer': 0, 'it': 0, 'foreign': 0, 'total': 0})
        tx = taiex_map.get(d)
        combined.append({
            'date': d,
            'taiex_close': tx['close'] if tx else None,
            'taiex_open': tx['open'] if tx else None,
            'taiex_high': tx['max'] if tx else None,
            'taiex_low': tx['min'] if tx else None,
            'taiex_volume': tx['Trading_Volume'] if tx else None,
            'dealer_oi': oi['dealer'],
            'it_oi': oi['it'],
            'foreign_oi': oi['foreign'],
            'total_oi': oi['total']
        })

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'data', 'history_2024_2026.json')
    js_data_path = os.path.join(base_dir, 'data', 'data.js')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    with open(js_data_path, 'w', encoding='utf-8') as f:
        f.write('window.MARKET_DATA = ' + json.dumps(combined, ensure_ascii=False) + ';\n')

    print(f'Done! Successfully updated {len(combined)} trading days.')

if __name__ == '__main__':
    fetch_data()
