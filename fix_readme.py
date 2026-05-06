import re; content = open('README.md', 'r', encoding='utf-8').read(); lines = content.split('\r\n'); new = []; i=0; 
while i < len(lines):
    new.append(lines[i])
    if '### Step 2' in lines[i]:
        i += 1
        while i < len(lines) and not lines[i].strip(): new.append(lines[i]); i += 1
        if i < len(lines) and '`ash' in lines[i]:
            new.insert(-1, '> **Note**: Install package first if needed: pip install -e .'); new.append('')
    i += 1
open('README.md', 'w', encoding='utf-8').write('\r\n'.join(new)); print('OK')
