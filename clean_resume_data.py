import argparse
import pathlib
import json
from typing import List
import os
import experience_matcher as exp
from tqdm import tqdm

def process_data(data) -> List[dict]:
	processed_data = []
	for item in tqdm(data):
		experiences = item.get('experiences')
		if experiences is None:
			continue
		match_experiences = []
		for experience in experiences:
			match_bullets = []
			bullets = experience.get('bullets')
			if bullets is None:
				continue
			for bullet in bullets:
				doc = exp.nlp(bullet)
				matches = exp.matcher(doc)
				
				if len(matches) > 0:
					for match_id, _, _ in matches:
						# Heuristic to add sentences with weird line breaks
						string_id = exp.nlp.vocab.strings[match_id]
						
						if string_id == 'NOT_UPPERCASE':
							if match_bullets:
								match_bullets[-1] += ' ' + bullet
						else:
							match_bullets.append(bullet)
							break
			
			experience['bullets'] = match_bullets
			
			if experience['bullets']:
				match_experiences.append(experience)

		item['experiences'] = match_experiences

		if item['experiences']:
			processed_data.append(item)

	return processed_data
			

def main():
	parser = argparse.ArgumentParser(description='Convert json data to samples to be used by GPT 3')
	parser.add_argument('start_dir', help='Path to directory file containing data for sampling', type=pathlib.Path)
	parser.add_argument('-o', '--out', help='Output directory', type=pathlib.Path)
	args = parser.parse_args()
	start_dir = args.start_dir
	out_dir = args.out
	if out_dir is None:
		out_dir = start_dir
	else:
		out_dir.mkdir(exist_ok=True)
	
	for file in start_dir.glob('**/*.json'):
		with open(file, 'r', encoding='utf-8') as f:
			data = json.load(f)
			
			processed_data = process_data(data)
			
			file_name = file.name
			with open(os.path.join(out_dir, file_name), 'w', encoding='utf-8') as out_f:
				json.dump(processed_data, out_f, ensure_ascii=False, indent=4)
				print('File saved to ' + os.path.join(out_dir, file_name))
		
	
	

if __name__ == '__main__':
	main()
