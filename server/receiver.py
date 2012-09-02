#!/usr/bin/python
# -*- coding: utf-8 -*-

from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import urllib.parse
from settings import INPUT_PORT
import select, errno


class SMSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        o = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(o.query)
        if 'phone' in params and 'text' in params:
            self.send_response(200)
            if 'moderate' in params and params['moderate'][0] == 'no':
                self.send(params['phone'][0], params['text'][0])
            else:
                self.moderate(params['phone'][0], params['text'][0])
        else:
            self.send_response(412)

class ThreadedHTTPServer(HTTPServer, socketserver.ThreadingMixIn):
    pass

def afficher(tel, sms):
    print("[%s] %s" %(tel, sms))

def receive(moderate,send):
    SMSHandler.moderate = staticmethod(moderate)
    SMSHandler.send = staticmethod(send)
    try:
        server = ThreadedHTTPServer(('', INPUT_PORT), SMSHandler)
        print('started http server on port', INPUT_PORT, '...')
        server.serve_forever()
    except KeyboardInterrupt:
        print('shutting down http server')
        server.server_close()
        server.shutdown()

if __name__ == '__main__':
    receive(afficher, afficher)
