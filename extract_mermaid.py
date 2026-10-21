import re

with open('docs/ARCHITECTURE.md', 'r') as f:
    content = f.read()

# Extract the first mermaid diagram
match = re.search(r'```mermaid\n(.*?)\n```', content, re.DOTALL)
if match:
    diagram = match.group(1)
    with open('architecture.mmd', 'w') as f:
        f.write(diagram)
    print('Mermaid diagram extracted to architecture.mmd')
else:
    print('No mermaid diagram found')