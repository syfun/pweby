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

import errno
import functools
import gc
import os
import pprint
import socket
import sys
import threading
import time
import traceback


import eventlet
from eventlet import backdoor, event, greenpool, greenthread
import greenlet
from webob.dec import wsgify

from pweby import log as logging


LOG = logging.getLogger(__name__)


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
                LOG.error('not a middleware')
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


_ts = lambda: time.time()


class LoopingCallDone(Exception):
    """Exception to break out and stop a LoopingCallBase.

    The poll-function passed to LoopingCallBase can raise this exception to
    break out of the loop normally. This is somewhat analogous to
    StopIteration.

    An optional return-value can be included as the argument to the exception;
    this return-value will be returned by LoopingCallBase.wait()

    """

    def __init__(self, retvalue=True):
        """:param retvalue: Value that LoopingCallBase.wait() should return."""
        self.retvalue = retvalue


class LoopingCallBase(object):
    def __init__(self, f=None, *args, **kw):
        self.args = args
        self.kw = kw
        self.f = f
        self._running = False
        self.done = None

    def stop(self):
        self._running = False

    def wait(self):
        return self.done.wait()


class FixedIntervalLoopingCall(LoopingCallBase):
    """A fixed interval looping call."""

    def start(self, interval, initial_delay=None):
        self._running = True
        done = event.Event()

        def _inner():
            if initial_delay:
                greenthread.sleep(initial_delay)

            try:
                while self._running:
                    start = _ts()
                    self.f(*self.args, **self.kw)
                    end = _ts()
                    if not self._running:
                        break
                    delay = end - start - interval
                    if delay > 0:
                        LOG.warn('task %(func_name)s run outlasted '
                                     'interval by %(delay).2f sec',
                                 {'func_name': repr(self.f), 'delay': delay})
                    greenthread.sleep(-delay if delay < 0 else 0)
            except LoopingCallDone as e:
                self.stop()
                done.send(e.retvalue)
            except Exception:
                LOG.exception('in fixed duration looping call')
                done.send_exception(*sys.exc_info())
                return
            else:
                done.send(True)

        self.done = done

        greenthread.spawn_n(_inner)
        return self.done


class DynamicLoopingCall(LoopingCallBase):
    """A looping call which sleeps until the next known event.

    The function called should return how long to sleep for before being
    called again.
    """

    def start(self, initial_delay=None, periodic_interval_max=None):
        self._running = True
        done = event.Event()

        def _inner():
            if initial_delay:
                greenthread.sleep(initial_delay)

            try:
                while self._running:
                    idle = self.f(*self.args, **self.kw)
                    if not self._running:
                        break

                    if periodic_interval_max is not None:
                        idle = min(idle, periodic_interval_max)
                    LOG.debug('Dynamic looping call %(func_name)s sleeping '
                              'for %(idle).02f seconds',
                              {'func_name': repr(self.f), 'idle': idle})
                    greenthread.sleep(idle)
            except LoopingCallDone as e:
                self.stop()
                done.send(e.retvalue)
            except Exception:
                LOG.exception('in dynamic looping call')
                done.send_exception(*sys.exc_info())
                return
            else:
                done.send(True)

        self.done = done

        greenthread.spawn(_inner)
        return self.done


def _thread_done(gt, *args, **kwargs):
    """Callback function to be passed to GreenThread.link() when we spawn()
    Calls the :class:`ThreadGroup` to notify if.

    """
    kwargs['group'].thread_done(kwargs['thread'])


class Thread(object):
    """Wrapper around a greenthread, that holds a reference to the
    :class:`ThreadGroup`. The Thread will notify the :class:`ThreadGroup` when
    it has done so it can be removed from the threads list.
    """
    def __init__(self, thread, group):
        self.thread = thread
        self.thread.link(_thread_done, group=group, thread=self)

    def stop(self):
        self.thread.kill()

    def wait(self):
        return self.thread.wait()

    def link(self, func, *args, **kwargs):
        self.thread.link(func, *args, **kwargs)


class ThreadGroup(object):
    """The point of the ThreadGroup class is to:

    * keep track of timers and greenthreads (making it easier to stop them
      when need be).
    * provide an easy API to add timers.
    """
    def __init__(self, thread_pool_size=10):
        self.pool = greenpool.GreenPool(thread_pool_size)
        self.threads = []
        self.timers = []

    def add_dynamic_timer(self, callback, initial_delay=None,
                          periodic_interval_max=None, *args, **kwargs):
        timer = DynamicLoopingCall(callback, *args, **kwargs)
        timer.start(initial_delay=initial_delay,
                    periodic_interval_max=periodic_interval_max)
        self.timers.append(timer)

    def add_timer(self, interval, callback, initial_delay=None,
                  *args, **kwargs):
        pulse = FixedIntervalLoopingCall(callback, *args, **kwargs)
        pulse.start(interval=interval,
                    initial_delay=initial_delay)
        self.timers.append(pulse)

    def add_thread(self, callback, *args, **kwargs):
        gt = self.pool.spawn(callback, *args, **kwargs)
        th = Thread(gt, self)
        self.threads.append(th)
        return th

    def thread_done(self, thread):
        self.threads.remove(thread)

    def _stop_threads(self):
        current = threading.current_thread()

        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x is current:
                # don't kill the current thread.
                continue
            try:
                x.stop()
            except Exception as ex:
                LOG.exception(ex)

    def stop_timers(self):
        for x in self.timers:
            try:
                x.stop()
            except Exception as ex:
                LOG.exception(ex)
        self.timers = []

    def stop(self, graceful=False):
        """stop function has the option of graceful=True/False.

        * In case of graceful=True, wait for all threads to be finished.
          Never kill threads.
        * In case of graceful=False, kill threads immediately.
        """
        self.stop_timers()
        if graceful:
            # In case of graceful=True, wait for all threads to be
            # finished, never kill threads
            self.wait()
        else:
            # In case of graceful=False(Default), kill threads
            # immediately
            self._stop_threads()

    def wait(self):
        for x in self.timers:
            try:
                x.wait()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)
        current = threading.current_thread()

        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x is current:
                continue
            try:
                x.wait()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)


def _abstractify(socket_name):
    if socket_name.startswith('@'):
        # abstract namespace socket
        socket_name = '\0%s' % socket_name[1:]
    return socket_name


def _sd_notify(unset_env, msg):
    notify_socket = os.getenv('NOTIFY_SOCKET')
    if notify_socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.connect(_abstractify(notify_socket))
            sock.sendall(msg)
            if unset_env:
                del os.environ['NOTIFY_SOCKET']
        except EnvironmentError:
            LOG.debug("Systemd notification failed", exc_info=True)
        finally:
            sock.close()


def notify_once():
    """Send notification once to Systemd that service is ready.

    Systemd sets NOTIFY_SOCKET environment variable with the name of the
    socket listening for notifications from services.
    This method removes the NOTIFY_SOCKET environment variable to ensure
    notification is sent only once.
    """
    _sd_notify(True, 'READY=1')


class EventletBackdoorConfigValueError(Exception):
    def __init__(self, port_range, help_msg, ex):
        msg = ('Invalid backdoor_port configuration %(range)s: %(ex)s. '
               '%(help)s' %
               {'range': port_range, 'ex': ex, 'help': help_msg})
        super(EventletBackdoorConfigValueError, self).__init__(msg)
        self.port_range = port_range


def _dont_use_this():
    print("Don't use this, just disconnect instead")


def _find_objects(t):
    return [o for o in gc.get_objects() if isinstance(o, t)]


def _print_greenthreads():
    for i, gt in enumerate(_find_objects(greenlet.greenlet)):
        print(i, gt)
        traceback.print_stack(gt.gr_frame)
        print()


def _print_nativethreads():
    for threadId, stack in sys._current_frames().items():
        print(threadId)
        traceback.print_stack(stack)
        print()


help_for_backdoor_port = (
    "Acceptable values are 0, <port>, and <start>:<end>, where 0 results "
    "in listening on a random tcp port number; <port> results in listening "
    "on the specified port number (and not enabling backdoor if that port "
    "is in use); and <start>:<end> results in listening on the smallest "
    "unused port number within the specified range of port numbers.  The "
    "chosen port is displayed in the service's log file.")


def _parse_port_range(port_range):
    if ':' not in port_range:
        start, end = port_range, port_range
    else:
        start, end = port_range.split(':', 1)
    try:
        start, end = int(start), int(end)
        if end < start:
            raise ValueError
        return start, end
    except ValueError as ex:
        raise EventletBackdoorConfigValueError(port_range, ex,
                                               help_for_backdoor_port)


def _listen(host, start_port, end_port, listen_func):
    try_port = start_port
    while True:
        try:
            return listen_func((host, try_port))
        except socket.error as exc:
            if (exc.errno != errno.EADDRINUSE or
               try_port >= end_port):
                raise
            try_port += 1


def initialize_if_enabled():
    backdoor_locals = {
        'exit': _dont_use_this,      # So we don't exit the entire process
        'quit': _dont_use_this,      # So we don't exit the entire process
        'fo': _find_objects,
        'pgt': _print_greenthreads,
        'pnt': _print_nativethreads,
    }

    backdoor_port = None
    if backdoor_port is None:
        return None

    start_port, end_port = _parse_port_range(str(backdoor_port))

    # NOTE(johannes): The standard sys.displayhook will print the value of
    # the last expression and set it to __builtin__._, which overwrites
    # the __builtin__._ that gettext sets. Let's switch to using pprint
    # since it won't interact poorly with gettext, and it's easier to
    # read the output too.
    def displayhook(val):
        if val is not None:
            pprint.pprint(val)
    sys.displayhook = displayhook

    sock = _listen('localhost', start_port, end_port, eventlet.listen)

    # In the case of backdoor port being zero, a port number is assigned by
    # listen().  In any case, pull the port number out here.
    port = sock.getsockname()[1]
    LOG.info(
        'Eventlet backdoor listening on %(port)s for process %(pid)d' %
        {'port': port, 'pid': os.getpid()}
    )
    eventlet.spawn_n(eventlet.backdoor.backdoor_server, sock,
                     locals=backdoor_locals)
    return port
