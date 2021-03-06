#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from supysonic.db import Folder

from .frontendtestbase import FrontendTestBase

class FolderTestCase(FrontendTestBase):
    def test_index(self):
        self._login('bob', 'B0b')
        rv = self.client.get('/folder', follow_redirects = True)
        self.assertIn('There\'s nothing much to see', rv.data)
        self.assertNotIn('Music folders', rv.data)
        self._logout()

        self._login('alice', 'Alic3')
        rv = self.client.get('/folder')
        self.assertIn('Music folders', rv.data)

    def test_add_get(self):
        self._login('bob', 'B0b')
        rv = self.client.get('/folder/add', follow_redirects = True)
        self.assertIn('There\'s nothing much to see', rv.data)
        self.assertNotIn('Add Folder', rv.data)
        self._logout()

        self._login('alice', 'Alic3')
        rv = self.client.get('/folder/add')
        self.assertIn('Add Folder', rv.data)

    def test_add_post(self):
        self._login('alice', 'Alic3')
        rv = self.client.post('/folder/add')
        self.assertIn('required', rv.data)
        rv = self.client.post('/folder/add', data = { 'name': 'name' })
        self.assertIn('required', rv.data)
        rv = self.client.post('/folder/add', data = { 'path': 'path' })
        self.assertIn('required', rv.data)
        rv = self.client.post('/folder/add', data = { 'name': 'name', 'path': 'path' })
        self.assertIn('Add Folder', rv.data)
        rv = self.client.post('/folder/add', data = { 'name': 'name', 'path': 'tests/assets' }, follow_redirects = True)
        self.assertIn('created', rv.data)
        self.assertEqual(self.store.find(Folder).count(), 1)

    def test_delete(self):
        folder = Folder()
        folder.name = 'folder'
        folder.path = 'tests/assets'
        folder.root = True
        self.store.add(folder)
        self.store.commit()

        self._login('bob', 'B0b')
        rv = self.client.get('/folder/del/' + str(folder.id), follow_redirects = True)
        self.assertIn('There\'s nothing much to see', rv.data)
        self.assertEqual(self.store.find(Folder).count(), 1)
        self._logout()

        self._login('alice', 'Alic3')
        rv = self.client.get('/folder/del/string', follow_redirects = True)
        self.assertIn('Invalid', rv.data)
        rv = self.client.get('/folder/del/' + str(uuid.uuid4()), follow_redirects = True)
        self.assertIn('No such folder', rv.data)
        rv = self.client.get('/folder/del/' + str(folder.id), follow_redirects = True)
        self.assertIn('Music folders', rv.data)
        self.assertEqual(self.store.find(Folder).count(), 0)

    def test_scan(self):
        folder = Folder()
        folder.name = 'folder'
        folder.path = 'tests/assets'
        folder.root = True
        self.store.add(folder)
        self.store.commit()
        self._login('alice', 'Alic3')

        rv = self.client.get('/folder/scan/string', follow_redirects = True)
        self.assertIn('Invalid', rv.data)
        rv = self.client.get('/folder/scan/' + str(uuid.uuid4()), follow_redirects = True)
        self.assertIn('No such folder', rv.data)
        rv = self.client.get('/folder/scan/' + str(folder.id), follow_redirects = True)
        self.assertIn('Added', rv.data)
        self.assertIn('Deleted', rv.data)
        rv = self.client.get('/folder/scan', follow_redirects = True)
        self.assertIn('Added', rv.data)
        self.assertIn('Deleted', rv.data)

if __name__ == '__main__':
    unittest.main()

