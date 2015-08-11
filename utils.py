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


class Mapper(object):

    def __init__(self):
        self.url_apps = OrderedDict()

    def bind(self, url, app, **kwargs):
        self.url_apps[Urlwrap(url, **kwargs)] = app

    def match(self, req):
        for urlwrap, app in self.url_apps.items():
            res = urlwrap.match(req)
            if res:
                return app, res[1]
            continue
        return None, {}


class Urlwrap(object):
    """

    """

    def __init__(self, url, **kwargs):
        self.url = url
        self._praser(**kwargs)

    def _praser(self, **kwargs):
        if not self.url.startswith('/'):
            raise Exception()
        self._elements = self.url.lstrip('/').split('/')
        self._method = kwargs.get('method', None)
        self._methods = kwargs.get('methods', [])
        if self._method and self._methods:
            raise Exception()
        self._add = kwargs.get('add', {})
        self._len = len(self._elements)

    def match(self, req):
        # due with method
        method = req.method
        if method != self._method and method not in self._methods:
            if self._method is not None or self._methods != []:
                return False

        path = req.path
        if path == self.url:
            return True, {}

        # if _elemets is [''], it's url is '/'. So it matches each url.
        if self._elements == ['']:
            return True, {}

        elements = path.lstrip('/').split('/')
        # if length of elements less than _len, not match.
        if len(elements) != self._len:
            return False
        kwargs = {}
        for ele1, ele2 in zip(elements, self._elements):
            # example: user, user
            if ele1 == ele2:
                continue
            if ele2.startswith('<') and ele2.endswith('>'):
                ele2 = ele2.lstrip('<').rstrip('>')
                if ele2 not in self._add.keys():
                    # example: user, <user>
                    kwargs[ele2] = ele1
                    continue
                m = re.match(self._add[ele2], ele1)
                if not m:
                    return False
                # exmaple: 2015, <year>(\d{2, 4})
                kwargs[ele2] = ele1
                continue
            return False
        return True, kwargs


class Application(object):
    """
    Base WSGI application wrapper.
    Subclasses need to implement process_request.
     """
    filters = []
    prefix = ''
    prefix_add = {}

    def __new__(cls, handler):
        app = super(Application, cls).__new__(cls)
        app.handler = handler
        prefix = app.prefix
        prefix_add = app.prefix_add
        _app = add_filters(app, cls.filters)
        for _, func in cls.__dict__.items():
            try:
                _url = getattr(func, '_url')
                _kwargs = getattr(func, '_kwargs')
            except AttributeError:
                continue
            else:
                # func's priority of request method is higher.
                prefix_add.update(_kwargs)
                app.handler.mapper.bind(prefix+_url,
                                        (_app, func.__name__),
                                        **prefix_add)

        return _app

    @wsgify
    def __call__(self, req):
        _func_name = req.environ['_func_name']
        _kwargs = req.environ['_kwargs']
        _func = getattr(self, _func_name)
        return _func(req, **_kwargs)


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


def check_url(url):
    """

    :param url:
    :return:
    """
    return True


WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__',
                       '_url', '_kwargs')


def route(url, **kwargs):
    """
    1. @route('/v1')
       def myfunc(req):
           pass

    2. class Myclass(Application):
           @route('/v1')
           def myfunc(self, req):
               pass

    :param url:
    :param kwargs:
    :return:
    """
    if not check_url(url):
        logger.error('check error')
        raise Exception()

    def _route(func):
        func._url = url
        func._kwargs = kwargs

        @functools.wraps(func, assigned=WRAPPER_ASSIGNMENTS)
        def __route(*args, **kwargs):
            return func(*args, **kwargs)

        return __route
    return _route
