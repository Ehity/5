import pathlib 
pathlib.Path(r'c:\Python\subscription-web\backend\test_generator.py').write_bytes(pathlib.Path(r'c:\Python\subscription-web\backend\_tg2.py').read_bytes()) 
print(123) 
import sys 
sys.path.insert(0,r'c:/Python/subscription-web/backend') 
from test_generator import generate_test_csv, SERVICES 
csv=generate_test_csv(); lines=csv.decode().split(chr(10)) 
subs=[l for l in lines if 'Subscription' in l] 
print(f'Total: {len(lines)}, Subs: {len(subs)}') 
print(chr(10).join(subs[:5])) 
f=open(r'c:/Python/subscription-web/backend/_tg2.py') 
print(len(f.readlines())) 
