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

from wsgi import Application, Filter
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
                # return functools.partial(app, **res[1])
                return res
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
            return True

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


def add_filters(app, filters):
    """

    :param app:
    :param filters:
    :return:
    """
    for f in filters.reverse():
        if not isfilter(f):
            logger.error('not a middleware')
            raise Exception()
        app = f.factory(app)
    return app


def isapp(app):
    """

    :param app:
    :return:
    """
    if isinstance(app, Application) or hasattr(app, '__wsgi_app__'):
        return True
    else:
        return False


def isfilter(filter):
    if isinstance(filter, Filter):
        return True
    else:
        return False


def route(url, **kwargs):
    """
    1. @route('/')
       def myfunc(req):
           pass
    2. @route('/')
       class Myclass(Application):
           pass
    3. class Myclass(Application):
       @route('/')
       def myfunc(self, req):
           pass

    :param url:
    :param kwargs:
    :return:
    """
    def _route(app):
        @functools.wraps
        def __route(*args, **kwargs):
            app(*args, **kwargs)

        if issubclass(app, Application):
            # 2
            mapper.bind(url, app, **kwargs)
            return __route

        im_class = getattr(app, 'im_class', object)
        if issubclass(im_class, Application):
            # 3
            im_class.bind(url, app, **kwargs)
            return __route

        # 1
        if not getattr(app, '__wsgi_app__', False):
            app = wsgify(app)
            app.__wsgi_app__ = True
        mapper.bind(url, app, **kwargs)
        return __route
    return _route


def filters(filters):
    """
    1. @filters(filters)
       @route('/')
       def myfunc(req):
           pass
    2. @filters(filters)
       class Myapp(Application):
           pass
    :param filters:
    :return:
    """
    def _filter(app):
        @functools.wraps
        def __filter(*args, **kwargs):
            app(*args, **kwargs)

        if issubclass(app, Application):
            app.filters = filters
            return __filter
        if not getattr(app, '__wsgi_app__', False):
            app = add_filters(wsgify(app), filters)
            app.__wsgi_app__ = True
        return __filter
    return _filter
