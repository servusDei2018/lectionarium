#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Tests for :mod:`bible`
'''

# Standard imports:
import unittest

# Local imports:
import bible

class parseRefTestCase(unittest.TestCase):

    def test_None(self):
        with self.assertRaises(TypeError):
            bible.parseRef(None)

    def test_emptyString(self):
        with self.assertRaises(ValueError):
            bible.parseRef('')

    def test_singleTokenBookOnly(self):
        ref = bible.parseRef('gn')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(None, ref.verses)

    def test_twoTokenBookOnly(self):
        ref = bible.parseRef('1 samuel')
        self.assertEqual('1samuel', ref.book)
        self.assertEqual(None, ref.verses)

    def test_twoTokenBookPlus(self):
        ref = bible.parseRef('1 samuel 1:2-3:4')
        self.assertEqual('1samuel', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1, 2), bible.Point(3, 4))],
            ref.verses)

    def test_songOfSongs(self):
        '''
        This case requires that the parsing of the book tokens be
        'greedy'.

        Because 'song' is both an abbreviations for this book and the
        first word in its full name, a non-greedy approach to
        parsing-out the name of the book will leave too many tokens
        behind.
        '''

        ref = bible.parseRef('song of songs 1:2-3:4')
        self.assertEqual('songofsongs', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1, 2), bible.Point(3, 4))],
            ref.verses)

    def test_syntheticAndMinimal(self):
        '''
        This is exact same series appears in parseVersesTokenTestCase,
        but here we add the name of a book.
        '''

        ref = bible.parseRef('gn 1')
        self.assertEqual('genesis', ref.book)
        self.assertEqual([bible.Point(1)], ref.verses)

        ref = bible.parseRef('gn 1-2')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1), bible.Point(2))],
            ref.verses)

        ref = bible.parseRef('gn 1,3')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Point(1), bible.Point(3)],
            ref.verses)

        ref = bible.parseRef('gn 1-2,4')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1), bible.Point(2)), bible.Point(4)],
            ref.verses)

        ref = bible.parseRef('gn 1:1')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Point(1, 1)],
            ref.verses)

        ref = bible.parseRef('gn 1:1-2')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1, 1), bible.Point(1, 2))],
            ref.verses)

        ref = bible.parseRef('gn 1:1,3')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Point(1, 1), bible.Point(1, 3)],
            ref.verses)

        ref = bible.parseRef('gn 1:1-2,4')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1, 1), bible.Point(1, 2)), bible.Point(1, 4)],
            ref.verses)

        ref = bible.parseRef('gn 1:1-2:1')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Range(bible.Point(1, 1), bible.Point(2, 1))],
            ref.verses)

        ref = bible.parseRef('gn 1:1,2:1')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Point(1, 1), bible.Point(2, 1)],
            ref.verses)

        ref = bible.parseRef('gn 1:1,3,2:1')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Point(1, 1), bible.Point(1, 3), bible.Point(2, 1)],
            ref.verses)

        ref = bible.parseRef('gn 1:1,3-2:1')
        self.assertEqual('genesis', ref.book)
        self.assertEqual(
            [bible.Point(1, 1), bible.Range(bible.Point(1, 3), bible.Point(2, 1))],
            ref.verses)

class parseBookTokensGreedilyTestCase(unittest.TestCase):

    def test_1(self):
        bible._parseBookTokensGreedily(['foo', 'bar', 'zod'])

class BookTestCase(unittest.TestCase):

    # Here is a phony book with chapters, fabricated from excerpts of
    # genesis.txt.
    bookWithChaptersText = u'''\
1:1 In principio creavit Deus cælum et terram.
1:2 Terra autem erat inanis et vacua...
1:3 Dixitque Deus...
2:1 Igitur perfecti sunt cæli et terra...
2:2 Complevitque Deus die septimo opus suum quod fecerat...
2:3 Et benedixit diei septimo...
'''

    # Here is a phony book *without* chapters, fabricated from
    # excerpts of jude.txt.
    bookWithoutChaptersText = u'''\
1:1 Judas Jesu Christi servus...
1:2 Misericordia vobis...
1:3 Carissimi...
'''

    def test_normalName(self):
        self.assertEqual('genesis', bible.Book('Genesis', ['Gn']).normalName)

    def test_noramlAbbreviations(self):
        self.assertEqual(['gn'], bible.Book('Genesis', ['Gn']).normalAbbreviations)

    def test_matchesToken(self):
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('Genesis'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('genesis'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('GENESIS'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('GeNesIs'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('Gn'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('gn'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('GN'))
        self.assertTrue(bible.Book('Genesis', ['Gn']).matchesToken('gN'))

    def test_str(self):
        self.assertEqual('Genesis (Gn)', str(bible.Book('Genesis', ['Gn'])))

    def test_getTextAtPoint(self):
        bookWithChapters = bible.Book('withchapters', hasChapters=True)
        bookWithChapters.loadTextFromString(self.bookWithChaptersText)

        # This should return all of chapter 1.
        result = bookWithChapters._getTextAtPoint(bible.Point(1))
        self.assertEqual(
            result, [
                ((1, 1), u'In principio creavit Deus cælum et terram.'),
                ((1, 2), u'Terra autem erat inanis et vacua...'),
                ((1, 3), u'Dixitque Deus...'),
                ])

        # This should return all of chapter 2.
        result = bookWithChapters._getTextAtPoint(bible.Point(2))
        self.assertEqual(
            result, [
                ((2, 1), u'Igitur perfecti sunt cæli et terra...'),
                ((2, 2), u'Complevitque Deus die septimo opus suum quod fecerat...'),
                ((2, 3), u'Et benedixit diei septimo...'),
                ])

        # This should return verse 1:1.
        result = bookWithChapters._getTextAtPoint(bible.Point(1, 1))
        self.assertEqual(
            result, [
                ((1, 1), u'In principio creavit Deus cælum et terram.'),
                ])

        # This should return verse 1:2.
        result = bookWithChapters._getTextAtPoint(bible.Point(1, 2))
        self.assertEqual(
            result, [
                ((1, 2), u'Terra autem erat inanis et vacua...'),
                ])

        # This should return verse 2:3:
        result = bookWithChapters._getTextAtPoint(bible.Point(2, 3))
        self.assertEqual(
            result, [
                ((2, 3), u'Et benedixit diei septimo...'),
                ])

        bookWithoutChapters = bible.Book('withoutchapters', hasChapters=False)
        bookWithoutChapters.loadTextFromString(self.bookWithoutChaptersText)

        # This should return only verse 1.
        result = bookWithoutChapters._getTextAtPoint(bible.Point(1))
        self.assertEqual(
            result, [
                (1, u'Judas Jesu Christi servus...'),
                ])

        # This should return only verse 2.
        result = bookWithoutChapters._getTextAtPoint(bible.Point(2))
        self.assertEqual(
            result, [
                (2, u'Misericordia vobis...'),
                ])

        # A request for 1:2 should also return verse 2, but the
        # 'address' should have the shape of the reference.
        result = bookWithoutChapters._getTextAtPoint(bible.Point(1, 2))
        self.assertEqual(
            result, [
                ((1, 2), u'Misericordia vobis...'),
                ])

    def test_visitAllVersesInChapter(self):
        bookWithChapters = bible.Book('withchapters', hasChapters=True)
        bookWithChapters.loadTextFromString(self.bookWithChaptersText)

        # This should arrive at all verses in chapter 1.
        result = [verse for verse in \
                      bookWithChapters._visitAllVersesInChapter(1)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                (2, u'Terra autem erat inanis et vacua...'),
                (3, u'Dixitque Deus...'),
                ])

        # This should arrive at all verses in chapter 2.
        result = [verse for verse in \
                      bookWithChapters._visitAllVersesInChapter(2)]
        self.assertEqual(
            result, [
                (1, u'Igitur perfecti sunt cæli et terra...'),
                (2, u'Complevitque Deus die septimo opus suum quod fecerat...'),
                (3, u'Et benedixit diei septimo...'),
                ])

        bookWithoutChapters = bible.Book('withoutchapters', hasChapters=False)
        bookWithoutChapters.loadTextFromString(self.bookWithoutChaptersText)

        # This should arrive at all verses in chapter 1.
        result = [verse for verse in \
                      bookWithoutChapters._visitAllVersesInChapter(1)]
        self.assertEqual(
            result, [
                (1, u'Judas Jesu Christi servus...'),
                (2, u'Misericordia vobis...'),
                (3, u'Carissimi...'),
                ])

    def test_visitLastVersesInChapter(self):
        bookWithChapters = bible.Book('withchapters', hasChapters=True)
        bookWithChapters.loadTextFromString(self.bookWithChaptersText)

        # This should produce verses 1:1-3.
        result = [verse for verse in \
                      bookWithChapters._visitLastVersesInChapter(1, 1)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                (2, u'Terra autem erat inanis et vacua...'),
                (3, u'Dixitque Deus...'),
                ])

        # This should produce verses 1:2-3.
        result = [verse for verse in \
                      bookWithChapters._visitLastVersesInChapter(1, 2)]
        self.assertEqual(
            result, [
                (2, u'Terra autem erat inanis et vacua...'),
                (3, u'Dixitque Deus...'),
                ])

        # This should produces verses 1:3.
        result = [verse for verse in \
                      bookWithChapters._visitLastVersesInChapter(1, 3)]
        self.assertEqual(
            result, [
                (3, u'Dixitque Deus...'),
                ])

    def test_visitFirstVersesInChapter(self):
        bookWithChapters = bible.Book('withchapters', hasChapters=True)
        bookWithChapters.loadTextFromString(self.bookWithChaptersText)

        # This should produce verses 1:1-3.
        result = [verse for verse in \
                      bookWithChapters._visitFirstVersesInChapter(1, 1)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                ])

        # This should produce verses 1:2-3.
        result = [verse for verse in \
                      bookWithChapters._visitFirstVersesInChapter(1, 2)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                (2, u'Terra autem erat inanis et vacua...'),
                ])

        # This should produces verses 1:3.
        result = [verse for verse in \
                      bookWithChapters._visitFirstVersesInChapter(1, 3)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                (2, u'Terra autem erat inanis et vacua...'),
                (3, u'Dixitque Deus...'),
                ])

    def test_visitMiddleVersesInChapter(self):
        bookWithChapters = bible.Book('withchapters', hasChapters=True)
        bookWithChapters.loadTextFromString(self.bookWithChaptersText)

        # This should produce all three verses of chapter one.
        result = [verse for verse in \
                      bookWithChapters._visitMiddleVersesInChapter(1, 1, 3)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                (2, u'Terra autem erat inanis et vacua...'),
                (3, u'Dixitque Deus...'),
                ])

        # This should produce only verse 1.
        result = [verse for verse in \
                      bookWithChapters._visitMiddleVersesInChapter(1, 1, 1)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                ])

        # This should produce only verse 2.
        result = [verse for verse in \
                      bookWithChapters._visitMiddleVersesInChapter(1, 2, 2)]
        self.assertEqual(
            result, [
                (2, u'Terra autem erat inanis et vacua...'),
                ])

        # This should produce only verse 3.
        result = [verse for verse in \
                      bookWithChapters._visitMiddleVersesInChapter(1, 3, 3)]
        self.assertEqual(
            result, [
                (3, u'Dixitque Deus...'),
                ])

        # This should produce verses 1-2.
        result = [verse for verse in \
                      bookWithChapters._visitMiddleVersesInChapter(1, 1, 2)]
        self.assertEqual(
            result, [
                (1, u'In principio creavit Deus cælum et terram.'),
                (2, u'Terra autem erat inanis et vacua...'),
                ])

        # This should produce verses 2-3.
        result = [verse for verse in \
                      bookWithChapters._visitMiddleVersesInChapter(1, 2, 3)]
        self.assertEqual(
            result, [
                (2, u'Terra autem erat inanis et vacua...'),
                (3, u'Dixitque Deus...'),
                ])

class BibleTestCase(unittest.TestCase):

    def test_findBook(self):
        self.assertIsNotNone(bible._bible.findBook('Genesis'))
        self.assertIsNotNone(bible._bible.findBook('genesis'))
        self.assertIsNotNone(bible._bible.findBook('GENESIS'))
        self.assertIsNotNone(bible._bible.findBook('GeNeSIs'))

        self.assertIsNotNone(bible._bible.findBook('Gn'))
        self.assertIsNotNone(bible._bible.findBook('gn'))
        self.assertIsNotNone(bible._bible.findBook('GN'))
        self.assertIsNotNone(bible._bible.findBook('gN'))

class PointTestCase(unittest.TestCase):

    def test_eq(self):
        self.assertTrue(bible.Point(1) == bible.Point(1))
        self.assertTrue(bible.Point(2) == bible.Point(2))

    def test_str(self):
        self.assertEqual('1', str(bible.Point(1)))
        self.assertEqual('2', str(bible.Point(2)))
        self.assertEqual('1:2', str(bible.Point(1, 2)))

class RangeTestCase(unittest.TestCase):

    def test_eq(self):
        self.assertTrue(bible.Range(1, 2) == bible.Range(1, 2))
        self.assertTrue(
            bible.Range(bible.Point(1), bible.Point(2)) == \
                bible.Range(bible.Point(1), bible.Point(2)))

    def test_str(self):
        self.assertEqual(
            '1:2-3:4', str(bible.Range(bible.Point(1, 2), bible.Point(3, 4))))

class parseVersesTokenTestCase(unittest.TestCase):

    def test_None(self):
        with self.assertRaises(TypeError):
            bible._parseVersesToken(None)

    def test_emptyString(self):
        with self.assertRaises(ValueError):
            bible._parseVersesToken('')

    def test_syntheticAndMinimal(self):
        self.assertEqual(
            [bible.Point(1)],
            bible._parseVersesToken('1'))
        self.assertEqual(
            [bible.Range(bible.Point(1), bible.Point(2))],
            bible._parseVersesToken('1-2'))
        self.assertEqual(
            [bible.Point(1), bible.Point(3)],
            bible._parseVersesToken('1,3'))
        self.assertEqual(
            [bible.Range(bible.Point(1), bible.Point(2)), bible.Point(4)],
            bible._parseVersesToken('1-2,4'))
        self.assertEqual(
            [bible.Point(1, 1)],
            bible._parseVersesToken('1:1'))
        self.assertEqual(
            [bible.Range(bible.Point(1, 1), bible.Point(1, 2))],
            bible._parseVersesToken('1:1-2'))
        self.assertEqual(
            [bible.Point(1, 1), bible.Point(1, 3)],
            bible._parseVersesToken('1:1,3'))
        self.assertEqual(
            [bible.Range(bible.Point(1, 1), bible.Point(1, 2)), bible.Point(1, 4)],
            bible._parseVersesToken('1:1-2,4'))
        self.assertEqual(
            [bible.Range(bible.Point(1, 1), bible.Point(2, 1))],
            bible._parseVersesToken('1:1-2:1'))
        self.assertEqual(
            [bible.Point(1, 1), bible.Point(2, 1)],
            bible._parseVersesToken('1:1,2:1'))
        self.assertEqual(
            [bible.Point(1, 1), bible.Point(1, 3), bible.Point(2, 1)],
            bible._parseVersesToken('1:1,3,2:1'))
        self.assertEqual(
            [bible.Point(1, 1), bible.Range(bible.Point(1, 3), bible.Point(2, 1))],
            bible._parseVersesToken('1:1,3-2:1'))

if __name__ == '__main__':
    unittest.main()
