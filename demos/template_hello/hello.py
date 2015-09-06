#!/usr/bin/env python
# coding=utf8

import pweby


CONF = pweby.set_config('pweby.yml')


class Hello(pweby.Application):

    @pweby.route('/')
    def hello(self, req, template_name='index.html'):
        return pweby.render(template_name, name='world')


server = pweby.Server(Hello, host=CONF.host, port=CONF.port)
server.serve()
