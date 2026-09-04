f=open(r'c:/Python/subscription-web/backend/_tg2.py','r') 
lines=f.readlines() 
idx=next((i for i,l in enumerate(lines) if 'return buf.getvalue()' in l),None) 
print(idx,lines[idx] if idx is not None else 'NOT FOUND') 
