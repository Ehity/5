f=open(r'c:/Python/subscription-web/backend/_tg2.py','r') 
lines=f.readlines() 
idx=next((i for i,l in enumerate(lines) if 'return buf.getvalue()' in l),None) 
new_content=['\n','import base64\n','\n','\n','def generate_test_with_data():\n','    csv_bytes=generate_test_csv()\n','    return {\n','        \"csv_text\":csv_bytes.decode(\"utf-8\"),\n','        \"pdf_base64\":base64.b64encode(generate_test_pdf()).decode(),\n','    }\n'] 
open(r'c:/Python/subscription-web/backend/_tg2.py','w').writelines(lines) 
