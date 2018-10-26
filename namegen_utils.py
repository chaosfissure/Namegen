import random
from collections import defaultdict, deque

LOWERCASE        = 'abcdefghijklmnopqrstuvwxyz'
UPPERCASE        = LOWERCASE.upper()
VALID_LETTERS    = LOWERCASE + UPPERCASE
VALID_LETTER_SET = set(VALID_LETTERS)
NUMBERS          = set('0123456789')
VOWEL_SET        = set('aeiouy')
COMMON_LETTERS   = set('etaoinshrdlu')

def Chunk(l, s):
	'''Return sublists of elements grouped in groups of size s.'''
	for i in range(0, len(l), s):
		yield l[i:i+s]

		
def RemoveNumbers(word):
	'''Remove numbers from a word.'''
	return ''.join(letter for letter in word if letter not in NUMBERS)
	
	
def FilterLetters(word):
	'''Strip all elements from the input word that aren't in VALID_LETTER_SET.'''
	return ''.join(letter for letter in word if letter in VALID_LETTER_SET)
			
			
def ValidLines(fname):
	'''
	Returns all lines in a file that contain letters.
	All trailing whitespace is stripped from the entry.
	'''
	
	with open(fname, 'r') as f:
		for each_line in f:
			stripped = each_line.rstrip()
			if stripped:
				yield stripped

			
def ChunkSyllables(syllables):
	'''
	Group an ordered list of syllables into chunks of syllables, such that a raw list of [a, b, c] will yield the following results:
		1) [[a, b, c]]
		2) [[a], [b, c]]
		3) [[a, b], [c]]	
	'''
	
	if syllables:
	
		# Handles "[[a, b, c]]"
		yield [syllables]
	
		# Handles "[[a], [b, c]]" and "[[a, b], [c]]"
		for j in range(1, len(syllables)):
			me   = syllables[:j]
			rest = syllables[j:]
			
			for result in ChunkSyllables(rest):
				yield [me] + list(result)

				
def YieldAllFrom(*args):
	'''Given an arbitrary arglist of iterables, yield each entry for all iterables.'''
	for arg in args:
		yield from arg
			

def YieldNames(files):
	'''
	Collects and returns a list of every non-empty line read in the specified input files.
	Ignores lines considered SYLLABLES (which are denoted by leading whitespace).
	'''	
	for f in files:
		for line in ValidLines(f):
			if line.strip() == line:
				yield line
				
				
def ObtainSyllables(files, includeEmpty=False):
	'''
	Captures all names that have syllable definitions.
	
	IncludeEmpty is a utility that returns all entries, even if
	there aren't any syllables associated with them.  This can be
	useful if we want to generate syllables for these words.
	'''	
	
	words = defaultdict(set)
	
	for f in files:
	
		lastWord = None
		for line in ValidLines(f):
		
			if line.strip() == line:
				lastWord = line
				if includeEmpty:
					words[lastWord] = set()
				
			else:		
				words[lastWord].add(tuple(line.strip().split(' ')))
				
	return words
		
	
class Transitions(object):

	'''
	Markov chain implementation detail showing what appears before and after this element
	in the sample data.
	'''

	__slots__ = ('_value', '_sources', '_transitionCache', '_prepared')

	def __init__(self, val):
	
		self._value = val
		
		self._sources = {
			'to'   : defaultdict(int),
			'from' : defaultdict(int),
		}
		
		# Cascades is a weird construct without context -- the 'True' and 'False'
		# indicate whether it's allowed to transition to a "None" key or not.
		self._transitionCache = { 
			True  : {},
			False : {},
		}
		
		self._prepared = False
	
	
	def ConnectWith(self, whatterm, direction):
	
		'''
		Connect this chain element with another element either before or after it.
		
		Directions must be the strings 'to' or 'from' for the _GenerateCache cache
		to be generated properly.
		'''
		
		self._sources[direction][whatterm] += 1
		self._prepared = False
		
		
	def _GenerateCache(self):
	
		'''
		This effectively creates a list representing the states we can transition to and from.
		
		This perfectly represents the number of times we move to an arbitrary instance (if we move from this
		object to the letter 'a' 10 times, the entry 'a' will be present in the list 10 times).
		
		While this keeps code simple in the trivial case (random.choice(list)), this obviously can cause
		problems with memory if the number of recorded transitions between elements are very large.
		'''
		
		if not self._prepared:
		
			# Iterate through to and from terms
			for direction, transitions in self._sources.items():
		
				# Generate dictionaries for ignoring and listening for "None" transitions.
				# The "None" transition indicates that we're at the end of a word (if transitioning 'to'),
				# or at the very start (if transitioning 'from').
				for noNones in [True, False]:
				
					tmp_transition = {}
					total = 0
		
					for term, value in transitions.items():
					
						# If we don't want 'None' terms and this is a 'None', ignore it.
						if noNones and term is None:
							continue
								
						for j in range(total, total+value):
							tmp_transition[j] = term
					
						total += value
				
					self._transitionCache[noNones][direction] = tmp_transition
				
			self._prepared = True

			
	def PickRandomTerm(self, direction, noNones=False):
	
		'''
		Randomly pick an element connecting to this element in the desired direction ('to' or 'from).
		If 'noNones' is true, it will only return None if this term doesn't connect to anything else in the specified direction.
		'''

		self._GenerateCache()
		
		transitions = self._transitionCache[noNones][direction]		
		if not transitions:
			return None
			
		return random.choice(transitions)
		
		
	def __str__(self):
	
		return '\n'.join([
			self.value, 
			'\tTo:  \n\t\t{}'.format(self._sources['to']),
			'\tFrom:\n\t\t{}'.format(self._sources['from']),
		])
		
		
# -------------------------------------------------------------------------------------------------		
# MarkovChainHandler
# -------------------------------------------------------------------------------------------------		
class MarkovChainHandler(object):

	def __init__(self, params):
		
		self._connections = { None : Transitions(None) }
		self._args = params
		
		
	def Debug(self):
		''' Show all connections that the MarkovChainHandler has registered. '''
		for name, obj in self._connections.items():
			print(f'For object called "{name}": \n{obj}')
	
	
	def UpdateTermString(self, terms):
	
		''' Given an iterable sequence of terms, bidirectionally connect elements with their neighbors. '''
		
		# Ensure all terms exist. ---------------------------------------------
		
		for term in terms:
			if term not in self._connections:
				self._connections[term] = Transitions(term)
				
		# Connect neighboring terms with each other. --------------------------
		
		for thisTerm, nextTerm in zip(terms[:-1], terms[1:]):	
		
			self._connections[thisTerm].ConnectWith(nextTerm, 'to')
			self._connections[nextTerm].ConnectWith(thisTerm, 'from')
			
		# Connect the starting and ending term with 'none.' -------------------
		
		self._connections[None].ConnectWith(terms[0], 'to')
		self._connections[terms[0]].ConnectWith(None, 'from')
		
		self._connections[terms[-1]].ConnectWith(None, 'to')
		self._connections[None].ConnectWith(terms[-1], 'from')
				
		
	def GenerateChain(self):
	
		'''
		Generates a sequence of elements based on input arguments specified in the constructor.
		
		Returns either `None` or a sequence of elements 
		'''
	
		chain = deque()
		
		# By default, start using "None" to force generations to start with terms
		# explicitly used in the input. This can be overridden by the args constructed
		# with this class.
		
		starting_term = None
		if self._args.start:
		
			# Check if any of the starting terms are valid.
			if not any(term in self._connections for term in self._args.start):
				raise ValueError(f'None of the starting terms ({self._args.start}) exist as elements in the Markov Chain handler!')
			
			valid_starting_terms = set(self._connections) & set(self._args.start)
			starting_term = random.choice(valid_starting_terms)
			
		chain.append(self._connections[starting_term].PickRandomTerm('to', True))
		
		if chain[0] is None:
			return None

		# -----------------------------------------------------------------------------			
		# Generate the name until we think it's good.
		# -----------------------------------------------------------------------------	
		
		while 1:
							
			if chain[-1] is None:
				nextTerm = self._connections[chain[0]].PickRandomTerm('from', len(chain) < 3)
				chain.appendleft(nextTerm)
			else:
				nextTerm = self._connections[chain[-1]].PickRandomTerm('to', len(chain) < 3)
				chain.append(nextTerm)
					
			stringified = ''.join(x for x in chain if x)
					
			if chain[-1] is None and len(stringified) < self._args.minlen:
				return None
					
			if chain[-1] is None and chain[0] is None:
				break
				
			elif len(stringified) >= self._args.maxlen:
				break
	
		return tuple(x for x in chain if x)
					
