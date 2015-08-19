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

from jinja2 import Environment, FileSystemLoader
from pweby.wsgi import Response
from pweby.log import getLogger

LOG = getLogger(__name__)


template_path = 'templates'
env = Environment(loader=FileSystemLoader(template_path))


def render(template_name=None, **kwargs):
    if not template_name:
        LOG.error('template_name has to not be None.')
        raise Exception()
    template = env.get_template(template_name)
    source = template.render(**kwargs)
    return Response(body=source)



