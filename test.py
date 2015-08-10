#!/usr/bin/env python
# coding=utf8

from wsgi import WSGIService, Application, Response, Middleware
from utils import route


class Test(Middleware):
    def process_request(self, req):
        return None

    def process_response(self, response):
        response.write('Test middleware')
        return response

class Test1(Middleware):
    def process_response(self, response):
        response.write('TEst1')
        return response

class Hello(Application):

    @route('/')
    def hello(self, req):
        return Response('hello')


middlewares = [Test, Test1]
service = WSGIService(Hello(), middlewares=middlewares)
service.start()
