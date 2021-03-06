#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import mutagen
import os
import shutil
import tempfile
import time
import unittest

from contextlib import contextmanager
from threading import Thread

from supysonic.db import get_store, Track, Artist
from supysonic.managers.folder import FolderManager
from supysonic.watcher import SupysonicWatcher

from ..testbase import TestConfig

class WatcherTestConfig(TestConfig):
    DAEMON = {
        'wait_delay': 0.5,
        'log_file': None,
        'log_level': 'DEBUG'
    }

    def __init__(self, db_uri):
        super(WatcherTestConfig, self).__init__(False, False)
        self.BASE['database_uri'] = db_uri

class WatcherTestBase(unittest.TestCase):
    @contextmanager
    def _get_store(self):
        store = None
        try:
            store = get_store('sqlite:///' + self.__dbfile)
            yield store
            store.commit()
            store.close()
        except:
            store.rollback()
            store.close()
            raise

    def setUp(self):
        self.__dbfile = tempfile.mkstemp()[1]
        conf = WatcherTestConfig('sqlite:///' + self.__dbfile)
        self.__sleep_time = conf.DAEMON['wait_delay'] + 1

        with self._get_store() as store:
            with io.open('schema/sqlite.sql', 'r') as sql:
                schema = sql.read()
                for statement in schema.split(';'):
                    store.execute(statement)

        self.__watcher = SupysonicWatcher(conf)
        self.__thread = Thread(target = self.__watcher.run)

    def tearDown(self):
        os.unlink(self.__dbfile)

    def _start(self):
        self.__thread.start()
        time.sleep(0.2)

    def _stop(self):
        self.__watcher.stop()
        self.__thread.join()

    def _is_alive(self):
        return self.__thread.is_alive()

    def _sleep(self):
        time.sleep(self.__sleep_time)

class NothingToWatchTestCase(WatcherTestBase):
    def test_spawn_useless_watcher(self):
        self._start()
        time.sleep(0.2)
        self.assertFalse(self._is_alive())
        self._stop()

class WatcherTestCase(WatcherTestBase):
    def setUp(self):
        super(WatcherTestCase, self).setUp()
        self.__dir = tempfile.mkdtemp()
        with self._get_store() as store:
            FolderManager.add(store, 'Folder', self.__dir)
        self._start()

    def tearDown(self):
        self._stop()
        shutil.rmtree(self.__dir)
        super(WatcherTestCase, self).tearDown()

    @staticmethod
    def _tempname():
        with tempfile.NamedTemporaryFile() as f:
            return os.path.basename(f.name)

    def _temppath(self):
        return os.path.join(self.__dir, self._tempname() + '.mp3')

    def _addfile(self):
        path = self._temppath()
        shutil.copyfile('tests/assets/folder/silence.mp3', path)
        return path

    def assertTrackCountEqual(self, expected):
        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), expected)

    def test_add(self):
        self._addfile()
        self.assertTrackCountEqual(0)
        self._sleep()
        self.assertTrackCountEqual(1)

    def test_add_nowait_stop(self):
        self._addfile()
        self._stop()
        self.assertTrackCountEqual(1)

    def test_add_multiple(self):
        self._addfile()
        self._addfile()
        self._addfile()
        self.assertTrackCountEqual(0)
        self._sleep()
        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), 3)
            self.assertEqual(store.find(Artist).count(), 1)

    def test_change(self):
        path = self._addfile()
        self._sleep()

        trackid = None
        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), 1)
            self.assertEqual(store.find(Artist, Artist.name == 'Some artist').count(), 1)
            trackid = store.find(Track).one().id

        tags = mutagen.File(path, easy = True)
        tags['artist'] = 'Renamed'
        tags.save()
        self._sleep()

        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), 1)
            self.assertEqual(store.find(Artist, Artist.name == 'Some artist').count(), 0)
            self.assertEqual(store.find(Artist, Artist.name == 'Renamed').count(), 1)
            self.assertEqual(store.find(Track).one().id, trackid)

    def test_rename(self):
        path = self._addfile()
        self._sleep()

        trackid = None
        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), 1)
            trackid = store.find(Track).one().id

        newpath = self._temppath()
        shutil.move(path, newpath)
        self._sleep()

        with self._get_store() as store:
            track = store.find(Track).one()
            self.assertIsNotNone(track)
            self.assertNotEqual(track.path, path)
            self.assertEqual(track.path, newpath)
            self.assertEqual(track.id, trackid)

    def test_move_in(self):
        filename = self._tempname() + '.mp3'
        initialpath = os.path.join(tempfile.gettempdir(), filename)
        shutil.copyfile('tests/assets/folder/silence.mp3', initialpath)
        shutil.move(initialpath, os.path.join(self.__dir, filename))
        self._sleep()
        self.assertTrackCountEqual(1)

    def test_move_out(self):
        initialpath = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        newpath = os.path.join(tempfile.gettempdir(), os.path.basename(initialpath))
        shutil.move(initialpath, newpath)
        self._sleep()
        self.assertTrackCountEqual(0)

        os.unlink(newpath)

    def test_delete(self):
        path = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        os.unlink(path)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_add_delete(self):
        path = self._addfile()
        os.unlink(path)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_add_rename(self):
        path = self._addfile()
        shutil.move(path, self._temppath())
        self._sleep()
        self.assertTrackCountEqual(1)

    def test_rename_delete(self):
        path = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        newpath = self._temppath()
        shutil.move(path, newpath)
        os.unlink(newpath)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_add_rename_delete(self):
        path = self._addfile()
        newpath = self._temppath()
        shutil.move(path, newpath)
        os.unlink(newpath)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_rename_rename(self):
        path = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        newpath = self._temppath()
        finalpath = self._temppath()
        shutil.move(path, newpath)
        shutil.move(newpath, finalpath)
        self._sleep()
        self.assertTrackCountEqual(1)

def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(NothingToWatchTestCase))
    suite.addTest(unittest.makeSuite(WatcherTestCase))

    return suite

if __name__ == '__main__':
    unittest.main()

