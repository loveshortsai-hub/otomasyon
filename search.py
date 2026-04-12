import sys

with open('app_kopya.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('bul.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if 'Görsel Oluştur' in line or 'İncele &' in line or 'Tekli işlem' in line or 'Ek işlemlere geri dön' in line:
            out.write(f'{i+1}: {line.strip()[:100]}\n')
