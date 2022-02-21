import os
from namegen_utils import ObtainSyllables



def Cleanup(fname):
	
	names_and_syls = { k.capitalize() : v for k, v in ObtainSyllables([fname], True).items() }
	
	with open(fname, 'w', encoding="utf8") as f:
		for name in sorted(names_and_syls):
			f.write(f'{name}\n')
			for syllables in sorted(names_and_syls[name]):
				f.write('\t{}\n'.format(' '.join(syllables)))


if __name__ == '__main__':

	for eachdir in ['resource', 'generated']:
		if os.path.exists(eachdir):
			content = [os.path.join(eachdir, x) for x in os.listdir(eachdir)]
			content = [x for x in content if not os.path.isdir(x)]
			for eachfile in content:
				Cleanup(eachfile)
	