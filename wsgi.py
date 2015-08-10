#!/usr/bin/env python
# coding=utf8
# Copyright 2015 Syfun
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import eventlet
from eventlet import wsgi
from webob import dec, exc, Response as Resp


class WSGIService(object):
    """Server class to manage a WSGI server, serving a WSGI application."""

    def __init__(self, app, host=None, port=None, middlewares=None):
        self.app = app
        self._host = host or '127.0.0.1'
        self._port = port or 8080
        self._socket = self._get_socket(self._host, self._port)
        self._middlewares = middlewares

    def _get_socket(self, host, port):
        bind_addr = (host, port)
        sock = eventlet.listen(bind_addr)
        return sock

    def start(self):
        """Run the blocking eventlet WSGI server.

        :returns: None

        """
        for middle in self._middlewares:
            self.app = middle.factory(self.app)
        wsgi.server(self._socket, self.app)

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port


from utils import mapper


class Application(object):
    """Base WSGI application wrapper. Subclasses need to implement process_request."""

    @dec.wsgify
    def __call__(self, req):
        response = self.process_request(req)
        return response

    def process_request(self, req):
        func = mapper.match(req)
        if func is None:
            return exc.HTTPNotFound()
        response = func(self, req)
        return response


class Middleware(object):

    @classmethod
    def factory(cls, application):
        return cls(application)

    def __init__(self, application):
        self.application = application

    @dec.wsgify
    def __call__(self, req):
        response = self.process_request(req)
        if response:
            return response
        response = req.get_response(self.application)
        return self.process_response(response)

    def process_request(self, req):
        """Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.

        """
        return None

    def process_response(self, response):
        """Do whatever you'd like to the response."""
        return response


class Response(Resp):
    pass
