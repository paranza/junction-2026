import sys, html, re
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.inpre=0; self.buf=[]; self.blocks=[]; self.text=[]
    def handle_starttag(self, t, a):
        if t=='pre': self.inpre+=1; self.buf=[]
    def handle_endtag(self, t):
        if t=='pre' and self.inpre:
            self.inpre-=1; self.blocks.append(''.join(self.buf))
    def handle_data(self, d):
        if self.inpre: self.buf.append(d)
        else: self.text.append(d)
p=P(); p.feed(open(sys.argv[1],encoding='utf-8',errors='replace').read())
for i,b in enumerate(p.blocks):
    print(f'---- BLOCK {i} ----'); print(b)
open(sys.argv[2],'w').write(re.sub(r'\n\s*\n+','\n',' '.join(p.text)))
