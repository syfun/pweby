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
from webob import dec, exc, Response as Resp, Request as Req

from log import logger
from utils import is_app, Mapper


class WSGIService(object):
    """Server class to manage a WSGI server, serving a WSGI application."""

    def __init__(self, app, host=None, port=None):
        if is_app(app):
            self.app = MainHandler(app)
        elif isinstance(app, MainHandler):
            self.app = app
        else:
            logger.error('not a app')
            raise Exception()
        self._host = host or '127.0.0.1'
        self._port = port or 8080
        self._socket = self._get_socket(self._host, self._port)

    def _get_socket(self, host, port):
        bind_addr = (host, port)
        sock = eventlet.listen(bind_addr)
        return sock

    def start(self):
        """Run the blocking eventlet WSGI server.

        :returns: None

        """
        wsgi.server(self._socket, self.app)

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port


class Request(Req):
    pass


class Response(Resp):
    pass


from utils import Mapper, is_app


class MainHandler(object):
    """

    """
    def __init__(self, *apps):
        self.mapper = Mapper()
        self.apps = []
        for app in apps:
            self.add_app(app)

    @dec.wsgify
    def __call__(self, req):
        _app, _kwargs = self.mapper.match(req)
        if not _app:
            return exc.HTTPNotFound()
        _app, _func_name = _app
        req.environ['_func_name'] = _func_name
        req.environ['_kwargs'] = _kwargs
        return req.get_response(_app)

    def add_app(self, app):
        """

        :param app:
        :return:
        """
        if not is_app(app):
            logger.error('not a app')
            raise Exception()
        app(self)
