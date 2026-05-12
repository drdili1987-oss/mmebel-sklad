import re

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

matches = re.findall(r'"([^"]*Yetkazishlar nazorati)"', content)
print(f"Found {len(matches)} matches:")
for idx, m in enumerate(matches):
    print(f"{idx}: {m.encode('unicode_escape')} -> {len(m)} chars")

unique = set(matches)
if len(unique) == 1:
    print("All match EXACTLY")
else:
    print("THEY DO NOT MATCH!")
    for i, x in enumerate(unique):
        print(f"Unique {i}: {x.encode('unicode_escape')}")
