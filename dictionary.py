"""
:author Jay Mashauri
"""
from abc import ABC
import sqlite3 as sqlite


LETTERS = "abcdefghijklmnopqrstuvwxyz"


class Dictionary(ABC):
    """Abstract class with utility functions for working with the database of
    words of a dictionary."""

    # ------------------------------------------------------------------------------- #
    # PUBLIC VARIABLES                                                                #
    # ------------------------------------------------------------------------------- #

    has_table = False

    @property
    def connection(self):
        return self._con

    @connection.setter
    def connection(self, con):
        if not con:
            raise ValueError("Invalid value assigned to connection property.")
        self._con = con

    # ------------------------------------------------------------------------------- #
    # FUNCTIONS                                                                       #
    # ------------------------------------------------------------------------------- #

    @classmethod
    def execute(cls, query, query_param_values=None):
        """Executes a given SQLite query and does not know
        about the results.
        :return ``True`` on success and ``False`` on failure
        """

        cursor = cls.connection.cursor()
        try:
            if query_param_values and isinstance(query_param_values, tuple):
                cursor.execute(query, query_param_values)
            else:
                cursor.execute(query)
        except sqlite.Error:
            cls.connection.rollback()
            return False
        else:
            cls.connection.commit()
            cursor.close()
            return True

    @classmethod
    def get_word(cls, word, column="word"):
        """Fetches a word from the dictionary.
        :return `word` or ``None``
        """
        cls.connection.row_factory = sqlite.Row
        cursor = cls.connection.cursor()
        try:
            cursor.execute("SELECT %s FROM words WHERE word = ?" % column, (word, ))
        except sqlite.OperationalError:
            return None
        else:
            results = cursor.fetchone()
            return results[column] if results else None

    @classmethod
    def word_exists(cls, word):
        """Checks if a `word` exists in the dictionary database."""
        return True if cls.get_word(word) else False

    @classmethod
    def get_words(cls, column="word"):
        """Gets all words from the dictionary as a list.
        :param column: column to fetch
        :return ``list`` of words or ``None``
        """
        words = cls.get_words_as_dicts()
        return [word[column] for word in words] if words else None

    @classmethod
    def get_words_as_dicts(cls):
        """Gets all words as a list of table entries.
        :return ``list`` of words dictionaries or ``None``
        """
        cls.connection.row_factory = sqlite.Row
        cursor = cls.connection.cursor()
        try:
            cursor.execute("SELECT * FROM words WHERE 1")
        except sqlite.OperationalError:
            return None
        else:
            results = cursor.fetchall()
            return [dict(result) for result in results] if results else None

    @classmethod
    def create_table(cls):
        """Creates the table of words in the dictionary database."""
        if not cls.has_table:
            query = "CREATE TABLE IF NOT EXISTS words(" \
                    "word TEXT(15) PRIMARY KEY COLLATE NOCASE, pos_tag TEXT(20) NOT NULL)"
            result = cls.execute(query)
            if result:
                cls.has_table = True
            return result
        return None

    @classmethod
    def add(cls, word, pos_tag=None):
        """Adds a new word into dictionary database.
        :param word: word to be added
        :param pos_tag: type of the word, e.g adjective, noun, etc
        :return ``True`` on success and ``False`` on failure
        """
        return cls.execute("INSERT INTO words(word, pos_tag) VALUES(?, ?)", (word, pos_tag))

    @classmethod
    def remove(cls, word):
        """Removes a `word` from the dictionary database.
        :return ``True`` on success and ``False`` on failure
        """
        return cls.execute("DELETE FROM words WHERE word = ?", (word, ))

    @classmethod
    def get_instance(cls):
        """:return new instance of the class with important properties initialized."""
        instance = Dictionary()
        instance.connection = cls.connection
        instance.create_table()
        return instance

    def __init__(self):
        super().__init__()
        self._con = None
