#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
For retrieving texts from Sacred Scripture

This module currently uses the Celementine Vulgate text maintained
here:

* http://vulsearch.sourceforge.net/index.html

Summary of Command-Line Interface
======================================================================

Provide a scripture citation and :mod:`bible` will write it to
``stdout``.  For example:

.. code-block:: none

    $ bible.py john 3:16
    [3:16] Sic enim Deus dilexit mundum, ut Filium suum unigenitum daret : ut omnis
    qui credit in eum, non pereat, sed habeat vitam æternam.

You can use this to experiment with and observe the behavior library
functions :func:`getVerses` and :func:`formatVersesForConsole`.

Summary of Library Interface
======================================================================

* :func:`getVerses` - Get an object representation of some verses
* :func:`formatVersesForConsole` - Format verses for display on the console

Reference
======================================================================
'''

# Standard imports:
import argparse
import itertools
import os
import re
import sys
import textwrap

# Local imports:
import books
import locs
import citations

def getVerses(query):
    '''
    Return an object representation of the verses associated with
    `query` that you can format according to your needs.

    The `query` is parsed by :func:`citations.parse`.

    The representation of the returned verses is a ``list`` of pairs.
    The first element in each pair is the **address** of a verse.  The
    second element in each pair is the **text** of the same verse.

    The address of the verse is itself a pair of integers representing
    the **chapter** and **verse** respectively.  (This will have to
    change to handle the insertions into Esther.)
    '''

    citation = citations.parse(query)
    book = books.findBook(citation.book)
    if citation.locs is None:
        # This is the citation of an entire book.
        return book.text.getAllVerses()

    return list(
        itertools.chain.from_iterable(
            book.text.getRangeOfVerses(addrRange)
            for addrRange in citation.addrRanges
            )
        )

class FormattingError(RuntimeError):
    '''
    Represents an error that has occurred during formatting.
    '''

    def __init__(self, s):
        RuntimeError.__init__(self, s)

class Paragraph(object):
    '''
    Represents a paragraph of text, either prose or poetry, and
    provides the means to format it.  (Console formatting only, at the
    moment!)
    '''

    # A wrapper for the leading paragraph of prose.
    textWrapperForProse1 = textwrap.TextWrapper(
        width=80)

    # A wrapper for second and following paragraphs of prose.
    textWrapperForProse2 = textwrap.TextWrapper(
        width=80, initial_indent='    ')

    # The ANSI sequence for 'dim' text.
    DIM = '\033[2m'

    # The ANSI sequence for 'normal brightness' text.
    NORMAL = '\033[22m'

    def __init__(self, formatting, useColor=True):
        self.formatting = formatting
        self.useColor = useColor
        self.lines = []

    def addText(self, addr, text):
        self.lines.append((addr, text))

    @property
    def isEmpty(self):
        return len(self.lines) == 0

    def formatForConsole(self, isFirst=True):
        if self.formatting == 'prose':
            return self._formatProseForConsole(isFirst)
        elif self.formatting == 'poetry':
            return self._formatPoetryForConsole()

    def _formatProseForConsole(self, isFirst):

        def formatLineOfProse(addr, text):
            if addr is None:
                addrToken = ''
            else:
                chapter, verse = addr
                if self.useColor:
                    addrToken = '%s%d:%d%s' % (
                        self.DIM, chapter, verse, self.NORMAL)
                else:
                    addrToken = '[%d:%d]' % (chapter, verse)
            return '%s %s' % (addrToken, text)

        if isFirst:
            textWrapper = self.textWrapperForProse1
        else:
            textWrapper = self.textWrapperForProse2

        return textWrapper.fill(
            ' '.join([
                    formatLineOfProse(addr, text)
                    for (addr, text)
                    in self.lines
                    ]))

    def _formatPoetryForConsole(self):

        def formatLineOfPoetry(addr, text, isFirst):
            if addr is None:
                addrToken = ''
            else:
                chapter, verse = addr
                addrToken = '[%d:%d]' % (chapter, verse)

            indentSize = (12 if isFirst else 16)
            addrToken = '%-*s' % (indentSize, addrToken)

            if self.useColor:
                addrToken = addrToken.replace('[', self.DIM)
                addrToken = addrToken.replace(']', self.NORMAL + '  ')

            return '%s%s' % (addrToken, text)

        return '\n'.join([
                formatLineOfPoetry(addr, text, index == 0)
                for index, (addr, text) in
                enumerate(self.lines)
                ])

class ConsoleVerseFormatter(object):
    '''
    Convert a list of `verses` to a formatted string that is readable
    on the console.

    The expected format of `verses` is the same as that returned by
    :func:`getVerses`.
    '''

    def __init__(self):
        self._useColor = True
        self.paragraphs = []
        self.verseAddr = None

    @property
    def useColor(self):
        '''
        ``True`` to insert color escape sequences, otherwise ``False``
        '''

        return self._useColor

    @useColor.setter
    def useColor(self, newValue):
        self._useColor = newValue

    @property
    def currentParagraphIsProse(self):
        '''
        ``True`` if the current paragraph is formatted as prose.
        '''

        return len(self.paragraphs) > 0 and \
            self.paragraphs[-1].formatting == 'prose'

    @property
    def currentParagraphIsNotProse(self):
        '''
        ``True`` if the current paragraph is formatted as prose.
        '''

        return len(self.paragraphs) > 0 and \
            self.paragraphs[-1].formatting != 'prose'

    @property
    def currentParagraphIsPoetry(self):
        '''
        ``True`` if the current paragraph is formatted as poetry.
        '''

        return len(self.paragraphs) > 0 and \
            self.paragraphs[-1].formatting == 'poetry'

    @property
    def currentParagraphIsNotPoetry(self):
        '''
        ``True`` if the current paragraph is formatted as poetry.
        '''

        return len(self.paragraphs) > 0 and \
            self.paragraphs[-1].formatting != 'poetry'

    def addTextToCurrentParagraph(self, text):
        '''
        Add `text` to the current paragraph.

        Unless `text` is the empty string, then do nothing.

        If there is no current paragraph, create a new paragraph of
        prose and add the text there.

        Forget `verseAddr` so we don't add more than once.
        '''

        if len(text) > 0:
            if len(self.paragraphs) == 0:
                self.paragraphs.append(Paragraph('prose', self.useColor))
            self.paragraphs[-1].addText(self.verseAddr, text)
            self.verseAddr = None

    def formatVerses(self, verses):
        '''
        Return the `verses` as a formatted, ready-to-display string.
        '''

        # Allocate the verses to paragraphs.
        for verseAddr, verseText in verses:
            self.verseAddr = verseAddr
            self._formatVerse(verseText)

        # Trim the trailing empty paragraph (if there is one).
        if self.paragraphs[-1].isEmpty:
            self.paragraphs.pop()

    @property
    def formattedText(self):
        return '\n'.join([
                paragraph.formatForConsole(index == 0)
                for index, paragraph
                in enumerate(self.paragraphs)
                ]) + '\n'

    def _formatVerse(self, verseText):
        '''
        Update `paragraphs` with the content of `verseAddr` and
        `verseText` while observing formatting metacharacters that appear
        in the `verseText`.
        '''

        metaCharRegex = r'[\[\]/\\]'

        matchResult = re.search(metaCharRegex, verseText)
        while matchResult is not None:
            # Capture everything up to the metacharacter in
            # `verseTextSegment`.
            verseTextSegment = verseText[:matchResult.start()].strip()

            metaChar = verseText[matchResult.start()]
            if metaChar == '[':
                self._handlePoetryBegin(verseTextSegment)
            elif metaChar == ']':
                self._handlePoetryEnd(verseTextSegment)
            elif metaChar == '/':
                self._handlePoetryLineBreak(verseTextSegment)
            elif metaChar == '\\':
                self._handleParagraphBreak(verseTextSegment)

            # Discard the portion of `verseText` up to and including
            # the metacharacter (the part we just handled) and attempt
            # to match again.
            verseText = verseText[matchResult.start() + 1:].strip()
            matchResult = re.search(metaCharRegex, verseText)

        # Everything that remains of the current `verseText` should be
        # committed to the current paragraph.
        self.addTextToCurrentParagraph(verseText)

    def _handlePoetryBegin(self, verseTextSegment):
        # This is a request to commit the current `verseTextSegment`
        # to the current paragraph and start a new paragraph with
        # poetry formatting.
        if self.currentParagraphIsPoetry:
            raise FormattingError(
                'Saw "[" inside of poetry!')

        self.addTextToCurrentParagraph(verseTextSegment)

        # This is here for the transition from Baruch 3:38 to 4:1.
        # Verse 3:38 terminates a paragraph of poetry, causing us to
        # add an empty paragraph of prose.  Then we see the beginning
        # of poetry in verse 4:1 and start a new paragraph of poetry.
        # We don't want the interleaving paragraph of prose.
        if len(self.paragraphs) > 0:
            if self.paragraphs[-1].isEmpty:
                self.paragraphs.pop()

        self.paragraphs.append(Paragraph('poetry', self.useColor))

    def _handlePoetryEnd(self, verseTextSegment):
        # This is a request to commit the current `verseTextSegment`
        # to the current paragraph, to start a new paragraph, and to
        # exit poetry formatting.
        if self.currentParagraphIsProse:
            raise FormattingError(
                'Saw "]" inside of prose!')

        self.addTextToCurrentParagraph(verseTextSegment)

        self.paragraphs.append(Paragraph('prose', self.useColor))

    def _handlePoetryLineBreak(self, verseTextSegment):
        # Assuming poetry formatting, this means a line break.  Add
        # the `verseTextSegment` to the current paragraph.
        if self.currentParagraphIsNotPoetry:
            # The first reading for all-souls-1 (Jb 19:1,23-27) has
            # precisely this thing, so it must be legit.
            #
            # raise FormattingError(
            #     'Saw "/" outside of poetry!')
            self.paragraphs.append(Paragraph('poetry', self.useColor))

        self.addTextToCurrentParagraph(verseTextSegment)

    def _handleParagraphBreak(self, verseTextSegment):
        # Assuming prose formatting, this means a paragraph break.
        # Commit the current `verseTextSegment` to the current
        # paragraph and start a new paragraph.
        if self.currentParagraphIsNotProse:
            raise FormattingError(
                'Saw "\\" outside of prose!')

        self.addTextToCurrentParagraph(verseTextSegment)

        # This is conditional for the sake of Baruch 4:4, when ends
        # poetry AND a paragraph with ']\'.  We don't two empty
        # paragraphs on the end.  One is enough.
        if not self.paragraphs[-1].isEmpty:
            self.paragraphs.append(Paragraph('prose', self.useColor))

def formatVersesForConsole(verses):
    '''
    Convert a list of `verses` to a formatted string that is readable
    on the console.

    The expected format of `verses` is the same as that returned by
    :func:`getVerses`.
    '''

    verseFormatter = ConsoleVerseFormatter()
    verseFormatter.formatVerses(verses)
    return verseFormatter.formattedText

def main():
    '''
    This is the entry point to the command-line interface.
    '''

    args = _CommandLineParser().parse()

    if len(args.citations) > 0:
        verses = getVerses(' '.join(args.citations))
        sys.stdout.write(formatVersesForConsole(verses))
    elif args.exportFolderPath is not None:
        _HTMLBibleExporter(args.exportFolderPath).export()

class _CommandLineParser(argparse.ArgumentParser):

    def __init__(self):
        argparse.ArgumentParser.__init__(
            self, description='The canon of Sacred Scripture in Python')
        self._configure()

    def _configure(self):
        self.add_argument(
            dest='citations',
            default=[],
            nargs='*',
            help='scripture citations')
        self.add_argument(
            '--export',
            dest='exportFolderPath',
            default=None,
            help='export the whole biblical text')

    def parse(self):
        '''
        Return an object representation of the command line.
        '''

        self.args = self.parse_args()
        self._rejectMissingCommand()
        self._rejectMultipleCommands()
        return self.args

    def _rejectMissingCommand(self):
        if (len(self.args.citations) == 0) and \
                (self.args.exportFolderPath is None):
            self.print_help()
            sys.stderr.write(
                '\nNo citations and no commands were provided.\n')
            raise SystemExit(1)

    def _rejectMultipleCommands(self):
        if (len(self.args.citations) > 0) and \
                (self.args.exportFolderPath is not None):
            self.print_help()
            sys.stderr.write(
                '\nCitations and the --export command are mutually exclusive.\n')
            raise SystemExit(1)

class _HTMLBibleExporter(object):

    def __init__(self, outputFolderPath):
        self.indexExporter = _HTMLBibleIndexExporter(outputFolderPath)
        self.bookExporter = _HTMLBibleBookExporter(outputFolderPath)

    def export(self):
        '''
        Export the entire bible as HTML, with index, to
        `outputFolderPath`.
        '''

        self.indexExporter.export()
        self.bookExporter.export()

class _HTMLBibleIndexExporter(object):

    def __init__(self, outputFolderPath):
        self.outputFolderPath = outputFolderPath

    def export(self):
        outputFilePath = os.path.join(self.outputFolderPath, 'index.html')

        with open(outputFilePath, 'w') as outputFile:
            self._writeIndexHead(outputFile)
            self._writeIndexBody(outputFile)
            self._writeIndexFoot(outputFile)

    def _writeIndexHead(self, outputFile):
        outputFile.write('''\
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Vulgata Clementina</title>
  </head>
  <body>
    <h1>Vulgata Clementina</h1>
    <hr>
''')

    def _writeIndexBody(self, outputFile):
        self._writeIndexOfTestament(
            outputFile, books._bible.otBooks, 'Vetus Testamentum')
        self._writeIndexOfTestament(
            outputFile, books._bible.ntBooks, 'Novum Testamentum')

    def _writeIndexOfTestament(self, outputFile, books, title):
        outputFile.write('''\
    <h2>%s</h2>
''' % title)

        outputFile.write('''\
    <ul>
''')
        for book in books:
            self._writeIndexOfBook(outputFile, book)
        outputFile.write('''\
    </ul>
''')

    def _writeIndexOfBook(self, outputFile, book):
        outputFile.write('''\
      <li>''')

        outputFile.write(
            '<a href="%s.html">%s</a>' % (book.normalName, book.name))

        outputFile.write('</li>\n')

    def _writeIndexFoot(self, outputFile):
        outputFile.write('''\
    <hr/>
    Text courtesty of: <a href="http://vulsearch.sourceforge.net/index.html">The Clementine Vulgate Project</a>
  </body>
</html>
''')

class _HTMLBibleBookExporter(object):

    def __init__(self, outputFolderPath):
        self.outputFolderPath = outputFolderPath

    def export(self):
        for book in books._bible.allBooks:
            self._exportBook(book)

    def _exportBook(self, book):
        outputFilePath = os.path.join(
            self.outputFolderPath, '%s.html' % book.normalName)

        with open(outputFilePath, 'w') as outputFile:
            self._writeBookHead(outputFile, book)
            self._writeBookBody(outputFile, book)
            self._writeBookFoot(outputFile, book)

    def _writeBookHead(self, outputFile, book):
        outputFile.write('''\
<html>
  <head>
    <meta charset="utf-8"/>
    <title>%s</title>
  </head>
  <body>
''' % book.name)

        outputFile.write('''\
    <h1>%s</h1>
    <hr/>
''' % book.name)

        if book.hasChapters:
            chapterNumbers = [
                '<a href="#chapter-%s">%s</a>' % (chapterKey, chapterKey)
                for chapterKey in book.text.chapterKeys
                ]
            outputFile.write('''\
    %s
    <hr/>
''' % ' | '.join(chapterNumbers))

    def _writeBookBody(self, outputFile, book):
        for chapterKey in book.text._text.keys():
            if book.hasChapters:
                outputFile.write('''\
    <h2><a name="chapter-%d">%d</a></h2>
''' % (chapterKey, chapterKey))
            verses = book.text._allVersesInChapter(chapterKey)
            for verseKey, verseText in verses:
                outputFile.write(
                    '<sup>%s</sup> %s\n' % (verseKey[-1], verseText))

    def _writeBookFoot(self, outputFile, book):
        outputFile.write('''\
    <hr/>
    Text courtesty of: <a href="http://vulsearch.sourceforge.net/index.html">The Clementine Vulgate Project</a>
  </body>
</html>
''')

if __name__ == '__main__':
    main()
