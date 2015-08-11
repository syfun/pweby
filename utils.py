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
from copy import deepcopy
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
                #return functools.partial(app, **res[1])
                return app, res[1]
            continue
        return None, {}


mapper = Mapper()


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
        self._requirements = kwargs.get('requirements', None)
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
        if len(elements) < self._len:
            return False
        kwargs = {}
        for ele1, ele2 in zip(elements, self._elements):
            # example: user, user
            if ele1 == ele2:
                continue
            if ele2.startswith('<') and ele2.endswith('>'):
                ele2 = ele2.lstrip('<').rstrip('>')
                if ele2 not in self._requirements.keys():
                    # example: user, <user>
                    kwargs[ele2] = ele1
                    continue
                m = re.match(self._requirements[ele2], ele1)
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

    def __new__(cls, *args, **kwargs):
        app = super(Application, cls).__new__(cls)
        app._set_mapper()
        return add_filters(app, cls.filters)

    @wsgify
    def __call__(self, req):
        if self.func_name is None:
            app, kwargs = mapper.match(req)
            if app is None:
                logger.error('404')
                return exc.HTTPNotFound()
            self.func_name = app.func.__name__
        func = getattr(self, self.func_name)
        return func(req, **self.func_kwargs)

    @classmethod
    def _set_mapper(cls):
        for _, func in cls.__dict__.items():
            url = getattr(func, '__url', None)
            if url:
                mapper.bind(url, func)


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
    if isinstance(app, Application) or is_appfunc(app):
        return True
    else:
        return False


def is_filter(filter):
    if issubclass(filter, Filter):
        return True
    else:
        return False


is_wsgifunc = lambda func: hasattr(func, '__wsgi_app__')


# def is_appfunc(func):
#     return hasattr(func, '__wsgi_app')
def check_url(url):
    """

    :param url:
    :return:
    """
    return True


WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__',
                       '__url', '__kwargs')


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
        func.__url = url
        func.__kwargs = kwargs

        @functools.wraps(func, assigned=WRAPPER_ASSIGNMENTS)
        def __route(*args, **kwargs):
            return func(*args, **kwargs)

        return __route
    return _route


def filters(filters):
    """
    @filters(filters)
       @route('/')
       def myfunc(req):
           pass

    :param filters:
    :return:
    """
    def _filter(func):
        if not is_wsgifunc(func):
            func = add_filters(wsgify(func), filters)
            func.__wsgi_app__ = True

        @functools.wraps(func)
        def __filter(*args, **kwargs):
            func(*args, **kwargs)

        return __filter
    return _filter
