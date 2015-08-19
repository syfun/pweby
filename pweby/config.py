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

import yaml


class Config(object):

    def __init__(self):
        self.conf = {}

    def __getattr__(self, item):
        return self.conf.get(item, None)


CONF = Config()


def set_config(config_file=None, config_json=None):
    if config_file:
        with open(config_file) as f:
            yml = yaml.load(f)
            CONF.conf.update(yml)
    if config_json:
        CONF.conf.update(config_json)
    return CONF
