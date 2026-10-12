#!/usr/bin/env python3
"""
Download HTML fixtures for testing
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from requests import Session

SESSION = Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

FIXTURES = {
    "categoria_cultura_arte.html": "https://riotur.rio/o-que-fazer/cultura-arte/",
    "detalhe_museu_naval.html": "https://riotur.rio/que_fazer/museu-naval/",
    "detalhe_ago.html": "https://riotur.rio/onde_comer/ago/",
    "detalhe_copacabana_palace.html": "https://riotur.rio/onde_ficar/copacabana-palace-2/",
}

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

for filename, url in FIXTURES.items():
    filepath = os.path.join(FIXTURES_DIR, filename)
    if os.path.exists(filepath):
        print("[skip] ja existe: {}".format(filename))
        continue
    print("[*] Baixando {}...".format(url))
    resp = SESSION.get(url, timeout=15)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("[OK] {} ({} bytes)".format(filename, len(resp.text)))

print("\n[OK] {} fixtures prontos".format(len(FIXTURES)))