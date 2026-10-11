"""Single-command local launcher: serves UI and optimization API, with no cloud access."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json
import os
from app import MAX_JSON_BYTES,route

WEB_DIR=Path(__file__).resolve().parent/'web'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(WEB_DIR),**kwargs)
    def send_json(self,status,obj):
        data=json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=self.path.split('?',1)[0]
        if path.startswith('/api/'):
            status,body=route('GET',path)
            return self.send_json(status,body)
        return super().do_GET()
    def do_POST(self):
        path=self.path.split('?',1)[0]
        if path not in ('/api/optimize','/api/intelligence'):return self.send_json(404,{"error":"Unknown route"})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>MAX_JSON_BYTES or n<0:
                return self.send_json(413,{"error":"Request exceeds 16 KB"})
            body=json.loads(self.rfile.read(n) or b'{}')
        except (ValueError,UnicodeDecodeError):return self.send_json(400,{"error":"Invalid JSON"})
        status,payload=route('POST',path,body)
        return self.send_json(status,payload)
    def log_message(self,fmt,*args):
        if '/api/' in str(args):super().log_message(fmt,*args)

if __name__=='__main__':
    port=int(os.environ.get('PORT','8000'))
    print(f'Grid Flex local dashboard: http://localhost:{port}')
    print('Synthetic demonstration. Not connected to actual meters or industrial equipment.')
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
