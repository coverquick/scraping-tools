from bs4 import BeautifulSoup
import json
import argparse
import pathlib
import os
import re
from tqdm import tqdm
def check_none(data):
	return data.text if data is not None else ''


def process_bullets(bullets):
	if bullets is None:
		return []
	

	for br in bullets.find_all('br'):
		br.replace_with('\n')
	
	bullets = bullets.text.split('\n')
	
	
	bullets = [bullet.strip() for bullet in bullets]
	bullets = [re.sub('[^a-zA-Z0-9 \n\.]', ' ', bullet) for bullet in bullets]
	bullets = [bullet for bullet in bullets if bullet is not None]
	bullets = [bullet for bullet in bullets if bullet != '']
	bullets = [bullet.strip() for bullet in bullets]
	
	return bullets


def process_file(file_path, out_path='./'):
	with open(file_path, 'r', encoding='utf-8') as f:
		file_data = json.load(f)
		processed_resumes = []
		yoe_pattern = r'\d+ year(s)?'
		for resume in file_data:
			resume_data = {}
			soup = BeautifulSoup(resume, 'html.parser')
			summary = soup.select_one('#res_summary')
			if summary is not None:
				resume_data['summary'] = summary.text
			
			work_experience = soup.select_one('#work-experience-items')
			if work_experience is not None:
				experiences = work_experience.select('.work-experience-section.section-entry')
				if experiences is not None:
					resume_data['experiences'] = []
					for experience in experiences:
						experience_data = {}
						title = experience.select_one('.work_title.title')
						company = experience.select_one('.work_company')
						dates = experience.select_one('.work_dates')
						bullets = experience.select_one('.work_description.rdp-richtext')
						experience_data['title'] = check_none(title)
						experience_data['company'] = check_none(company)
						experience_data['dates'] = check_none(dates)
						experience_data['bullets'] = process_bullets(bullets)
						resume_data['experiences'].append(experience_data)
			
			education = soup.select_one('#education-items')
			if education is not None:
				educations = education.select('.education-section.section-entry')
				if educations is not None:
					resume_data['educations'] = []
					for education in educations:
						education_data = {}
						title = education.select_one('h3.edu_title')
						dates = education.select_one('.edu_dates')
						school = education.select_one('.edu_school')
						education_data['title'] = check_none(title)
						education_data['dates'] = check_none(dates)
						education_data['school'] = check_none(school)
						resume_data['educations'].append(education_data)

			skills = soup.select('#skills-items > li')
			

			if skills is not None:
				resume_data['skills'] = []
				for skill in skills:
					skill_data = {}
					skill_data['name'] = check_none(skill)
					yoe = re.search(yoe_pattern, check_none(skill))
					if yoe is not None:
						skill_data['yoe'] = yoe.group(0)
					resume_data['skills'].append(skill_data)
					if yoe is not None:
						skill_data['years'] = yoe.group(0).split(' ')[0]
					resume_data['skills'].append(skill_data)

			links = soup.select('#link-items > .link_url')
			if links is not None:
				resume_data['links'] = []
				for link in links:
					link_data = {}
					link_data['url'] = check_none(link)
					resume_data['links'].append(link_data)

			
			processed_resumes.append(resume_data)
		
		file_name = file_path.split('/')[-1]
		with open(os.path.join(out_path, file_name), 'w', encoding='utf-8') as out_f:
			no_dups = {json.dumps(x, sort_keys=True):x for x in processed_resumes}.values()
			no_dups = list(no_dups)
			json.dump(no_dups, out_f, ensure_ascii=False, indent=4)
			print('File saved to ' + os.path.join(out_path, file_name))


def main():
	parser = argparse.ArgumentParser(description='Convert text file to json')
	parser.add_argument('directory', help='Path to directory file', type=pathlib.Path)
	parser.add_argument('-o', '--out', help='Output directory', type=pathlib.Path)
	args = parser.parse_args()
	files = os.listdir(args.directory)
	if not args.out:
		out_path = args.directory.with_stem('resumes_processed')
	else:
		out_path = args.out
	
	os.makedirs(out_path, exist_ok=True)
	for file in tqdm(files):
		joined_file = os.path.join(args.directory, file)
		process_file(joined_file, out_path)
		


if __name__ == '__main__':
	main()
