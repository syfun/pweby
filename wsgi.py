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
from utils import is_app
from mapper import Mapper

import errno
import time
import socket

import eventlet
import greenlet

from log import logger


class Server(object):
    """Provides ability to launch API from a 'paste' configuration."""
    default_pool_size = 1000
    max_header_line = 8192

    def __init__(self, name, app, host=None, port=None, pool_size=None,
                 protocol=eventlet.wsgi.HttpProtocol, backlog=128):
        """Initialize, but do not start, a WSGI server.

        :param name: Pretty name for logging.
        :param app: The WSGI application to serve.
        :param host: IP address to serve the application.
        :param port: Port number to server the application.
        :param pool_size: Maximum number of eventlets to spawn concurrently.
        :returns: None

        """
        # Allow operators to customize http requests max header line size.
        eventlet.wsgi.MAX_HEADER_LINE = self.max_header_line
        self.name = name
        self.app = app
        self._host = host or "0.0.0.0"
        self._port = port or 0
        self._server = None
        self._protocol = protocol
        self._pool = eventlet.GreenPool(pool_size or self.default_pool_size)
        #self._logger = logging.getLogger("eventlet.wsgi.server")
        #self._wsgi_logger = logging.WritableLogger(self._logger)

        if backlog < 1:
            raise Exception('The backlog must be more than 1')
        self._socket = self._get_socket(self._host,
                                        self._port,
                                        backlog=backlog)

    # def _set_app(self, app):
    #     try:
    #         if is_app(app):
    #             self.app = MainHandler(app)
    #         elif isinstance(app, MainHandler):
    #             self.app = app
    #         else:
    #             logger.error('not a app')
    #             raise Exception()
    #     except TypeError:
    #         if isinstance(app, MainHandler):
    #             self.app = app

    def _get_socket(self, host, port, backlog):
        bind_addr = (host, port)
        # eventlet's green dns/socket module does not actually
        # support IPv6 in getaddrinfo(). We need to get around this in the
        # future or monitor upstream for a fix
        try:
            info = socket.getaddrinfo(bind_addr[0],
                                      bind_addr[1],
                                      socket.AF_UNSPEC,
                                      socket.SOCK_STREAM)[0]
            family = info[0]
            bind_addr = info[-1]
        except Exception:
            family = socket.AF_INET

        # cert_file = CONF.ssl_cert_file
        # key_file = CONF.ssl_key_file
        # ca_file = CONF.ssl_ca_file
        # use_ssl = cert_file or key_file
        #
        # if cert_file and not os.path.exists(cert_file):
        #     raise RuntimeError(_("Unable to find cert_file : %s") % cert_file)
        #
        # if ca_file and not os.path.exists(ca_file):
        #     raise RuntimeError(_("Unable to find ca_file : %s") % ca_file)
        #
        # if key_file and not os.path.exists(key_file):
        #     raise RuntimeError(_("Unable to find key_file : %s") % key_file)
        #
        # if use_ssl and (not cert_file or not key_file):
        #     raise RuntimeError(_("When running server in SSL mode, you must "
        #                          "specify both a cert_file and key_file "
        #                          "option value in your configuration file"))
        #
        # def wrap_ssl(sock):
        #     ssl_kwargs = {
        #         'server_side': True,
        #         'certfile': cert_file,
        #         'keyfile': key_file,
        #         'cert_reqs': ssl.CERT_NONE,
        #     }
        #
        #     if CONF.ssl_ca_file:
        #         ssl_kwargs['ca_certs'] = ca_file
        #         ssl_kwargs['cert_reqs'] = ssl.CERT_REQUIRED
        #
        #     return ssl.wrap_socket(sock, **ssl_kwargs)

        sock = None
        retry_until = time.time() + 30
        while not sock and time.time() < retry_until:
            try:
                sock = eventlet.listen(bind_addr,
                                       backlog=backlog,
                                       family=family)
                # if use_ssl:
                #     sock = wrap_ssl(sock)

            except socket.error as err:
                if err.args[0] != errno.EADDRINUSE:
                    raise
                eventlet.sleep(0.1)
        if not sock:
            raise RuntimeError("Could not bind to %(host)s:%(port)s "
                               "after trying for 30 seconds" %
                               {'host': host, 'port': port})
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sockets can hang around forever without keepalive
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # # This option isn't available in the OS X version of eventlet
        # if hasattr(socket, 'TCP_KEEPIDLE'):
        #     sock.setsockopt(socket.IPPROTO_TCP,
        #                     socket.TCP_KEEPIDLE,
        #                     CONF.tcp_keepidle)

        return sock

    # def start(self):
    #     """Run the blocking eventlet WSGI server.
    #
    #     :returns: None
    #
    #     """
    #     wsgi.server(self._socket, self.app)

    def _start(self):
        """Run the blocking eventlet WSGI server.

        :returns: None

        """
        eventlet.wsgi.server(self._socket,
                             self.app,
                             protocol=self._protocol,
                             custom_pool=self._pool)
                             #log=self._wsgi_logger)

    def start(self, backlog=128):
        """Start serving a WSGI application.

        :param backlog: Maximum number of queued connections.
        :returns: None
        :raises: cinder.exception.InvalidInput

        """
        self._server = eventlet.spawn(self._start)
        (self._host, self._port) = self._socket.getsockname()[0:2]
        logger.info("Started %(name)s on %(host)s:%(port)s" %
                    {'name': self.name, 'host': self.host, 'port': self.port})

    def stop(self):
        """Stop this server.

        This is not a very nice action, as currently the method by which a
        server is stopped is by killing its eventlet.

        :returns: None

        """
        logger.info("Stopping WSGI server.")
        if self._server is not None:
            # Resize pool to stop new requests from being processed
            self._pool.resize(0)
            self._server.kill()

    def wait(self):
        """Block, until the server has stopped.

        Waits on the server's eventlet to finish, then returns.

        :returns: None

        """
        try:
            if self._server is not None:
                self._server.wait()
        except greenlet.GreenletExit:
            logger.info("WSGI server has stopped.")

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


class MainHandler(object):
    """

    """
    def __init__(self, *apps):
        self.mapper = Mapper()
        self.apps = {}
        for app in apps:
            self.add_app(app)

    @dec.wsgify
    def __call__(self, req):
        result = self.mapper.match(req.path)
        if not result:
            return exc.HTTPNotFound()
        app_name, func_name = result.pop('controller').split('&&&')
        app = self.apps[app_name]
        req.environ['_func_name'] = func_name
        req.environ['_kwargs'] = result
        return req.get_response(app)

    def add_app(self, app):
        """

        :param app:
        :return:
        """
        if not is_app(app):
            logger.error('not a app')
            raise Exception()
        _app = app(self)
        self.apps[str(_app)] = _app
