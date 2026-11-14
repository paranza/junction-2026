import sys, json
nb = json.load(open(sys.argv[1], encoding='utf-8'))
for i, c in enumerate(nb['cells']):
    src = ''.join(c.get('source', []))
    print(f'#### CELL {i} [{c["cell_type"]}]')
    print(src[:3000])
