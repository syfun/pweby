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

from collections import OrderedDict
import functools
import re

from webob.dec import wsgify
from webob import exc

from log import logger


class Application(object):
    """
    Base WSGI application wrapper.
    Subclasses need to implement process_request.
     """
    filters = []
    prefix = ''
    prefix_more = {}
    methods = []

    def __new__(cls, handler):
        app = super(Application, cls).__new__(cls)
        app.handler = handler
        _app = add_filters(app, cls.filters)
        for _, func in cls.__dict__.items():
            try:
                _url = getattr(func, '_url')
                _kwargs = getattr(func, '_kwargs')
            except AttributeError:
                continue
            else:
                # func's priority of request method is higher.
                _kwargs['requirements'].update(app.prefix_more)
                _kwargs['conditions']['method'] = app.methods
                controller = '%s&&&%s' % (str(_app), func.__name__)
                app.handler.mapper.connect(
                    app.prefix + _url,
                    controller=controller,
                    **_kwargs)

        return _app

    @wsgify
    def __call__(self, req):
        func_name = req.environ['_func_name']
        kwargs = req.environ['_kwargs']
        func = getattr(self, func_name)
        return func(req, **kwargs)


class Filter(object):

    @classmethod
    def factory(cls, application):
        return cls(application)

    def __init__(self, application):
        self.application = application

    @wsgify
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


def add_filters(app, filters):
    """

    :param app:
    :param filters:
    :return:
    """
    # _app = deepcopy(app)
    if filters:
        filters.reverse()
        for f in filters:
            if not is_filter(f):
                logger.error('not a middleware')
                raise Exception()
            app = f.factory(app)
    return app


def is_app(app):
    """

    :param app:
    :return:
    """
    if issubclass(app, Application):
        return True
    return False


def is_filter(filter):
    """

    :param filter:
    :return:
    """
    if issubclass(filter, Filter):
        return True
    return False


WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__',
                       '_url', '_kwargs')


def route(url, **kwargs):
    """
        class Myclass(Application):
           @route('/{year}', more={'year': R'\d{2,4}'}, methods=['GET'])
           def myfunc(self, req):
               pass

    :param url:
    :param kwargs:
    :return:
    """
    def _route(func):
        func._url = url
        func._kwargs = {}
        func._kwargs['requirements'] = kwargs.get('more', {})
        func._kwargs['conditions'] = dict(method=kwargs.get('methods', {}))

        @functools.wraps(func, assigned=WRAPPER_ASSIGNMENTS)
        def __route(*args, **kwargs):
            return func(*args, **kwargs)

        return __route
    return _route
