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

import logging
from logging import config, LoggerAdapter

import six


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'default': {
            'format': '%(asctime)s-%(levelname)s-%(name)s-%(message)s'
        },
    },
    'root': {
        'level': 'DEBUG',
    },
}

config.dictConfig(LOGGING)


class ContextAdapter(LoggerAdapter):

    def __init__(self, logger, name):
        self.logger = logger
        self.name = name

    def process(self, msg, kwargs):
        # If msg is not unicode, coerce it into unicode.
        if not isinstance(msg, six.text_type):
            msg = six.text_type(msg)
        return msg, kwargs


_loggers = {}


def getLogger(name='unknown'):
    if name not in _loggers:
        _loggers[name] = ContextAdapter(logging.getLogger(name), name)
    return _loggers[name]