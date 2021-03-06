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

import time
import unittest

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase

class SearchTestCase(ApiTestBase):
    def setUp(self):
        super(SearchTestCase, self).setUp()

        root = Folder()
        root.root = True
        root.name = 'Root folder'
        root.path = 'tests/assets'
        self.store.add(root)

        for letter in 'ABC':
            folder = Folder()
            folder.name = letter + 'rtist'
            folder.path = 'tests/assets/{}rtist'.format(letter)
            folder.parent = root

            artist = Artist()
            artist.name = letter + 'rtist'

            for lether in 'AB':
                afolder = Folder()
                afolder.name = letter + lether + 'lbum'
                afolder.path = 'tests/assets/{0}rtist/{0}{1}lbum'.format(letter, lether)
                afolder.parent = folder

                album = Album()
                album.name = letter + lether + 'lbum'
                album.artist = artist

                for num, song in enumerate([ 'One', 'Two', 'Three' ]):
                    track = Track()
                    track.disc = 1
                    track.number = num
                    track.title = song
                    track.duration = 2
                    track.album = album
                    track.artist = artist
                    track.bitrate = 320
                    track.path = 'tests/assets/{0}rtist/{0}{1}lbum/{2}'.format(letter, lether, song)
                    track.content_type = 'audio/mpeg'
                    track.last_modification = 0
                    track.root_folder = root
                    track.folder = afolder
                    self.store.add(track)

        self.store.commit()

        self.assertEqual(self.store.find(Folder).count(), 10)
        self.assertEqual(self.store.find(Artist).count(), 3)
        self.assertEqual(self.store.find(Album).count(), 6)
        self.assertEqual(self.store.find(Track).count(), 18)

    def __track_as_pseudo_unique_str(self, elem):
        return elem.get('artist') + elem.get('album') + elem.get('title')

    def test_search(self):
        # invalid parameters
        self._make_request('search', { 'count': 'string' }, error = 0)
        self._make_request('search', { 'offset': 'sstring' }, error = 0)
        self._make_request('search', { 'newerThan': 'ssstring' }, error = 0)

        # no search
        self._make_request('search', error = 10)

        # non existent artist (but searched string present in other fields)
        rv, child = self._make_request('search', { 'artist': 'One' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)
        self.assertEqual(child.get('totalHits'), '0')
        self.assertEqual(child.get('offset'), '0')

        rv, child = self._make_request('search', { 'artist': 'AAlbum' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # non existent album (but search present in other fields)
        rv, child = self._make_request('search', { 'album': 'One' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        rv, child = self._make_request('search', { 'album': 'Artist' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # non existent title (but search present in other fields)
        rv, child = self._make_request('search', { 'title': 'AAlbum' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        rv, child = self._make_request('search', { 'title': 'Artist' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # non existent anything
        rv, child = self._make_request('search', { 'any': 'Chaos' }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # artist search
        rv, child = self._make_request('search', { 'artist': 'Artist' }, tag = 'searchResult')
        self.assertEqual(len(child), 1)
        self.assertEqual(child.get('totalHits'), '1')
        self.assertEqual(child[0].get('title'), 'Artist')

        rv, child = self._make_request('search', { 'artist': 'rti' }, tag = 'searchResult')
        self.assertEqual(len(child), 3)
        self.assertEqual(child.get('totalHits'), '3')

        # same as above, but created in the future
        future = int(time.time() * 1000 + 1000)
        rv, child = self._make_request('search', { 'artist': 'rti', 'newerThan': future }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # album search
        rv, child = self._make_request('search', { 'album': 'AAlbum' }, tag = 'searchResult')
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get('title'), 'AAlbum')
        self.assertEqual(child[0].get('artist'), 'Artist')

        rv, child = self._make_request('search', { 'album': 'lbu' }, tag = 'searchResult')
        self.assertEqual(len(child), 6)

        # same as above, but created in the future
        rv, child = self._make_request('search', { 'album': 'lbu', 'newerThan': future }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # song search
        rv, child = self._make_request('search', { 'title': 'One' }, tag = 'searchResult')
        self.assertEqual(len(child), 6)
        for i in range(6):
            self.assertEqual(child[i].get('title'), 'One')

        rv, child = self._make_request('search', { 'title': 'e' }, tag = 'searchResult')
        self.assertEqual(len(child), 12)

        # same as above, but created in the future
        rv, child = self._make_request('search', { 'title': 'e', 'newerThan': future }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # any field search
        rv, child = self._make_request('search', { 'any': 'r' }, tag = 'searchResult')
        self.assertEqual(len(child), 10) # root + 3 artists (*rtist)  + 6 songs (Three)

        # same as above, but created in the future
        rv, child = self._make_request('search', { 'any': 'r', 'newerThan': future }, tag = 'searchResult')
        self.assertEqual(len(child), 0)

        # paging
        songs = []
        for offset in range(0, 12, 2):
            rv, child = self._make_request('search', { 'title': 'e', 'count': 2, 'offset': offset }, tag = 'searchResult')
            self.assertEqual(len(child), 2)
            self.assertEqual(child.get('totalHits'), '12')
            self.assertEqual(child.get('offset'), str(offset))
            for song in map(self.__track_as_pseudo_unique_str, child):
                self.assertNotIn(song, songs)
                songs.append(song)

    def test_search2(self):
        # invalid parameters
        self._make_request('search2', { 'artistCount': 'string' }, error = 0)
        self._make_request('search2', { 'artistOffset': 'sstring' }, error = 0)
        self._make_request('search2', { 'albumCount': 'string' }, error = 0)
        self._make_request('search2', { 'albumOffset': 'sstring' }, error = 0)
        self._make_request('search2', { 'songCount': 'string' }, error = 0)
        self._make_request('search2', { 'songOffset': 'sstring' }, error = 0)

        # no search
        self._make_request('search2', error = 10)

        # non existent anything
        rv, child = self._make_request('search2', { 'query': 'Chaos' }, tag = 'searchResult2')
        self.assertEqual(len(child), 0)

        # artist search
        rv, child = self._make_request('search2', { 'query': 'Artist' }, tag = 'searchResult2')
        self.assertEqual(len(child), 1)
        self.assertEqual(len(self._xpath(child, './artist')), 1)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 0)
        self.assertEqual(child[0].get('name'), 'Artist')

        rv, child = self._make_request('search2', { 'query': 'rti' }, tag = 'searchResult2')
        self.assertEqual(len(child), 3)
        self.assertEqual(len(self._xpath(child, './artist')), 3)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 0)

        # album search
        rv, child = self._make_request('search2', { 'query': 'AAlbum' }, tag = 'searchResult2')
        self.assertEqual(len(child), 1)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 1)
        self.assertEqual(len(self._xpath(child, './song')), 0)
        self.assertEqual(child[0].get('title'), 'AAlbum')
        self.assertEqual(child[0].get('artist'), 'Artist')

        rv, child = self._make_request('search2', { 'query': 'lbu' }, tag = 'searchResult2')
        self.assertEqual(len(child), 6)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 6)
        self.assertEqual(len(self._xpath(child, './song')), 0)

        # song search
        rv, child = self._make_request('search2', { 'query': 'One' }, tag = 'searchResult2')
        self.assertEqual(len(child), 6)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 6)
        for i in range(6):
            self.assertEqual(child[i].get('title'), 'One')

        rv, child = self._make_request('search2', { 'query': 'e' }, tag = 'searchResult2')
        self.assertEqual(len(child), 12)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 12)

        # any field search
        rv, child = self._make_request('search2', { 'query': 'r' }, tag = 'searchResult2')
        self.assertEqual(len(child), 9)
        self.assertEqual(len(self._xpath(child, './artist')), 3)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 6)

        # paging
        artists = []
        for offset in range(0, 4, 2):
            rv, child = self._make_request('search2', { 'query': 'r', 'artistCount': 2, 'artistOffset': offset }, tag = 'searchResult2')
            names = self._xpath(child, './artist/@name')
            self.assertLessEqual(len(names), 2)
            for name in names:
                self.assertNotIn(name, artists)
                artists.append(name)

        songs = []
        for offset in range(0, 6, 2):
            rv, child = self._make_request('search2', { 'query': 'r', 'songCount': 2, 'songOffset': offset }, tag = 'searchResult2')
            elems = self._xpath(child, './song')
            self.assertEqual(len(elems), 2)
            for song in map(self.__track_as_pseudo_unique_str, elems):
                self.assertNotIn(song, songs)
                songs.append(song)

    # Almost identical as above. Test dataset (and tests) should probably be changed
    # to have folders that don't share names with artists or albums
    def test_search3(self):
        # invalid parameters
        self._make_request('search3', { 'artistCount': 'string' }, error = 0)
        self._make_request('search3', { 'artistOffset': 'sstring' }, error = 0)
        self._make_request('search3', { 'albumCount': 'string' }, error = 0)
        self._make_request('search3', { 'albumOffset': 'sstring' }, error = 0)
        self._make_request('search3', { 'songCount': 'string' }, error = 0)
        self._make_request('search3', { 'songOffset': 'sstring' }, error = 0)

        # no search
        self._make_request('search3', error = 10)

        # non existent anything
        rv, child = self._make_request('search3', { 'query': 'Chaos' }, tag = 'searchResult3')
        self.assertEqual(len(child), 0)

        # artist search
        rv, child = self._make_request('search3', { 'query': 'Artist' }, tag = 'searchResult3')
        self.assertEqual(len(child), 1)
        self.assertEqual(len(self._xpath(child, './artist')), 1)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 0)
        self.assertEqual(child[0].get('name'), 'Artist')

        rv, child = self._make_request('search3', { 'query': 'rti' }, tag = 'searchResult3')
        self.assertEqual(len(child), 3)
        self.assertEqual(len(self._xpath(child, './artist')), 3)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 0)

        # album search
        rv, child = self._make_request('search3', { 'query': 'AAlbum' }, tag = 'searchResult3')
        self.assertEqual(len(child), 1)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 1)
        self.assertEqual(len(self._xpath(child, './song')), 0)
        self.assertEqual(child[0].get('name'), 'AAlbum')
        self.assertEqual(child[0].get('artist'), 'Artist')

        rv, child = self._make_request('search3', { 'query': 'lbu' }, tag = 'searchResult3')
        self.assertEqual(len(child), 6)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 6)
        self.assertEqual(len(self._xpath(child, './song')), 0)

        # song search
        rv, child = self._make_request('search3', { 'query': 'One' }, tag = 'searchResult3')
        self.assertEqual(len(child), 6)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 6)
        for i in range(6):
            self.assertEqual(child[i].get('title'), 'One')

        rv, child = self._make_request('search3', { 'query': 'e' }, tag = 'searchResult3')
        self.assertEqual(len(child), 12)
        self.assertEqual(len(self._xpath(child, './artist')), 0)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 12)

        # any field search
        rv, child = self._make_request('search3', { 'query': 'r' }, tag = 'searchResult3')
        self.assertEqual(len(child), 9)
        self.assertEqual(len(self._xpath(child, './artist')), 3)
        self.assertEqual(len(self._xpath(child, './album')), 0)
        self.assertEqual(len(self._xpath(child, './song')), 6)

        # paging
        artists = []
        for offset in range(0, 4, 2):
            rv, child = self._make_request('search3', { 'query': 'r', 'artistCount': 2, 'artistOffset': offset }, tag = 'searchResult3')
            names = self._xpath(child, './artist/@name')
            self.assertLessEqual(len(names), 2)
            for name in names:
                self.assertNotIn(name, artists)
                artists.append(name)

        songs = []
        for offset in range(0, 6, 2):
            rv, child = self._make_request('search3', { 'query': 'r', 'songCount': 2, 'songOffset': offset }, tag = 'searchResult3')
            elems = self._xpath(child, './song')
            self.assertEqual(len(elems), 2)
            for song in map(self.__track_as_pseudo_unique_str, elems):
                self.assertNotIn(song, songs)
                songs.append(song)

if __name__ == '__main__':
    unittest.main()

