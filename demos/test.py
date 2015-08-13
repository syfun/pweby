#!/usr/bin/env python
# coding=utf8

import eventlet
from eventlet import wsgi

from webob.dec import wsgify
from webob import Response


# @wsgify
# def app(req, ss):
#     return Response('hello')

#
# if __name__ == '__main__':
#     sock = eventlet.listen(('127.0.0.1', 8080))
#     wsgi.server(sock, app)

from functools import wraps


def deco(url):
    def _deco(func):
        func.url = url

        @wraps(func)
        def __deco(*args, **kwargs):
            func(*args, **kwargs)
        return __deco
    return _deco


class A(object):

    a = 2

    def __new__(cls, *args, **kwargs):
        print cls.hello.url


    def __init__(self):
        for k, v in A.__dict__.items():
            url = getattr(v, 'url', None)
            if url:
                print url

    @deco('/sdf')
    def hello(self):
        """
        Hello
        :return:
        """
        pass

    @classmethod
    def test(cls):
        print cls.hello.url
        print cls.__dict__['hello'].url
        print hasattr(cls.hello, 'url')

a = A()
