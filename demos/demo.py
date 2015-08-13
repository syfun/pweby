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


from pweby.wsgi import WSGIService, Response, MainHandler
from pweby.utils import route, Application, Filter


class Filter1(Filter):
    pass


class Filter2(Filter):
    pass


class Hello1(Application):
    prefix = '/{year}/{month}'
    prefix_more = {'year': r'\d{2,4}', 'month': r'\d{1,2}'}
    filters = [Filter1, Filter2]

    @route('/{day}', more={'day': R'\d{1,2}'})
    def hello(self, req, year, month, day):
        return Response(day)


class Hello2(Application):

    @route('/index')
    def hello(self, req):
        return Response('hello world')

handler = MainHandler(Hello1, Hello2)
service = WSGIService(handler)
service.start()
