#!/usr/bin/env python2

import chardet
import sys
import urllib
import urllib2
import waitsms

SMS_PORT = 13756

def to_unicode(msg):
    try:
        return msg.decode("utf-8")
    except UnicodeDecodeError:
        pass

    enc = chardet.detect(msg)['encoding']
    try:
        return msg.decode(enc, "replace")
    except LookupError:
        return msg.decode("iso-8859-1", "replace")

def _sms_received(host, tel, msg):
    tel = to_unicode(tel)
    msg = to_unicode(msg)

    print u"%s : %s" % (tel, msg)

    url = "http://%s:%d/sms?%s" % (host, SMS_PORT, urllib.urlencode({
        'phone': tel.encode('utf8'),
        'text': msg.encode('utf8')
    }))

    print url

    urllib2.urlopen(url).read()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: %s <host>" % sys.argv[0]

    #urllib2.urlopen("http://%s:%d/" % (sys.argv[1], SMS_PORT)).read()

    waitsms.runloop(lambda tel, msg: _sms_received(sys.argv[1], tel, msg))
