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
from utils import is_wsgifunc, Application


class WSGIService(object):
    """Server class to manage a WSGI server, serving a WSGI application."""

    def __init__(self, app, host=None, port=None, filters=None):
        self.app = app
        self._host = host or '127.0.0.1'
        self._port = port or 8080
        self._socket = self._get_socket(self._host, self._port)
        self._filters = filters

    def _get_socket(self, host, port):
        bind_addr = (host, port)
        sock = eventlet.listen(bind_addr)
        return sock

    def start(self):
        """Run the blocking eventlet WSGI server.

        :returns: None

        """
        if self._filters:
            for f in self._filters:
                self.app = f.factory(self.app)
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


from utils import mapper


class MainHandler(object):
    """

    """
    def __init__(self, *apps):
        self.apps = []
        self.app_names = []
        for app in apps:
            self.add_app(app)

    @dec.wsgify
    def __call__(self, req):
        app, kwargs = mapper.match(req)
        if app is None:
            return exc.HTTPNotFound()

        if is_wsgifunc(app):
            app_name = app.__name__
        else:
            app_class = app.im_class
            app_class.func_name = app.__name__
            app_class.func_kwargs = kwargs
            app_name = app_class.__name__
        try:
            i = self.app_names.index(app_name)
        except ValueError:
            logger.error('not found app')
            raise Exception()
        else:
            return req.get_response(self.apps[i])

    def get_app(self, app):
        if is_wsgifunc(app):
            app_name = app.func.__name__
        else:
            app_class = app.func.im_class
            app_name = app_class.__name__
        try:
            i = self.app_names.index(app_name)
        except ValueError:
            logger.error('not found app')
            raise Exception()
        else:
            return self.apps[i]

    def add_app(self, app):
        if issubclass(app, Application):
            self.apps.append(app())
            self.app_names.append(app.__name__)
            return None
        if not is_wsgifunc(app):
            logger.error('not a app')
            raise Exception()
        self.apps.append(app)
        self.app_names.append(app.__name__)


