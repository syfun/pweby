#!/usr/bin/env python
# coding=utf8

import pweby


class Hello(pweby.Application):

    @pweby.route('/')
    def hello(self, req):
        return pweby.Response('Hello World!')


server = pweby.Server(Hello, host='127.0.0.1', port=8080)
server.serve()
