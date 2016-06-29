import random
import sys
import os
import time
import time
from collections import defaultdict
import editdistance

# We need special terms to append to the beginning and end of strings to indicate where they start and end - 
#   -- This allows the markov chains to end when transitioning from one character.
#   -- This allows us to limit how words start to existing words if we so choose.
STRING_BASE = '\1'
STRING_END = '\n'
ALLTERMS = 2

def IndividualMarkov(filedata):

	global STRING_BASE
	global STRING_END
	global ALLTERMS

	ret = defaultdict(list)
	ret[ALLTERMS] = set()
	
	for line in filedata:
			
		# The STRING_BASE will know all the starting letters.
		prior = STRING_BASE
				
		for character in line + STRING_END:
			ret[ALLTERMS].add(prior)
			ret[prior].append(character)
			prior = character

	return ret
	
# splitFunc converts a list of non-delimiter groups and delimiter terms into [start, end] pairs for use in the chain.
def SplitAtTerms(filedata, delimiters):

	global STRING_BASE
	global STRING_END
	global ALLTERMS

	ret = defaultdict(list)
	ret[ALLTERMS] = set()
	
	for line in filedata:
			
		# The STRING_BASE will know all the starting letters.
		splits = [STRING_BASE]
		substring = ''
		
		# Split the line into a list of terms and delimiters.			
		for character in line:
			substring += character
		
			for term in delimiters:
				if substring.endswith(term):
					splits.append(substring[:-len(term)])
					splits.append(term)
					substring = ''
					break
			
		if substring != '': splits.append(substring)
						
		# connect the prior terms in the splits list to the subsequent terms.
		
		splits = [x for x in splits if x != ''] + [STRING_END]
			
		for j in xrange(len(splits)-1):
			fromTerm = splits[j]
			toTerm   = splits[j+1]
			
			ret[ALLTERMS].add(fromTerm)
			ret[ALLTERMS].add(toTerm)	
			ret[fromTerm].append(toTerm)
			
	return ret
	
	
def SplitBeforeTerms(filedata, delimiters):

	global STRING_BASE
	global STRING_END
	global ALLTERMS
	
	ret = defaultdict(list)
	ret[ALLTERMS] = set()
	
	for line in filedata:
		splits = [STRING_BASE]
		substring = ''
	
		for character in line:
			substring += character
		
			for term in delimiters:
				if substring.endswith(term) and len(substring) > len(term):
					splits.append(substring[:-len(term)])
					substring = term
					break
			
		if substring != '': splits.append(substring)
		splits = [x for x in splits if x != ''] + [STRING_END]
			
		for j in xrange(len(splits)-1):
			fromTerm = splits[j]
			toTerm   = splits[j+1]
			
			ret[ALLTERMS].add(fromTerm)
			ret[ALLTERMS].add(toTerm)	
			ret[fromTerm].append(toTerm)
			
	return ret
	
	
def SplitAfterTerms(filedata, delimiters):

	global STRING_BASE
	global STRING_END
	global ALLTERMS
	
	ret = defaultdict(list)
	ret[ALLTERMS] = set()
	
	for line in filedata:
		splits = [STRING_BASE]
		substring = ''
	
		for character in line:
			substring += character
		
			for term in delimiters:
				if substring.endswith(term):
					splits.append(substring)
					substring = ''
					break
							
		if substring != '': splits.append(substring)
		splits = [x for x in splits if x != ''] + [STRING_END]
			
		for j in xrange(len(splits)-1):
			fromTerm = splits[j]
			toTerm   = splits[j+1]
			
			ret[ALLTERMS].add(fromTerm)
			ret[ALLTERMS].add(toTerm)	
			ret[fromTerm].append(toTerm)
			
	return ret
	
def SplitAroundTerms(filedata, delimiters):
	return SplitByTerms(filedata, delimiters, lambda x: x)
	
	
def GenerateName(chainDict, minlen, maxlen, start, useLastChar=True):
	
	global STRING_BASE
	global STRING_END
	global ALLTERMS
				
	def RandomFromCollection(c):
		return c[random.randint(0, len(c)-1)]
		
	def RandomStartingTermFromLetter(d, letter):
		possibilities = []
		for allthings in d:
			if type(allthings) is str and letter == allthings[0]:
				possibilities.append(allthings)
		return RandomFromCollection(possibilities)	
	
	def RandomFromChainDict(d, letter):
		transitions = d[letter]
		return RandomFromCollection(transitions)
		
	def RandomNonEndingFromChainDict(d, letter):
		transitions = [x for x in d[letter] if x != STRING_END]
		if len(transitions) == 0:
			return None
		return RandomFromCollection(transitions)
	
	name = ''
	
	if start != '':
		startingLetter = RandomFromCollection(start)
		name = RandomStartingTermFromLetter(chainDict, startingLetter)
	else:
		name = RandomFromChainDict(chainDict, STRING_BASE)
			
	lastTerm = name if not useLastChar else name[-1]
		
	while len(name) < maxlen:
		
		# If we pass the length requirements and reach the end, then quit the loop.
		if len(name) > minlen and name[-1] == STRING_END:
			break	
			
		# Otherwise we haven't passed the length requirements.
		elif lastTerm in chainDict:
		
			# See what this term goes to.  We don't want to prevent it from ending
			# because there's a chance it normally will do that.
			term = RandomFromChainDict(chainDict, lastTerm)
			
			# Is the term an ending string before we actually have a decent length?
			while len(name) < minlen and term[-1] == STRING_END:
				term = RandomNonEndingFromChainDict(chainDict, lastTerm)
				
				# If we do have an ending only term, just admit that it won't work.
				# This name will be rejected probably, and we'll need to generate another.
				if term is None:
					term = STRING_END
					break
				
			name += term
			lastTerm = term if not useLastChar else name[-1]
			
		else:
			break
			
	return name.strip(STRING_BASE+STRING_END)
		
if __name__ == '__main__':

	params = dict()
	
	params['entries']   = 768   # How many names do we generate?
	params['minlength'] = 6     # What's the minimum name length?
	params['maxlength'] = 16    # How long should the names be kept?
	params['file']      = ''    # What's the name of the file that we read names from?
	params['filter']    = ''    # What is an existing list of names we do NOT want to generate?
	params['leven']     = 1     # Minimum Levenshtein distance between the source name and generated names
	params['start']     = ''    # Force all generated names to start with a certain term.
	params['dump']      = ''    # Dump the mappings between groupings of a -> b in the markov list to a file
	params['out']       = 'generatednames.txt' # Name of the output file we will write results to.
	
	# Extract key/value pairs from parameters.
	for element in sys.argv:
		for param in params:
			if element.count(param) > 0:
				keyValue = element.split('=')
				if params[param] is None:
					params[param] = keyValue[0]
				elif type(params[param]) is int: 
					params[param] = int(keyValue[1])
				else:
					params[param] = keyValue[1]
		
	# Replay the params so we can see what they are.
	print 'Param dump:'
	for param in params:
		print '\t', param, params[param]
		
	# If we don't have an input filename, then don't bother doing anything.
	if params['file'] == '':
		print 'No input file specified! Aborting.'
		exit(0)
				
	# If we have an existing file to filter against, load that data too.
	filtered = []
	if params['filter'] != '':
		with open(params['file'], 'r') as f:
			filtered = [x.lower().lstrip().rstrip() for x in f.readlines()]
			
	# To do filtering against the filtered names faster, we'll break the names up into
	# hashmaps based on name length.
	
	byLength = defaultdict(set)
	for word in filtered:
		byLength[len(word)].add(word)
			
	# We can release the filtered list now that we've constructed a dict with all its terms.
	# This isn't really necessary unless we're memory constrained....
	filtered = []
		
	# Figure out the mapping of the names in the input file.
	filedata = []
	with open(params['file'], 'r') as f: filedata = [x.lstrip().rstrip() for x in f.readlines()]
	filedata = [x.lower() for x in filedata if x != '']
	
	#dictionary = IndividualMarkov(filedata)
	#dictionary = SplitAtTerms(filedata, [x for x in 'aeiou'])
	#dictionary = SplitAfterTerms(filedata, [x for x in 'aeiou'])
	dictionary = SplitBeforeTerms(filedata, [x for x in 'aeiou'])
	
	
	if params['dump'] != '':
		with open(params['dump'], 'w') as f:
			for key in sorted(dictionary):
			
				fromTerm = str(key)
			
				f.write('From "' + fromTerm + '" -- \n')
					
				for eachValue in sorted(set(dictionary[key])):
					occurrences = str(list(dictionary[key]).count(eachValue))
					
					toTerm = str(eachValue)
					if eachValue == STRING_BASE:  toTerm = '<BEGIN>'
					elif eachValue == STRING_END: toTerm = '<END>'
									
					f.write('\tTo ' + toTerm + ': ' + occurrences + '\n')
		
						
	names = set()
	while (len(names) < params['entries']):
	
		name = GenerateName(dictionary, params['minlength'], params['maxlength'], params['start'])

		# Force names to be within the name size range.
		if not (params['minlength'] <= len(name) <= params['maxlength']): continue
		
		# Force names not to be existing nams or filtered names
		if name in names: continue

		# Check against the existing names of the same size.
		try:
		
			# Ignore if we already have the name.
			if name in byLength[len(name)]: continue
			
			# Ignore if the Levenshtein distance between names of the same length is too small.
			distances = [editdistance.eval(word,name) > params['leven'] for word in byLength[len(name)]]
			if False in distances: continue
			
		# Otherwise, the name is good and we can append it!
		except KeyError:
			byLength[len(name)] = set()
			
		names.add(name)
		byLength[len(name)].add(name)
	
	names = list(names)
	names.sort()
	
	with open(params['out'],'w') as file:
		for i in range(len(names)):
			file.write(names[i].capitalize()+'\n')			
	