from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from mib_runner.model_clients import HttpJsonModelClient


class Handler(BaseHTTPRequestHandler):
    seen = []
    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        payload = json.loads(self.rfile.read(n))
        Handler.seen.append(payload)
        body = json.dumps({
            'text': '{"type":"message","content":"ok"}',
            'usage': {'input_tokens': 10, 'output_tokens': 3},
            'metadata': {'test': True},
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass


def test_http_json_model_contract_is_stateless_request_shape():
    Handler.seen = []
    server = HTTPServer(('127.0.0.1', 0), Handler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        endpoint = f'http://127.0.0.1:{server.server_address[1]}/complete'
        c = HttpJsonModelClient(endpoint=endpoint, model_id='fixed-model')
        out = c.complete(
            messages=[{'role':'system','content':'s'},{'role':'user','content':'u'}],
            parameters={'temperature':0,'seed':7}, request_id='r1'
        )
        assert json.loads(out.text)['content'] == 'ok'
        assert out.usage['input_tokens'] == 10
        assert Handler.seen == [{
            'model':'fixed-model',
            'messages':[{'role':'system','content':'s'},{'role':'user','content':'u'}],
            'parameters':{'temperature':0,'seed':7},
            'request_id':'r1',
        }]
    finally:
        server.shutdown(); server.server_close()
