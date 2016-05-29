# Namegen
A Python, Markov-chain based name generator.

Command line args (and default vals):

* entries   = 768   # How many names do we generate?
* minlength = 6     # What's the minimum name length?
* maxlength = 16    # How long should the names be kept?
* file      = ''    # What's the name of the file that we read names from?
* filter    = ''    # What is an existing list of names we do NOT want to generate?
* leven     = 1     # Minimum Levenshtein distance between the source name and generated names
* start     = ''    # Force all generated names to start with a certain term.
* dump      = ''    # Dump the mappings between groupings of a -> b in the markov list to a file
* out       = 'generatednames.txt' # Name of the output file we will write results to.
 

# Purpose

Generating names is a fun hobby for game characters or fantasy place names.  I wanted to create a name generator that allowed me to look at parts of words (or groupings in words) and reconstruct names based on both single letters, or groups of letters.

The code: `dictionary = IndividualMarkov(filedata)` can be replaced by `SplitAtTerm(filedata, delimiter_list)`,  `SplitAfterTerms(filedata, delimiter_list)`,  or `SplitBeforeTerms(filedata, delimiter_list)` so you can split around vowels or groups of letters.


# External resources:
Requires editdistance: https://pypi.python.org/pypi/editdistance
