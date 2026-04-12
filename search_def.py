import sys

with open('app_kopya.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('bul.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if 'def gorsel_klonla_dialog' in line or 'def gorsel_analiz_dialog' in line:
            out.write(f'{i+1}: {line.strip()[:100]}\n')
