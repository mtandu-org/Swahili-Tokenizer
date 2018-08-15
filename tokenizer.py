from dictionary import Dictionary as Dc
from strings import sub_indices
import nltk
import re
from sqlite3 import connect

Dc.connection = connect('dictionary.db')
di = Dc.get_instance()


WORDS = di.get_words()
DICT_WORDS = di.get_words_as_dicts()
TERMINATORS = ['.', '!', '?']
WRAPPERS = ['"', "'", ')', ']']


class Tokenizer:
    """Class that uses the dictionary to process strings for grammar checking."""

    def __init__(self):
        self.abbreviations = {}

        with open('abbrev.txt', 'r') as abbr:
            abbr = abbr.read()
            lines = re.findall(r'[^\n]+', abbr)

            for line in lines:
                matcher = re.search(r'([^\s]*) : ([^\s]*)', line)
                if matcher:
                    self.abbreviations[matcher.group(1)] = matcher.group(2)

    def sent_tokenize(self, paragraph):
        """
        Breaks a `paragraph` into sentences.

        :param paragraph:
        :return: ``list`` of sentences
        """
        end = True
        sentences = []
        while end > -1:
            end = self.find_sentence_end(paragraph)
            if end > -1:
                sentences.append(paragraph[end:].strip())
                paragraph = paragraph[:end]
        sentences.append(paragraph)
        sentences.reverse()
        return sentences

    def find_sentence_end(self, paragraph):
        """
        Finds the sentence terminator of each sentence in `paragraph`
        and returns the index of the following space character.
        If there is more than 1 sentence, the index of last space character
        after the terminator of the last sentence is returned.

        :param paragraph:
        :rtype: int
        """
        [possible_endings, contraction_locations] = [[], []]
        contractions = self.abbreviations.keys()
        sentence_terminators = TERMINATORS + [terminator + wrapper for wrapper in WRAPPERS for terminator in
                                                   TERMINATORS]
        for sentence_terminator in sentence_terminators:
            t_indices = list(sub_indices(paragraph, sentence_terminator))
            possible_endings.extend(
                ([] if not len(t_indices) else [[i, len(sentence_terminator)] for i in t_indices]))
        for contraction in contractions:
            c_indices = list(sub_indices(paragraph, contraction))
            contraction_locations.extend(([] if not len(c_indices) else [i + len(contraction) for i in c_indices]))
        possible_endings = [pe for pe in possible_endings if pe[0] + pe[1] not in contraction_locations]
        if len(paragraph) in [pe[0] + pe[1] for pe in possible_endings]:
            max_end_start = max([pe[0] for pe in possible_endings])
            possible_endings = [pe for pe in possible_endings if pe[0] != max_end_start]
        possible_endings = [pe[0] + pe[1] for pe in possible_endings if
                            sum(pe) > len(paragraph) or (sum(pe) < len(paragraph) and paragraph[sum(pe)] == ' ')]
        end = (-1 if not len(possible_endings) else max(possible_endings))
        return end

    def word_tokenize(self, sentence):
        """
        Breaks a sentence into tokens.
        Tokens may be words, sentence terminators, etc.

        :param sentence:
        :return: ``list`` of the tokens
        :raise IndexError: If the last character does not match any
            of the `TERMINATORS`.
        """
        tokens = []
        words = re.split(r'\s+', sentence)
        for word in words:
            if word in self.abbreviations:
                tokens.append(word)
            else:
                if len(word):
                    last_char = word[-1]
                    if last_char in TERMINATORS:
                        tokens.append(word[:word.index(last_char)])
                        tokens.append(last_char)
                    else:
                        tokens.append(word)
        return tokens

    def pos_tag(self, sentence):
        """
        Breaks a `sentence` into words and each word is pos-tagged.

        :param sentence:
        :return: pos-tagged sentence
        :rtype: list
        """
        tagged_sentence = []

        for word in sentence:
            pos_tag = ''
            for i in range(0, len(DICT_WORDS)):
                if word.lower() == DICT_WORDS[i]['word'].lower():
                    pos_tag = DICT_WORDS[i]['pos_tag']
                    if not pos_tag:
                        pos_tag = ''
            tagged_sentence.append((word, pos_tag))

        return tagged_sentence

    def prepare_for_nlp(self, text):
        """
        Prepares a `text` for natural language processing.

        :param text: text to be processed
        :return: pos-tagged sentences
        :rtype: list
        """
        sentences = self.sent_tokenize(text)
        sentences = [self.word_tokenize(sent) for sent in sentences]
        sentences = [self.pos_tag(sent) for sent in sentences]
        return sentences

    def chunk(self, sentence):
        """
        Separates and segments a `sentence` into its subconstituents.

        :param sentence: string terminated by any of the possible `TERMINATORS`
        :return:
        :rtype: dict
        """
        chunk_to_extract = r"""
            KE: {<E>}
            KV: {<V>(<H><N+|W>)*}
            KH: {<H>(<N+|W><KV>*<KH>*)}
            KN: {(<N+|W><KV>*<KH>*)*(<U>(<N+|W><KV>*<KH>*)*)*}
            KT: {<t|Ts|T><KN|KV|KH|KE|W>*<T>*}
            """
        phrases = {'KN': None, 'KT': None}
        kn_found = False
        try:
            parser = nltk.RegexpParser(chunk_to_extract)
            result = parser.parse(sentence)
            #result.draw()
            for subtree in result.subtrees():
                if subtree.label() == 'KN':
                    # prevent KN phrase from being overridden by sub KN phrases in KT
                    if not kn_found:
                        phrases['KN'] = ' '.join(word for word, pos in subtree.leaves())
                        kn_found = True
                if subtree.label() == 'KT':
                    phrases['KT'] = ' '.join(word for word, pos in subtree.leaves())
        except Exception as e:
            pass
        return phrases


if __name__ == "__main__":
    t = Tokenizer()
    s = 'Mama yao amekuja.'
    s2 = 'Mjomba Saidi wa Njombe amekuja.'
    s3 = 'Mjomba Saidi na Wale watu warefu wa Njombe ya baridi wamekuja kwa ndugu yao!'
    s4 = 'Mama John amemuita mume wa shangazi yake.'
    s5 = 'John alimuita mama aliyekuwa anaondoka.'
    s6 = 'Ni mzuri.'
    s7 = 'John ni mtu mzuri mwenye sura ya upole.'
    s8 = 'ni mzuri wa sura.'
    sents = t.prepare_for_nlp(s3)

    for sent in sents:
        print(t.chunk(sent))
