from spacy.matcher import Matcher
import spacy

nlp = spacy.load('en_core_web_sm')

matcher = Matcher(nlp.vocab)


verb_match = [
	{'IS_SENT_START': True, 'POS': 'VERB', 'IS_TITLE': True},
]

i_match = [
	{'IS_SENT_START': True, 'TEXT': 'I', 'IS_TITLE': True},
]

adverb_match = [
	{'IS_SENT_START': True, 'POS': 'ADVERB', 'IS_TITLE': True},
]

not_upper = [
	{'IS_TITLE': False, 'IS_SENT_START': True},
]

patterns = [
	verb_match,
	i_match,
	adverb_match,
]



matcher.add('EXP_MATCH', patterns)
matcher.add('NOT_UPPERCASE', [not_upper])

