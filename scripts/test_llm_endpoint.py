import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv('BASE_URL', 'http://127.0.0.1:8000')

def run():
    url = BASE + '/api/ai/analyze-transactions'
    print('POST', url)
    r = requests.post(url, json={'limit': 20}, timeout=30)
    print('status', r.status_code)
    print(r.text)

if __name__ == '__main__':
    run()
