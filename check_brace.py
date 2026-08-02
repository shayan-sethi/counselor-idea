import sys

with open('static/app.js') as f:
    text = f.read()

def find_mismatch(s):
    stack = []
    in_string = False
    str_char = ''
    in_comment = False
    in_block_comment = False
    i = 0
    while i < len(s):
        c = s[i]
        
        if in_comment:
            if c == '\n':
                in_comment = False
            i += 1
            continue
            
        if in_block_comment:
            if c == '*' and i + 1 < len(s) and s[i+1] == '/':
                in_block_comment = False
                i += 1
            i += 1
            continue
            
        if in_string:
            if c == '\\':
                i += 2
                continue
            if c == str_char:
                in_string = False
            i += 1
            continue
            
        if c in ['\'', '\"', '`']:
            in_string = True
            str_char = c
            i += 1
            continue
            
        if c == '/' and i + 1 < len(s):
            if s[i+1] == '/':
                in_comment = True
                i += 1
                continue
            if s[i+1] == '*':
                in_block_comment = True
                i += 1
                continue
                
        if c in '{[(':
            stack.append((c, i))
        elif c in '}])':
            if not stack:
                print('Unmatched', c, 'at', i)
                return
            top, _ = stack.pop()
            if (top == '{' and c != '}') or (top == '[' and c != ']') or (top == '(' and c != ')'):
                print('Mismatch', top, 'and', c, 'at', i)
                return
        i += 1
        
    if stack:
        print('Unclosed', stack[-5:])
        for char, idx in stack[-5:]:
            line_no = s.count('\n', 0, idx) + 1
            print(f"Unclosed {char} at line {line_no}")

find_mismatch(text)
