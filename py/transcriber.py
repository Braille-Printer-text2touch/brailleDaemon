import tomllib
from typing import Any
import re

BrailleHalfChar = tuple[bool, bool, bool]
BrailleArray = tuple[BrailleHalfChar, BrailleHalfChar]

class BrailleTranscriber:
    '''Singleton for transcribing ASCII to Unicode Braille and array representation Braille'''

    symbol_pattern = re.compile(r"({-;{{[^}]+}}-;})")

    @staticmethod
    def __toml_open_and_load(file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
        
    __instance = None
    def __new__(cls):
        if cls.__instance is not None:
            # instance already exists, don't do anything
            return cls.__instance
        
        cls.__instance = super(BrailleTranscriber, cls).__new__(cls)

        # set up class variables
        cls.BRAILLE_JUMP = "⠀⠮⠐⠼⠫⠩⠯⠄⠷⠾⠡⠬⠠⠤⠨⠌⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔⠱⠰⠣⠿⠜⠹⠈⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵⠪⠳⠻⠘⠸"
        cls.BRAILLE_SPECIAL_WORDS   = cls.__toml_open_and_load("../brailleTransliterations/special-words.toml")
        cls.BRAILLE_SPECIAL_SYMBOLS = cls.__toml_open_and_load("../brailleTransliterations/special-symbols.toml")
        cls.BRAILLE_SPECIAL_SUFFIXES = cls.__toml_open_and_load("../brailleTransliterations/special-suffixes.toml")

        return cls.__instance
    
    def __init__(self):
        return

    @staticmethod
    def ascii2braille(c: str) -> str:
        '''
        Takes a unicode character in the range 0x20 (SPACE) to 0x5F (underscore) and 
        returns its unicode brialle representation.

        The ASCII characters to be translated to braille exist in the range 0x20 (SPACE)
        to 0x5F (underscore), thus determining the chracter in question is a simple substraction from 0x20
        which can then be used to index a specially crafted string as a jump table

        Inputs:
            c: str, the character to transliterate
        Outputs:
            str: the transliterated braille character (unicode)
        '''
        # only uppercase characters are in the proper range
        ascii_offset = ord(c.upper()) - 0x20
        if not (0x0 <= ascii_offset <= 0x3F):
            # out of range
            raise Exception("Unsupported character")
    
        return BrailleTranscriber.BRAILLE_JUMP[ascii_offset]

    @staticmethod
    def braille2array(b: str) -> BrailleArray:
        '''
        Takes a braille unicode character and returns its array representation for 
        running the solenoids.
        
        Braille characters start at 0x2800 and, for the first 0x3F characters,
        increment by counting in binary down the left column then down the right column
        Example:
            0x101110
        is
            .
            .
            . .

        Inputs:
            b: str, the utf8 braille character to convert
        Outputs:
            BrailleArray: the character represented by two BrailleHalfChar
        '''
        braille_offset = ord(b) - 0x2800
        if not (0x0 <= braille_offset <= 0x3F):
            # out of range
            raise Exception("Unsupported character")

        return (
                (bool(braille_offset & 1 << 0), bool(braille_offset & 1 << 1), bool(braille_offset & 1 << 2)),
                (bool(braille_offset & 1 << 3), bool(braille_offset & 1 << 4), bool(braille_offset & 1 << 5))
            )

    def transliterate_string(self, s: str) -> str:
        '''
        Take a string composed of ASCII characters (0x20-0x5F) and apply Braille 
        contractions, shorthands, and punctuation.

        The string should NOT have new lines present.

        Args:
            s (string): The string to be transliterated, devoid of new lines
        Returns:
            string, the transliterated string, still in ASCII
        '''

        # do symbol transliteration first to not mess with future symbols added
        # in shortforms, numbers, etc.
        # this is just a placeholder replacement, the actual symbols are added later
        # to not interfere with the braille special words
        symbol_level_transliteration, symbol_placeholders = self.__transliterate_symbols(s)

        # handle word level transliterations
        # a "chunk" is a collection of words and symbols
        # the words should be transliterated, but not symbols
        chunks: list[str] = symbol_level_transliteration.split(" ")
        transliterated_words: list[str] = []

        for chunk in chunks:
            # parse out the actual word, not the symbols
            word_and_syms = re.split(self.symbol_pattern, chunk)
            
            
            # transliterate the chunk
            word_transliteration = [self.__transliterate_words(word) for word in word_and_syms]

            # rejoin the chunk and append it to the final output
            transliterated_words.append("".join(word_transliteration))

        transliterated_string = " ".join(transliterated_words) # add spaces between processed words

        # finally, replace the symbol placeholders with the actual symbols
        for symbol_placeholder, symbol in symbol_placeholders.items():
            # replace the placeholder with the actual symbol
            transliterated_string = re.sub(re.escape(symbol_placeholder), symbol, transliterated_string)

        return transliterated_string

    @staticmethod
    def __replace_suffixes(suffixes: dict, word: str) -> str:
        for suffix in suffixes.keys():
            if word.endswith(suffix):
                return word.removesuffix(suffix) + suffixes[suffix]
        return word
    
    @staticmethod
    def __replace_prefix(prefixes: dict, word: str) -> str:
        for prefix in prefixes.keys():
            if word.startswith(prefix):
                return word.removeprefix(prefix) + prefixes[prefix]
        return word
    
    def __transliterate_words(self, word: str) -> str:
        '''Given a word return the transliterated version of the word
        if it exists, otherwise return the word itself
        '''
        if re.match(self.symbol_pattern, word) is not None:
            # "word" is a symbol, so skip
            return word

        # handle numbers
        if word.isnumeric():
            # turn numbers into cooresponding braille alphabetic character
            # 1 => a, 2 => b, 3 => c, ... 0 => j
            # and then prefix
            numbers_as_letters = []
            for c in word:
                if c == '0':
                    letter_ascii = 0x6A # just make 0 lowercase a, it's not linear with the rest
                else:
                    letter_ascii = ord(c) - 0x31 + 0x61 # get number offset (from '1' or 0x31) and add to lowercase letter base (0x61)
                numbers_as_letters.append(chr(letter_ascii)) # turn back to character
                    
            return ('#' + "".join(numbers_as_letters)) # prefix with number prefix '#'

        # handle suffixes
        for collection in self.BRAILLE_SPECIAL_SUFFIXES.values():
            if (suffix_word := self.__replace_suffixes(collection, word)) != word:
                # if found a suffix, finish processing that word
                return suffix_word

        # handle other special words
        # collection is an inner dictionary
        for collection in self.BRAILLE_SPECIAL_WORDS.values():
            if word in collection:
                return collection[word]

        # didn't encounter any special collection words
        # if nothing else, just return the word 
        return word


    def __transliterate_symbols(self, s: str) -> tuple[str, dict[str,str]]:
        '''Individual symbol transliteration, not word level
        
        Returns
            tuple[str, dict[str,str]]: the transliterated string and a dictionary of temporary symbol replacements
        '''
        all_chars: list[str] = []
        placeholders: dict[str, str] = {}

        for c in s:
            if c in self.BRAILLE_SPECIAL_SYMBOLS:
                placeholder = self.wrap_symbol(c)
                new_c = self.BRAILLE_SPECIAL_SYMBOLS[c]

                # add a new placeholder
                # may overwrite an existing one, but that's okay
                # since the same symbol will be replaced with the same placeholder
                placeholders[placeholder] = new_c
                
                # add the placeholder to the list
                all_chars.append(placeholder)

            else:
                # character isn't a special symbol
                # check for uppercase case
                if c.isupper():
                    placeholder = self.wrap_symbol('upper')
                    placeholders[placeholder] = ',' # add comma for uppercase
                    all_chars.append(placeholder) # add comma for uppercase
                new_c = c
                all_chars.append(new_c.lower())

        return "".join(all_chars), placeholders
    
    @staticmethod
    def wrap_symbol(s: str) -> str:
        '''Simple helper. Given a string, wrap it in the symbols markings'''
        return "{-;{{" + s + "}}-;}"


def assert_equal_strings_verbose(s0: str, s1: str) -> None:
    if s0 != s1:
        raise AssertionError(f"\n\nExpected: '{s0}'\nGot: '{s1}'\n\n")

if __name__ == "__main__":
    transcriber = BrailleTranscriber()
    
    assert_equal_strings_verbose(transcriber.ascii2braille('a'), '⠁')
    assert_equal_strings_verbose(transcriber.ascii2braille('5'), '⠢')
    assert_equal_strings_verbose(transcriber.ascii2braille('&'), '⠯')

    assert_equal_strings_verbose(transcriber.braille2array('⠁'), ((1,0,0),(0,0,0)))
    assert_equal_strings_verbose(transcriber.braille2array('⠢'), ((0,1,0),(0,0,1)))
    assert_equal_strings_verbose(transcriber.braille2array('⠯'), ((1,1,1),(1,0,1)))

    assert_equal_strings_verbose(transcriber.transliterate_string("but"), "b")
    assert_equal_strings_verbose(transcriber.transliterate_string("about"), "ab")
    assert_equal_strings_verbose(transcriber.transliterate_string("themselves"), "!mvs")
    assert_equal_strings_verbose(transcriber.transliterate_string("1"), "#a")
    assert_equal_strings_verbose(transcriber.transliterate_string("190"), "#aij")
    assert_equal_strings_verbose(transcriber.transliterate_string("and"), "&")
    assert_equal_strings_verbose(transcriber.transliterate_string("his"), "8")

    assert_equal_strings_verbose(transcriber.transliterate_string("1 themselves"), "#a !mvs")
    assert_equal_strings_verbose(transcriber.transliterate_string("Hello, world!"), ",hello1 _w6")
    with open("endpoem.txt", "r") as src, open("endpoem_transliteration.txt", "r") as translit:
        for src_line, translit_line in zip(src, translit):
            # remove newlines
            src_line = src_line.strip()
            translit_line = translit_line.strip()

            assert_equal_strings_verbose(transcriber.transliterate_string(src_line), translit_line)

    print("All tests passed!")
