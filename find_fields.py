with open('bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

targets = ["nomi", "modeli"]
for idx, line in enumerate(lines):
    for t in targets:
        if t in line:
            print(f"{idx+1}: {line.encode('unicode_escape').decode('ascii')[:150]}")
            break
