#!/usr/bin/env python

import sys, random, argparse

from namegen_utils import *

# -------------------------------------------------------------------------------------------------	
# Split entries by rule
# -------------------------------------------------------------------------------------------------
def PartitionGroup(entries, whatfunc, position):

	'''
	
	Splits apart each of entries into a list of chunks based on `whatfunc`.
	
	`whatfunc` is expected to return a tuple of two objects:
		matches, consumed = whatfunc(substr)
		
		When `matches` is True, it indicates the word needs to be split in
		its current position.  Everything stored before this term will be:
		
			1) `position`=='after'  : Appended to the current collection of non-matching letters
				'food', split after 'oo', becomes ['foo', 'd']
			
			2) `position`=='before' : Appended at the start of the next collection of non-matching letters
				'food', split before 'oo', becomes ['f', 'ood']
				
			3) `position`=='around' : Appended as a unique group after the current non-matching letter group.
				'food', split around 'oo', becomes ['f', 'oo', 'd']
				
			4) `position`=='random' : Nondeterministic.  Randomly picks 'before'/'after'/'around' after each
			    successful match or iteration performed.
			
	'''
	
	original_position = position
		
	for word in entries:
	
		letterlist  = list(word)
		nonmatching = ['']
		
		while letterlist:
		
			if original_position == 'random':
				position = random.choice(('before', 'after', 'around'))
		
			match, consume = whatfunc(letterlist)
			
			if match:
			
				consumed   = ''.join(letterlist[:consume])
				letterlist = letterlist[consume:]
				
				if position == 'before':
					nonmatching.append(consumed)
					
				elif position == 'after':
					nonmatching[-1] += consumed
					nonmatching.append('')
					
				else:
					nonmatching.extend([consumed, ''])
				
			else:
				nonmatching[-1] += letterlist.pop(0)
							
		yield tuple(x for x in nonmatching if x)
		
		
# -------------------------------------------------------------------------------------------------
#
# Various rule lists for splitting up words.
#
# -------------------------------------------------------------------------------------------------

def letters(what):
	''' Return the very first letter in the term, and indicate we consume a single letter. '''
	return True, 1
	
def eachvowel(what):
	''' Return True only if we're a vowel, and consume a single letter. '''
	return what[0] in VOWEL_SET, 1
	
def groupedvowels(what):
	''' Consume all substrings of vowels length 2 or larger. '''
	
	count = 0
	for elem in what:
		if elem in VOWEL_SET:
			count += 1
		else:
			break
			
	if count >= 2:
		return True, count
	return False, 1
	

def twocommon(what):
		
	''' Consume two letters and return True if two common letters are next to each other. '''
	if len(what) >= 2 and all(x in COMMON_LETTERS for x in what[:2]):
		return True, 2
		
	return False, 1
	
	
def choose_randomly(what):
	''' Nondeterministic.  Pick a random method from METHOD_MAPPING.'''
	return random.choice(list(METHOD_MAPPING.items()))[1](what)
	
	
METHOD_MAPPING = {
	'letters'         : letters,
	'eachvowel'       : eachvowel,
	'groupedvowels'   : groupedvowels,
	'twocommon'       : twocommon,
	'choose_randomly' : choose_randomly,
}
	
					
# -------------------------------------------------------------------------------------------------
# Drive the program fooooooorward into the future!
# -------------------------------------------------------------------------------------------------
if __name__ == '__main__':

	ap = argparse.ArgumentParser('Generates names by splitting letters in words in various ways')

	ap.add_argument('--minlen', type=int, default=4,  help='Minimum string length of generated names.')
	ap.add_argument('--maxlen', type=int, default=13, help='Force markov chain termination if the name is at least this size.')
	
	ap.add_argument('-s', '--start', nargs='+',
		help='A series of letter or letters names must start with.')
	
	ap.add_argument('-i', '--input', required=True, nargs='+',
		help='Input file(s) containing a list of names.  Each file must have one word/name per line.')
	
	ap.add_argument('--method', default='letters',
		choices = set(METHOD_MAPPING),
		help    = 'Determine how letters in words will be split apart before the probability list is constructed.')
		
	ap.add_argument('--split', default='around',
		choices = ('around', 'before', 'after', 'random'),
		help    = 'When splitting a word apart (specified via -m/--method), determine how to break apart the word at a given separation point.')

	args = ap.parse_args()
		
	if args.minlen >= args.maxlen or args.minlen < 1 or args.maxlen < 1:
		raise ValueError('The --minlen and --maxlen parameters must be larger than zero and a valid increasing range from minlen to maxlen')
		
	args.method = METHOD_MAPPING[args.method]
		
	entries = [x.lower() for x in YieldNames(args.input)]
	
	chain = MarkovChainHandler(args)
	for entry in PartitionGroup(entries, args.method, args.split):
		chain.UpdateTermString(entry)
			
	seen = set(entries)
	
	while 1:
		generated = chain.GenerateChain()
		if generated:
			stringified = ''.join(generated)
			if stringified not in seen:
				seen.add(stringified)
				
				stringified = stringified.capitalize()
				aligned     = '{:<' + str(args.maxlen + 1) + '}'
				show_name   = '{} =>'.format(aligned.format(stringified))
					
				input(show_name)
					