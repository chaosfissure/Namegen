# Namegen
A Python, Markov-chain based name generator.  At the minimum, it requires an input file containing a list of names to run.

# Namegen_Syllable

This was more of an experimental script to try using markov chains with syllables and reconstructing them into words. However, the variations of methods and segmentation positions in `Namegen` still appear to yield higher quality results. It's similar to `Namegen` in requiring an input file, but expects input in a certain format:

```
name1
  <whitespace> <space-delimited syllabification of name 1>
		<whitespace> <alternate space-delimited syllabification of name 1>
name2
  <ect...>
```


# Namegen_Utils
Basically the brains behind the Markov Chain construction and generation, as well as some utility functions used among the other files in this group of scripts.

# Corpify
A script I use to try finding how a word breaks down into syllables so I can append syllables to names in a text file. Namely, it's a utility fueling `Namegen_Syllable`.
 

# Purpose

Generating names is a fun hobby for game characters or fantasy place names.  I wanted to create a name generator that allowed me to look at parts of words (or groupings in words) and reconstruct names based on both single letters, or groups of letters.

# External Requirements:

`Corpify` and `Namegen_Syllable` require NLTK's cmudict corpus:
```
python -m pip install nltk
python -c "import nltk; nltk.download('cmudict')"
```
