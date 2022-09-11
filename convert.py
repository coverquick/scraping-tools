import sys
import json
def convert(file:str) -> str:
	with open(file, 'r', encoding='utf-8')as f:
		content = f.read()
	
	content = content.split(';')
	cookies = []
	for cookie in content:
		cookie = cookie.split('=')
		cookie_dict = dict(
			name=cookie[0],
			value=cookie[1],
			url='https://resumes.indeed.com/search',
		)
		cookies.append(cookie_dict)
	
	return json.dump(cookies, open(file.replace('.txt', '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
	


if __name__ == '__main__':
	file_path = sys.argv[1]
	convert(file_path)