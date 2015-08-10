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


class Mapper(object):

    def __init__(self):
        self.order_urls = OrderedDict()

    def route(self, url, func, **kwargs):
        self.order_urls[Urlwrap(url, **kwargs)] = func

    def match(self, req):
        for urlwrap, func in self.order_urls.items():
            res = urlwrap.match(req)
            if res:
                return functools.partial(func, **res[1])
            continue
        return None


mapper = Mapper()


class Urlwrap(object):

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
        if len(elements) != self._len:
            return False
        kwargs = {}
        for ele1, ele2 in zip(elements, self._elements):
            if ele1 == ele2:
                continue
            if ele2.startswith('<') and ele2.endswith('>'):
                ele2 = ele2.lstrip('<').rstrip('>')
                if ele2 not in self._requirements.keys():
                    kwargs[ele2] = ele1
                    continue
                m = re.match(self._requirements[ele2], ele1)
                if not m:
                    return False
                kwargs[ele2] = ele1
                continue
            return False
        return True, kwargs


def route(url, **kwargs):
    def _route(func):
        mapper.route(url, func, **kwargs)
    return _route
