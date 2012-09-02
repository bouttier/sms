#!/usr/bin/python
# -*- coding: utf-8 -*-

from sender import Sender
from moderator import Moderator
from receiver import receive


s = Sender()
m = Moderator(s.send)

m.start()
s.start()

receive(m.moderate, s.send)
