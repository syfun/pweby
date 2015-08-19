#!/usr/bin/env python
# coding=utf8

class config(object):

    def __init__(self):
        self.conf = {'name': 'test'}

    def __getattr__(self, item):
        return self.conf.get(item, None)


c = config()
print c.conf
print c.name
print hasattr(c, 'name')
