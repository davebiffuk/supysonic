#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import binascii

from .apitestbase import ApiTestBase

class UserTestCase(ApiTestBase):
    def test_get_user(self):
        # missing username
        self._make_request('getUser', error = 10)

        # non-existent user
        self._make_request('getUser', { 'username': 'non existent' }, error = 70)

        # self
        rv, child = self._make_request('getUser', { 'username': 'alice' }, tag = 'user')
        self.assertEqual(child.get('username'), 'alice')
        self.assertEqual(child.get('adminRole'), 'true')

        # other
        rv, child = self._make_request('getUser', { 'username': 'bob' }, tag = 'user')
        self.assertEqual(child.get('username'), 'bob')
        self.assertEqual(child.get('adminRole'), 'false')

        # self from non-admin
        rv, child = self._make_request('getUser', { 'u': 'bob', 'p': 'B0b', 'username': 'bob' }, tag = 'user')
        self.assertEqual(child.get('username'), 'bob')
        self.assertEqual(child.get('adminRole'), 'false')

        # other from non-admin
        self._make_request('getUser', { 'u': 'bob', 'p': 'B0b', 'username': 'alice' }, error = 50)

    def test_get_users(self):
        # non-admin
        self._make_request('getUsers', { 'u': 'bob', 'p': 'B0b' }, error = 50)

        # admin
        rv, child = self._make_request('getUsers', tag = 'users')
        self.assertEqual(len(child), 2)
        self.assertIsNotNone(self._find(child, "./user[@username='alice']"))
        self.assertIsNotNone(self._find(child, "./user[@username='bob']"))

    def test_create_user(self):
        # non admin
        self._make_request('createUser', { 'u': 'bob', 'p': 'B0b' }, error = 50)

        # missing params, testing every combination, maybe overkill
        self._make_request('createUser', error = 10)
        self._make_request('createUser', { 'username': 'user' }, error = 10)
        self._make_request('createUser', { 'password': 'pass' }, error = 10)
        self._make_request('createUser', { 'email': 'email@example.com' }, error = 10)
        self._make_request('createUser', { 'username': 'user', 'password': 'pass' }, error = 10)
        self._make_request('createUser', { 'username': 'user', 'email': 'email@example.com' }, error = 10)
        self._make_request('createUser', { 'password': 'pass', 'email': 'email@example.com' }, error = 10)

        # duplicate
        self._make_request('createUser', { 'username': 'bob', 'password': 'pass', 'email': 'me@bob.com' }, error = 0)

        # test we only got our two initial users
        rv, child = self._make_request('getUsers', tag = 'users')
        self.assertEqual(len(child), 2)

        # create users
        self._make_request('createUser', { 'username': 'charlie', 'password': 'Ch4rl1e', 'email': 'unicorn@example.com', 'adminRole': True }, skip_post = True)
        rv, child = self._make_request('getUser', { 'username': 'charlie' }, tag = 'user')
        self.assertEqual(child.get('username'), 'charlie')
        self.assertEqual(child.get('email'), 'unicorn@example.com')
        self.assertEqual(child.get('adminRole'), 'true')

        self._make_request('createUser', { 'username': 'dave', 'password': 'Dav3', 'email': 'dave@example.com' }, skip_post = True)
        rv, child = self._make_request('getUser', { 'username': 'dave' }, tag = 'user')
        self.assertEqual(child.get('username'), 'dave')
        self.assertEqual(child.get('email'), 'dave@example.com')
        self.assertEqual(child.get('adminRole'), 'false')

        rv, child = self._make_request('getUsers', tag = 'users')
        self.assertEqual(len(child), 4)

    def test_delete_user(self):
        # non admin
        self._make_request('deleteUser', { 'u': 'bob', 'p': 'B0b', 'username': 'alice' }, error = 50)

        # missing param
        self._make_request('deleteUser', error = 10)

        # non existing
        self._make_request('deleteUser', { 'username': 'charlie' }, error = 70)

        # test we still got our two initial users
        rv, child = self._make_request('getUsers', tag = 'users')
        self.assertEqual(len(child), 2)

        # delete user
        self._make_request('deleteUser', { 'username': 'bob' }, skip_post = True)
        rv, child = self._make_request('getUsers', tag = 'users')
        self.assertEqual(len(child), 1)

    def test_change_password(self):
        # missing parameter
        self._make_request('changePassword', error = 10)
        self._make_request('changePassword', { 'username': 'alice' }, error = 10)
        self._make_request('changePassword', { 'password': 'newpass' }, error = 10)

        # admin change self
        self._make_request('changePassword', { 'username': 'alice', 'password': 'newpass' }, skip_post = True)
        self._make_request('ping', error = 40)
        self._make_request('ping', { 'u': 'alice', 'p': 'newpass' })
        self._make_request('changePassword', { 'u': 'alice', 'p': 'newpass', 'username': 'alice', 'password': 'Alic3' }, skip_post = True)

        # admin change other
        self._make_request('changePassword', { 'username': 'bob', 'password': 'newbob' }, skip_post = True)
        self._make_request('ping', { 'u': 'bob', 'p': 'B0b' }, error = 40)
        self._make_request('ping', { 'u': 'bob', 'p': 'newbob' })

        # non-admin change self
        self._make_request('changePassword', { 'u': 'bob', 'p': 'newbob', 'username': 'bob', 'password': 'B0b' }, skip_post = True)
        self._make_request('ping', { 'u': 'bob', 'p': 'newbob' }, error = 40)
        self._make_request('ping', { 'u': 'bob', 'p': 'B0b' })

        # non-admin change other
        self._make_request('changePassword', { 'u': 'bob', 'p': 'B0b', 'username': 'alice', 'password': 'newpass' }, skip_post = True, error = 50)
        self._make_request('ping', { 'u': 'alice', 'p': 'newpass' }, error = 40)
        self._make_request('ping')

        # change non existing
        self._make_request('changePassword', { 'username': 'nonexsistent', 'password': 'pass' }, error = 70)

        # non ASCII chars
        self._make_request('changePassword', { 'username': 'alice', 'password': 'новыйпароль' }, skip_post = True)
        self._make_request('ping', { 'u': 'alice', 'p': 'новыйпароль' })
        self._make_request('changePassword', { 'username': 'alice', 'password': 'Alic3', 'u': 'alice', 'p': 'новыйпароль' }, skip_post = True)

        # non ASCII in hex encoded password
        self._make_request('changePassword', { 'username': 'alice', 'password': 'enc:' + binascii.hexlify('новыйпароль') }, skip_post = True)
        self._make_request('ping', { 'u': 'alice', 'p': 'новыйпароль' })

        # new password starting with 'enc:' followed by non hex chars
        self._make_request('changePassword', { 'username': 'alice', 'password': 'enc:randomstring', 'u': 'alice', 'p': 'новыйпароль' }, skip_post = True)
        self._make_request('ping', { 'u': 'alice', 'p': 'enc:randomstring' })

if __name__ == '__main__':
    unittest.main()

