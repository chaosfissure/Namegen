#!/usr/bin/env python

import sys, operator, argparse, os
from collections import defaultdict, deque

from namegen_utils import *

# -------------------------------------------------------------------------------------------------
# HistoryState
# -------------------------------------------------------------------------------------------------
class HistoryState(object):

	'''
	Keeps track of previous and future history states so you can go back and forward through
	data.  Optionally, you can specify a number of saved states it can support.

	It raises exceptions if you try to return a value not in the history index (before OR after).
	'''

	def __init__(self, descriptor, maxsize=0):

		self._descriptor = descriptor
		self._maxsize    = maxsize
		self._history    = []
		self._position   = 0

	def __bool__(self):
		return bool(self._history)

	def __len__(self):
		return len(self._history)

	def Position(self):
		'''Returns the current position of the history state.'''
		return self._position

	def ResetPosition(self):
		'''Resets the history position to the start.'''
		self._position = 0

	def Next(self):
		'''Moves to the next position in history, raising an exception if it'd be out of bounds.'''

		if self._position + 1 < len(self._history):
			self._position += 1

		return self.Current()

	def Previous(self):
		'''Moves to the previous position in history, raising an exception if it'd be out of bounds.'''

		if self._position:
			self._position -= 1

		return self.Current()

	def Current(self):
		'''Returns the current history state.'''

		if not self._history:
			raise IndexError('"{}" does not have any entries!'.format(self._descriptor))

		return self._history[self._position]

	def AtEnd(self):
		'''Returns if we're at the end of the history.'''
		return self._position + 1 == len(self._history)

	def AddHistory(self, value):
		'''Moves history position to the end, inserting the next element and removing the first if we exceed the history size.'''
		self._history.append(value)

		if self._maxsize > 0 and len(self._history) > self._maxsize:
			self._history = self._history[1:]

		self._position = len(self._history) - 1

# -------------------------------------------------------------------------------------------------
# AdaptedCorpus
# -------------------------------------------------------------------------------------------------
class AdaptedCorpus(object):

	'''
	A base/abstract class that provides an underlying list of syllabified names and parsed names,
	and statically caches certain things that subclasses are likely to use.
	'''

	WORDS        = {}
	PARSED_NAMES = {}

	def __init__(self, files):

		# Don't reload a corpus we've already loaded. -------------------------
		if AdaptedCorpus.WORDS:
			return

		# Load from the corpus ------------------------------------------------
		# The corpus is solely used to determine good transitions of syllables,
		# but isn't used during name generation.

		print('Loading CMU dictionary.  This may take while...', end=' ')

		from nltk.corpus import cmudict
		canned_words = cmudict.dict()

		print('done!')

		# Load from files -----------------------------------------------------

		AdaptedCorpus.PARSED_NAMES = ObtainSyllables(files)


		# Process all corpus terms and input terms ----------------------------
		print('Removing terms with non-word symbols, cleaning up remaining terms...', end=' ')

		for word, syllable_groups in YieldAllFrom(canned_words.items(), AdaptedCorpus.PARSED_NAMES.items()):

			filtered_name = FilterLetters(word)

			# If the sanitized word is valid and we have syllabic renderings of the word, remove all numbers from the syllables.
			if filtered_name:

				pronunciations = []
				for syllable_group in syllable_groups:
					pronunciations.append([RemoveNumbers(x) for x in syllable_group])

				AdaptedCorpus.WORDS[filtered_name] = pronunciations

		print('done!')

# -------------------------------------------------------------------------------------------------
# Node
# -------------------------------------------------------------------------------------------------
class Node(object):
	'''Storage of syllable combinations showing what letter combinations might represent certain sounds'''

	__slots__ = ('value', 'children', 'strings', 'parent')

	def __init__(self, value, parent):

		self.value = value

		self.children = {}
		self.strings  = []
		self.parent   = parent

	def Update(self, remainingSyllables, word):

		'''Branch down through "rest" until it's an empty list, and append the word as being perfectly represented by the syllable combination.'''

		if not remainingSyllables:
			self.strings.append(word)

		else:
			first = remainingSyllables[0].upper()
			if first not in self.children:
				self.children[first] = Node(first, self)

			self.children[first].Update(remainingSyllables[1:], word)

	def YieldSolutions(self, rest):

		'''Given a list of syllables, yield any valid sound that matches the syllable combination.'''

		if not rest:
			yield from self.strings

		else:
			first = rest[0].upper()
			if first in self.children:
				yield from self.children[first].YieldSolutions(rest[1:])

# -------------------------------------------------------------------------------------------------
# Transcriber
# -------------------------------------------------------------------------------------------------
class Transcriber(AdaptedCorpus):
	'''Reverse a set of syllables into a jumble of letters that might be reasonable.'''

	def __init__(self, files):

		AdaptedCorpus.__init__(self, files)

		print('Constructing associations with syllables...', end=' ')

		# Root node...
		self._associations = Node(None, None)

		# Constuct a syllable list to word lookup from the list of words we've parsed.
		for word, dialect in AdaptedCorpus.WORDS.items():
			for pronunciation in dialect:
				self._associations.Update(pronunciation, word)

		# For sanity purposes, construct really short lists of syllables to match to sounds.
		for firstLetter in LOWERCASE:

			# All letters will be matched with themselves.
			self._associations.Update([firstLetter.upper()], firstLetter)
			for secondLetter in LOWERCASE:

				# All two letter combinations will match to the first letter
				self._associations.Update([(firstLetter+secondLetter).upper()], firstLetter)

		print('done!')

	def Transcribe(self, syllables):
		return list(self._associations.YieldSolutions(syllables))

# -------------------------------------------------------------------------------------------------
# ImpossibleFilter
# -------------------------------------------------------------------------------------------------
class ImpossibleFilter(AdaptedCorpus):

	'''
	ImpossibleFilter provides post analysis on syllables generated from a markov chain.
	It checks to see that combinations of letters seem to fall under a reasonably common pattern
	given both the input set of names and the pronunciation dictionary.
	'''

	def __init__(self, filenames):

		AdaptedCorpus.__init__(self, filenames)

		syllables = set()
		self.probabilities = {
			'syllable' : defaultdict(int),
			'letter'   : defaultdict(int),
		}

		self.allowed_overrides = set()
		syl_count = 0
		let_count = 0

		for word, syllable_group in AdaptedCorpus.WORDS.items():

			# Keep track of letter combinations that don't occur frequently
			# Use three-letter combinations as filters because only using two-syllable terms
			# seems to result in more weird/undesirable combinations.
			if len(word) > 2:
				for j in range(len(word)-2):
					self.probabilities['letter'][(word[j], word[j+1], word[j+2])] += 1
					let_count += 1

			# Keep track of how many transitions occur between two syllables
			for each_group in syllable_group:

				for j in range(len(each_group)-1):
					pairing = (each_group[j], each_group[j+1])
					self.probabilities['syllable'][pairing] += 1
					syl_count += 1

				for group in each_group:
					syllables.add(group)

		for key, num in self.probabilities['syllable'].items():
			self.probabilities['syllable'][key] = 100.0*num/syl_count

		for key, num in self.probabilities['letter'].items():
			self.probabilities['letter'][key] = 100.0*num/let_count

		print('done!')

		'''
		print 'Probabilites of connections:'

		sorted_syllables = sorted(self.probabilities['syllable'].iteritems(), key=operator.itemgetter(1), reverse=True)
		sorted_letters   = sorted(self.probabilities['letter'].iteritems(),   key=operator.itemgetter(1), reverse=True)

		print '\nSyllable Transitions:\n'
		for i, ((a, b), num) in enumerate(sorted_syllables):
			print '\t{:^2} -> {:^2}: {:.6f}%'.format(a, b, num),
			if not (i+1)%4:
				print ''

		print '\nLetter Transitions:\n'
		for i, ((a, b, c), num) in enumerate(sorted_letters):
			print '\t{}{}{}: {:.6f}%'.format(a, b, c, num),
			if not (i+1)%5:
				print ''
		'''

		# Explicitly allow syllabic transitions present in the input data, even if they're unlikely to occur in the corpus.
		#
		# Go through each syllable in our input names list and map each syllable with the following syllable as a valid
		# transition in the event our input names differ from the typical English corpus.
		print('Constructing input overrides...', end=' ')

		for _, syllable_groups in AdaptedCorpus.PARSED_NAMES.items():
			for each_group in syllable_groups:
				# Do syllable mappings between each syllable and following syllable
				for i in range(len(each_group)-1):
					for j in range(i+1, len(each_group)):
						self.allowed_overrides.add((each_group[i], each_group[j]))

		print('done!')

	def HasImpossibleCombinations(self, what):

		''' Return if a word has combinations of letters that aren't consistent with the corpus or name list. '''

		for j in range(len(what)-1):

			pairing = (what[j], what[j+1])

			if pairing in self.allowed_overrides:
				continue

			if pairing not in self.probabilities['syllable']:
				print('Impossible syllable combination: {:^2} -> {:^2}'.format(*pairing))
				return True

			# This constant can be tuned.  It wasn't picked in some type of optimial analysis, but seems to work fairly well.
			if self.probabilities['syllable'][pairing] < 0.001:
				print('Very unlikely syllable combination: {:^2} -> {:^2}'.format(*pairing))
				return True

		return False

	def HasDumbLetterCombinations(self, what):

		'''Return if a word has a combination of letters that seem highly unlikely given the corpus and namelists.'''

		if len(what) > 2:
			for j in range(len(what)-2):
				pairing = (what[j], what[j+1], what[j+2])

				if pairing not in self.probabilities['letter']:
					#print 'Impossible combination: {}{}{}'.format(*pairing)
					return True

				if self.probabilities['letter'][pairing] < 0.001:
					#print 'Very unlikely combination: {}{}{}'.format(*pairing)
					return True

		return False

# -------------------------------------------------------------------------------------------------
# SoundManager
# -------------------------------------------------------------------------------------------------
class SoundManager():

	'''Manages the phonetics of an input word provided to the system.'''

	def __init__(self, syllables, transcriber, impossibleChecker):

		self._history   = HistoryState('Sound Manager')
		self._syllables = syllables

		transcribed = []
		
		for grouping in ChunkSyllables(syllables):

			wordparts = []
			for element in grouping:

				results = transcriber.Transcribe(element)

				if not results:
					wordparts = []
					break

				else:
					if not wordparts:
						wordparts += results
					else:
						tmp = []
						for result in results:
							for existing in wordparts:
								tmp.append(existing+result)
						wordparts = tmp

			if wordparts:
				transcribed += wordparts

		# Force transcriptions to have valid letter combinations.
		transcribed = [x for x in transcribed if not impossibleChecker.HasDumbLetterCombinations(x)]

		# Force transcriptions to contain vowels
		transcribed = [x for x in transcribed if any(z in x for z in VOWEL_SET) and len(x)]

		# Force transcriptions to be at least three letters long
		transcribed = [x for x in transcribed if len(x) >= 3]

		transcribed = list(set(transcribed))
		transcribed.sort()
		transcribed.sort(key=len)

		# Convert the string representations into a version without the u'thing' to make it more readable.
		transcriptions = []

		replacements = [
			["',", ','],
			["['", '['],
			["']", ']']
		]

		for element in transcribed:
			for before, after in replacements:
				element = element.replace(before, after)

			transcriptions.append(element)

		for group in Chunk(transcriptions, 5):
			self._history.AddHistory(group)

	def _DisplaySounds(self):

		'''Show the sounds at the current position.'''

		if not self._history:
			print(f'No transcription of {self._syllables} exists...')

		else:
			transcriptions = self._history.Current()
			position       = self._history.Position()
			entries        = len(self._history)
			print(transcriptions, '({}/{})'.format(position+1, entries))

	def AdvanceSounds(self):

		'''
		Advance the position of words matching the syllables by one unit and display the next set of words.
		Returns True if it advanced, or False if the word is invalid or sounds have been exhausted.
		'''

		if self._history.AtEnd():
			print('\tAll generated names have been exhausted!')

		elif self._history:
			self._history.Next()
			self._DisplaySounds()
			return True

		else:
			print(f'No transcription of {self._syllables} exists...')

		return False

	def Activate(self):
		'''Return "focus" to this element by displaying the syllable list of this word.'''
		print('\nLooking at {} '.format(''.join(self._syllables)), self._syllables)
		self._history.ResetPosition()
		self._DisplaySounds()
		
	def Syllables(self):
		''' Returns the syllables that were generated for this entry. '''
		return self._syllables
		

# -------------------------------------------------------------------------------------------------
# InteractiveInterface
# -------------------------------------------------------------------------------------------------
class InteractiveInterface(AdaptedCorpus):

	'''The interface used to interact with the name generator'''

	def __init__(self, args):

		''' Sets up the corpus and markov chain information.'''

		AdaptedCorpus.__init__(self, args.input)

		self._seenSyllables = set()
		self._markov        = MarkovChainHandler(args)
		self._impossible    = ImpossibleFilter(args.input)
		self._transcriber   = Transcriber(args.input)
		self._history       = HistoryState('Sound History', 16)

		for _, syllable_groups in AdaptedCorpus.PARSED_NAMES.items():
			for each_group in syllable_groups:
				self._markov.UpdateTermString(each_group)

	def _CreateEntry(self):

		'''Do Markov chain generations until we end up with a unique, novel set of syllables.'''

		while 1:

			syllables = tuple(x.upper() for x in self._markov.GenerateChain())

			if syllables is None or syllables in self._seenSyllables:
				continue

			self._seenSyllables.add(syllables)

			if self._impossible.HasImpossibleCombinations(syllables):
				#print(f'\tIgnoring {syllables} due to impossible/unlikely syllable combination.')
				#continue
				print(f'\tHas unmapped/impossible/unlikely syllable combinations:\n\t\t{syllables}')

			self._history.AddHistory(SoundManager(syllables, self._transcriber, self._impossible))
			return

	def _Previous(self):

		'''Moves to the previous sound state if possible.'''

		if not self._history.Position():
			print('\tCannot advance back any further!')

		else:
			self._history.Previous().Activate()

	def _Next(self):

		''' Move to the next sound state and create a new entry as necessary.'''

		if self._history.AtEnd() or not self._history:
			self._CreateEntry()
			self._history.Current().Activate()

		else:
			self._history.Next().Activate()


	def Display(self):

		# Prepare and create the first entry
		entry = ''
		self._Next()

		try:
			while 1:

				# Help menu ---------------------------------------------------
				if entry and entry[0] in '?hH':
					entry = input('([n]ext, [p]revious, [s]ave,  <return>) => ').strip().lower()

				# Prompt for the next input -----------------------------------
				else:
					entry = input(' => ')

				# Empty line - show additional possible syllibifications of word
				if not entry:
					if not self._history.Current().AdvanceSounds():
						self._Next()


				# Move to previous term ---------------------------------------
				elif entry[0] == 'p':
					self._Previous()

				# Move to next term -------------------------------------------
				elif entry[0] == 'n':
					self._Next()
					
				# Save something to a file ------------------------------------
				elif entry[0] == 's':
				
					syllables = self._history.Current().Syllables()
					actual_spelling = input(f'Enter actual spelling of {syllables}: => ').rstrip()
					if actual_spelling:
					
						save_to = input('Save to what file? => ').rstrip()
						if save_to:
				
							if not save_to.endswith('.txt'):
								save_to += '.txt'
								
							save_to = os.path.join('generated', save_to)
						
							if os.path.exists(save_to) or input(f'Create file "{save_to}"?').strip()[0] in 'yY':
								with open(save_to, 'a') as f:
									f.write('\n'   + actual_spelling.capitalize())
									f.write('\n\t' + ' '.join(syllables))

		# Keyboard abort, prevent random fortran runtime errors from cmudict --
		except KeyboardInterrupt as e:
			print('Ctrl+C seen, ending program.')

		# Sometimes cmudict has weird stuff going on --------------------------
		except EOFError as e:
			print('Ctrl+C seen (via CMUDict exception), ending program.')
			exit(0)


# -------------------------------------------------------------------------------------------------
# Drive the program fooooooorward into the future!
# -------------------------------------------------------------------------------------------------
if __name__ == '__main__':

	ap = argparse.ArgumentParser('Generates names by trying to split up words based on best guesses about how they sound')

	ap.add_argument('--minlen', type=int, default=4,  help='Minimum string length of generated names.')
	ap.add_argument('--maxlen', type=int, default=13, help='Force markov chain termination if the name is at least this size.')

	ap.add_argument('-s', '--start', nargs='+',
		help='A series of letter or letters names must start with.')

	ap.add_argument('-i', '--input', required=True, nargs='+',
		help='Input file(s) containing a list of names.  Each file must have one word/name per line.')

	ap.add_argument('-d', '--direction', default='forward',
		choices = ('forward', 'backward', 'bidirectional'),
		help    = 'When generating names, specify if we generate forward (at the end of the word), backward, or in both directions randomly.')

	args = ap.parse_args()

	if args.minlen >= args.maxlen or args.minlen < 1 or args.maxlen < 1:
		raise ValueError('The --minlen and --maxlen parameters must be larger than zero and a valid increasing range from minlen to maxlen')

	iface = InteractiveInterface(args)
	iface.Display()
