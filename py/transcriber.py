import tomllib
from typing import Any

BrailleHalfChar = tuple[bool, bool, bool]
BrailleArray = tuple[BrailleHalfChar, BrailleHalfChar]

class BrailleTranscriber:
    '''Singleton for transcribing ASCII to Unicode Braille and array representation Braille'''

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
        cls.BRAILLE_SHORTFORMS    = cls.__toml_open_and_load("../brailleTransliterations/shortforms.toml")
        cls.ALPHABETIC_WORD_SIGNS = cls.__toml_open_and_load("../brailleTransliterations/alphabetic-word-signs.toml")
        cls.STRONG_CONTRACTIONS   = cls.__toml_open_and_load("../brailleTransliterations/strong-contractions.toml")
        cls.LOWER_CONTRACTIONS    = cls.__toml_open_and_load("../brailleTransliterations/lower-contractions.toml")
        cls.DOT_56_FINAL_LETTER   = cls.__toml_open_and_load("../brailleTransliterations/dot-56.toml")
        cls.DOT_46_FINAL_LETTER   = cls.__toml_open_and_load("../brailleTransliterations/dot-46.toml")
        cls.DOT_5_WORDS           = cls.__toml_open_and_load("../brailleTransliterations/dot-5.toml")
        cls.DOT_45_WORDS          = cls.__toml_open_and_load("../brailleTransliterations/dot-45.toml")
        cls.DOT_456_WORDS         = cls.__toml_open_and_load("../brailleTransliterations/dot-456.toml")
        cls.BRAILLE_SPECIAL_SYMBOLS = cls.__toml_open_and_load("../brailleTransliterations/special-symbols.toml")

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
        symbol_level_transliteration = self.__transliterate_symbols(s.lower())

        # handle word level transliterations
        words: list[str] = symbol_level_transliteration.split(" ")
        transliterated_words: list[str] = []
        
        # handle comma starting textual line
        if len(words) > 0 and words[0].isalpha():
            transliterated_words.append(",")

        for word in words:
            # shortforms
            if word in self.BRAILLE_SHORTFORMS:
                transliterated_words.append(self.BRAILLE_SHORTFORMS[word])

            # numbers
            elif word.isnumeric():
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
                
                transliterated_words.append('#' + "".join(numbers_as_letters)) # prefix with number prefix '#'

            # alphabetic word signs
            elif word in self.ALPHABETIC_WORD_SIGNS:
                transliterated_words.append(self.ALPHABETIC_WORD_SIGNS[word])

            # contractions
            elif word in self.STRONG_CONTRACTIONS:
                transliterated_words.append(self.STRONG_CONTRACTIONS[word])
            elif word in self.LOWER_CONTRACTIONS:
                transliterated_words.append(self.LOWER_CONTRACTIONS[word])

            # final-letter combinations
            # try to replace the suffix and see if anything changed
            # if so, add the changed word
            elif (suffix_word := self.__replace_suffixes(self.DOT_56_FINAL_LETTER, word)) != word:
                transliterated_words.append(suffix_word)
            elif (suffix_word := self.__replace_suffixes(self.DOT_46_FINAL_LETTER, word)) != word:
                transliterated_words.append(suffix_word)

            # more contractions!
            elif word in self.DOT_5_WORDS:
                transliterated_words.append(self.DOT_5_WORDS[word])
            elif word in self.DOT_45_WORDS:
                transliterated_words.append(self.DOT_45_WORDS[word])
            elif word in self.DOT_456_WORDS:
                transliterated_words.append(self.DOT_456_WORDS[word])

            # if nothing else, just add the word
            else:
                transliterated_words.append(word)

        transliterated_string = " ".join(transliterated_words) # add spaces between processed words
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

    def __transliterate_symbols(self, s: str) -> str:
        all_chars = list(s)

        for index, c in enumerate(all_chars):
            if c in self.BRAILLE_SPECIAL_SYMBOLS:
                all_chars[index] = self.BRAILLE_SPECIAL_SYMBOLS[c]

        return "".join(all_chars)

if __name__ == "__main__":
    transcriber = BrailleTranscriber()
    
    assert(transcriber.ascii2braille('a') == '⠁')
    assert(transcriber.ascii2braille('5') == '⠢')
    assert(transcriber.ascii2braille('&') == '⠯')

    assert(transcriber.braille2array('⠁') == ((1,0,0),(0,0,0)))
    assert(transcriber.braille2array('⠢') == ((0,1,0),(0,0,1)))
    assert(transcriber.braille2array('⠯') == ((1,1,1),(1,0,1)))

    assert(transcriber.transliterate_string("but") == "b")
    assert(transcriber.transliterate_string("about") == "ab")
    assert(transcriber.transliterate_string("themselves") == "!mvs")
    assert(transcriber.transliterate_string("1") == "#a")
    assert(transcriber.transliterate_string("190") == "#aij")
    assert(transcriber.transliterate_string("and") == "&")
    assert(transcriber.transliterate_string("his") == "8")

    assert(transcriber.transliterate_string("1 themselves") == "#a !mvs")
    print(transcriber.transliterate_string("Hello, world!"))
    assert(transcriber.transliterate_string("Hello, world!") == ",hello1 _w6")
    with open("endpoem.txt", "r") as src, open("endpoem_transliteration.txt", "r") as translit:
        for src_line, translit_line in zip(src, translit):
            # remove newlines
            src_line = src_line.strip()
            translit_line = translit_line.strip()

            assert(transcriber.transliterate_string(src_line) == translit_line)

    print("All tests passed!")
