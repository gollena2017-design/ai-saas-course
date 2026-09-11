#!/usr/bin/env python3
"""Simple integration test for transactions API: create -> summary -> delete"""
import requests
import sys

BASE = "http://127.0.0.1:8000"

def create():
    payload = {
        "type": "expense",
        "amount": 12.34,
        "category": "test-script",
        "description": "script run",
        "date": "2026-09-11",
    }
    r = requests.post(f"{BASE}/api/transactions", json=payload)
    print('POST', r.status_code, r.text)
    r.raise_for_status()
    return r.json().get('id')


def summary():
    r = requests.get(f"{BASE}/api/summary")
    print('SUMMARY', r.status_code, r.text)
    r.raise_for_status()
    return r.json()


def delete(id_):
    r = requests.delete(f"{BASE}/api/transactions/{id_}")
    print('DELETE', r.status_code, r.text)
    return r.status_code


if __name__ == '__main__':
    try:
        id_ = create()
        summary()
        status = delete(id_)
        if status == 200:
            print('OK')
            sys.exit(0)
        else:
            print('DELETE failed', status)
            sys.exit(2)
    except Exception as e:
        print('ERROR', e)
        sys.exit(1)
