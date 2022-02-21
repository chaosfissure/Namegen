#!/usr/bin/env python

from collections   import defaultdict
from namegen_utils import *
from nltk.corpus   import cmudict

WORDS = cmudict.dict()
		
def RemoveNumbers(word):
	'''Remove numbers from a word.'''
	return ''.join([letter for letter in word if letter not in set('0123456789')])
	
def ValidLines(fname):
	'''Return all non-whitespace lines in a file.'''
	with open(fname, 'r', encoding="utf8") as f:
		for each_line in f:
			stripped = each_line.rstrip()
			if stripped:
				yield stripped
	
def Chunk(l, s):
	'''Return sublists of elements grouped in groups of size s.'''
	for i in range(0, len(l), s):
		yield l[i:i+s]
	
def ListPermuter(what):
	
	if what:
	
		me = what[0]
									
		if type(me) is list:
			tmp = []
			for element in me:
				tmp.append([RemoveNumbers(x) for x in element])
			
			for element in tmp:
				if len(what) == 1:
					yield element
				else:
					for result in ListPermuter(what[1:]):
						yield element + result
	
		else:
			tmp = [RemoveNumbers(me)]
			if len(what) == 1:
				yield tmp
			else:
				for result in ListPermuter(what[1:]):
					yield tmp + result
		
def UpdateSyllablesFor(term, data):

	syllable_groups = list(data[term])
	term = term.capitalize()
	
	while 1:
	
		# Display menu options --------------------------------------------
		print(term)
		
		if syllable_groups:
			for i, elem in enumerate(syllable_groups):
				print(f'\t{i+1} - {elem}')
			print('')
			
		print('\tEnter "try <words> <or> <syllables>" to find pronunciation.')
		print('\tEnter "add <sounds> <to> <add>" to append a sound to this name.')
		print('\t\t - Start with an "@" to grab syllables from a word.')
		print('\t\t - Start with "@@" to grab syllables from all following words.')
		print('\tEnter "remove #" to remove the corresponding index')
		print('\tEnter "next" to move to the next word')
		print()

		result = input("Enter an option -> ")
		
		# Try to see syllabification of a term without changing the results ---
		
		if result.startswith('try '):
			rest = result[len('try '):].split(' ')
			
			for word in rest:
				word = word.lower()
				print(f'Phrase "{word}":')
				
				if word not in WORDS:
					print('\tNot found...')
					
				else:
					for variant in WORDS[word]:
						print('\t',variant)
						
		# Add syllabification for the current term ----------------------------
		elif result.startswith('add '):	
		
			result = result.upper()
		
			def AmpersandReplace(what):
				if what in WORDS:
					return WORDS[what]
				else:
					print(what, 'not recognized...ignoring input.')
					return None
						
			rest = [x.strip() for x in result[len('add '):].split(' ')]
			rest = [['@' in x or '@@' in result, x.replace('@','')] for x in rest]
			final = []
			
			for literal, entry in rest:
			
				if literal:
					lower = entry.lower()
					sounds = AmpersandReplace(lower)
					if sounds is not None:
						final.append(sounds)
				
				else:
					final.append(entry)

			syllable_groups += [x for x in ListPermuter(final)]
		
		# Move to the next term -------------------------------------------
		elif result.startswith('next'):
			break
			
		# Remove a term we've syllabified for this word.
		elif result.startswith('remove'):
			num = int(result[len('remove '):]) - 1
			if num < len(syllable_groups):
				syllable_groups.pop(num)
			else:
				print(f'Index {num} does not exist...')
				
				
	data[term] = set(tuple(x) for x in syllable_groups)


def SaveToFile(data, fname):

	if fname is None:
		fname = input('Save to what file? => ').strip()
		
	final_strings = []
	
	for term, entries in sorted(data.items()):
	
		# Only append things that have entries so we can delete terms too!
		if entries:
			final_strings.append(term + '\n')
			for entry in set(entries):
				stringify = RemoveNumbers(' '.join(entry))
				final_strings.append(f'\t{stringify}\n')
			
	with open(fname, 'w', encoding="utf8") as f:
		for elem in final_strings:
			f.write(elem)
	
			
def LoadAndMergeData(data, fname):

	if fname is None:
		fname = input('Load what file? => ').strip()
				
	words = ObtainSyllables([fname], True)	
	
	for word, syls in words.items():
		data[word.capitalize()] |= syls
				
	print('Loaded', len(words), 'names')
				
def ShowLoadedWords(data):

	for chunk in Chunk(sorted(data), 6):
		
		tmp = []
		
		for name in chunk:
			empty = not data[name]
			tmp.append('{:^16}'.format(f'**{name}**' if empty else name))
			
		print(' '.join(tmp))
			
		
if __name__ == '__main__':

	data = defaultdict(set)

	while 1:

		print('Enter a number corresponding to the option you would like.')
		print('\tLoad)     Load a list of words from a file, merging with existing data.')
		print('\tEdit/Add) Propose a new word or modify an existing word.')
		print('\t          Append a word to automatically modify it without needing to enter a separate word.')
		print('\tShow)     Show all loaded words')
		print('\tSave)     Save to file.')
		print('\tExit)     Exit without saving.')
		
		choice = input(' => ').strip().lower()
		
		args = choice.split()[1:]
		args = [x.strip() for x in args if x.strip()]
		
		if choice:
		
			if choice.startswith('load'):
				LoadAndMergeData(data, args[0] if args else None)
				
			elif choice.startswith('edit') or choice.startswith('add'):
			
				entry = args[0] if args else input('Propose what word? => ').strip()
				entry = entry.capitalize()
				
				if entry:
					UpdateSyllablesFor(entry, data)
					
			elif choice.startswith('show'):
				ShowLoadedWords(data)
				
			elif choice.startswith('save'):
				SaveToFile(data, args[0] if args else None)
				
			elif choice.startswith('exit'):
				break