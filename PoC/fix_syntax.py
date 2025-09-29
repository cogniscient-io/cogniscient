#!/usr/bin/env python3
\"\"\"Fix the syntax error in test_token_display.py\"\"\"

with open('tests/test_token_display.py', 'r') as f:
    content = f.read()

# Replace the problematic line with triple backslashes
# The problematic line has three backslashes at the end, which should be one
content = content.replace('as mock_token_counter, \\\\\\n         patch', 'as mock_token_counter, \\\n         patch')

with open('tests/test_token_display.py', 'w') as f:
    f.write(content)

print(\"Fixed the syntax error in test_token_display.py\")