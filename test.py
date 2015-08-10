#!/usr/bin/env python
# coding=utf8


class A(object):
    def __new__(cls, *args, **kwargs):
        instance = object.__new__(cls)
        instance.a = 3
        return instance

    def __init__(self, b):
        self.b = b

a = A(2)
print a.a, a.b