import argparse
import pathlib
import os
import json
import random
from typing import Tuple
import numpy as np
from similarity import Similarity
from tqdm import tqdm
import re
model = Similarity("all-mpnet-base-v2")

def flatten(l):
    return [item for sublist in l for item in sublist]


def education_match(education, resume_education):
	if len(resume_education) == 0:
		return None
	if len(resume_education) == 1:
		return resume_education[0]

	edu_titles = [edu.get('title') for edu in resume_education if edu.get('title') is not None]
	
	matches = model.predict(education, edu_titles)
	
	highest_match = matches[0]
	return resume_education[highest_match.get('j')]



def find_highest_match(resume, job_options, max_bullets=10) -> Tuple:
	highest_match = 0
	best_match = None
	h_bullets = None
	job_req = None
	experiences = resume.get('experiences')
	bullets = [experience.get('bullets') for experience in experiences]
	bullets = flatten(bullets)
	
	for i, job in enumerate(job_options):
		job_reqs = job.get('Responsibility', []).copy() + job.get('Qualification', []).copy()
		if not job_reqs:
			continue
		job_reqs = list(map(lambda x: x[0], job_reqs))
		matches = model.predict(bullets, job_reqs)
		match_scores = [match.get('score') for match in matches]
		
		score = np.mean(match_scores)
		if score > highest_match:
			h_reqs, h_bullets = set(), []
			
			for match in matches[:max_bullets]:
				h_reqs.add(job_reqs[match.get('j')])
				h_bullets.append(bullets[match.get('i')])
				   
			
			for job_req in job_reqs:
				if job_req not in h_reqs and len(h_reqs) < max_bullets:
					h_reqs.add(job_req)
					
			highest_match = score
			best_match = i
			job_req = list(h_reqs)
			
	# We return all the info we need so no recalculation is needed
	return (best_match, process_bullets(list(set(h_bullets))), process_bullets(job_req))



def process_bullets(bullets):
	
	bullets = [bullet.strip() for bullet in bullets]
	bullets = [re.sub('[^a-zA-Z0-9 \n\.]', ' ', bullet) for bullet in bullets]
	bullets = [bullet for bullet in bullets if bullet is not None]
	bullets = [bullet for bullet in bullets if bullet != '']
	bullets = [bullet.strip() for bullet in bullets]
	
	return bullets

def main():
	parser = argparse.ArgumentParser(description='Convert json data to samples to be used by GPT 3')
	parser.add_argument('start_dir', help='Path to directory file containing data for sampling', type=pathlib.Path)

	args = parser.parse_args()
	start_dir = args.start_dir
	files = []
	walked_dir = list(os.walk(start_dir))[1:3]
	files_1 = walked_dir[0][2]
	files_2 = walked_dir[1][2]
	
	os.makedirs(start_dir / 'samples', exist_ok=True)

	if 'jobs' in walked_dir[0][0]:
		jobs_path = walked_dir[0][0]
		resume_path = walked_dir[1][0]
	else:
		jobs_path = walked_dir[1][0]
		resume_path = walked_dir[0][0]
		
	
	assert len(files_1) == len(files_2)
	files_1.sort()
	files_2.sort()
	zipped = zip(files_1, files_2)
	for file_1, file_2 in zipped:
		
		assert file_1 == file_2
		files.append(file_1)
	
	for file in files:
		job_file = os.path.join(jobs_path, file)
		resume_file = os.path.join(resume_path, file)
		with open(job_file, 'r', encoding='utf-8') as f:
			job_data = json.load(f)
		with open(resume_file, 'r', encoding='utf-8') as f:
			resume_data = json.load(f)
		out_data = []
		for resume in tqdm(resume_data):
			# We sample 5 jobs randomly
			try:
				job_options = random.choices(job_data, k=5)
				highest_match, bullets, job_reqs = find_highest_match(resume, job_options)
				job = job_options[highest_match]
				
				
				
				if job.get('Education') is not None:
					education = job.get('Education')[0]
					resume_education = resume.get('educations')
					edu = education_match(education, resume_education)
				else:
					edu = None
				item = {
					'experience':bullets,
					'description':job_reqs,
				}
				if edu is not None:
					item['education'] = edu
				if job.get('Company Information') is not None:
					company = job.get('Company Information')
					company = list(map(lambda x: x[0], company))
				else:
					company = None
				item = {
					'experience':bullets,
					'description':job_reqs,
				}
				if edu is not None:
					item['education'] = edu
				
				if company is not None:
					item['company'] = company
				
				out_data.append(item)
			except Exception as e:
				print(e)
				pass

		with open(os.path.join(start_dir, 'samples', file), 'w', encoding='utf-8') as f:
			json.dump(out_data, f, ensure_ascii=False, indent=4)
			

if __name__ == '__main__':
	main()
	