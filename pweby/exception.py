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

import sys

from pweby import log as logging


LOG = logging.getLogger(__name__)


class PwebyException(Exception):
    """Base Pweby Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 500
    headers = {}
    safe = False

    # make exception message format errors fatal
    fatal_exception_format_errors = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.iteritems():
                    LOG.error("%s: %s" % (name, value))
                if self.fatal_exception_format_errors:
                    raise exc_info[0], exc_info[1], exc_info[2]
                # at least get the core message out if something happened
                message = self.message

        # We put the actual message in 'msg' so that we can access
        # it, because if we try to access the message via 'message' it will be
        # overshadowed by the class' message attribute
        self.msg = message
        super(PwebyException, self).__init__(message)

    def __unicode__(self):
        return unicode(self.msg)


class Invalid(PwebyException):
    message = "Unacceptable parameters."
    code = 400


class InvalidInput(Invalid):
    message = "Invalid input received: %(reason)s"


class InvalidApplication(Invalid):
    message = "%(app)s is not a invalid wsgi application."
