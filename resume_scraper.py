import asyncio
from urllib.parse import urlencode, urlparse, parse_qs
import os
import json
from tqdm import tqdm
import argparse
import time
from playwright.async_api import async_playwright

class ResumeScraper(object):
	def __init__(self, url, playwright):
		self.url = url
		self.browser = None
		self.page = None
		self.context = None
		self.playwright = playwright
		
	async def init_browser(self):
		self.browser = await self.playwright.chromium.launch()
		self.context = await self.browser.new_context(extra_http_headers=headers)
	
	async def init_session(self, session_data):
		await self.init_browser()
		self.page = await self.context.new_page()
		await self.page.set_viewport_size({'width': 1980, 'height': 1020})
		await self.context.add_cookies(session_data['cookies'])
		
		
		
	async def kill_browser(self):
		await self.browser.close()
		self.browser = None
		self.page = None
	

	
	async def scrape(self, search_params, session_data) -> list:
		await self.init_session(session_data)
		url = self.url + '?' + urlencode(search_params)
		await self.page.goto(url)
		try:
			await asyncio.sleep(1.5)
			label = self.page.locator('[aria-label="Close"]')
			
			await label.click()
		except Exception as e:
			pass
		list_items = await self.get_list_items()
		
		resumes = []
		try:
			start_time = time.time()
			while len(resumes) <  500:
				for item in list_items:
					resume = await self.get_resume(item)
					
					resumes.append(resume)

				query = urlparse(url).query
				query_params = dict(parse_qs(query))
				query_params= {k: v[0] for k, v in query_params.items()}
				query_params['start'] = int(query_params['start']) + 50
				await self.page.goto(self.url + '?' + urlencode(query_params))
				list_items = await self.get_list_items()

				# 15 minutes is the longest duration for a single scrape
				if time.time() - start_time > 900:
					break
			await self.kill_browser()
		except Exception as e:
			print(e)
			await self.kill_browser()
		
		print(len(resumes))
		return resumes


	async def get_list_items(self):
		await self.page.wait_for_selector('#result-list')
		list_el = await self.page.query_selector('#result-list')
		list_items = await list_el.query_selector_all('li')
		return list_items

	async def get_resume(self, item) -> str:
		
		await item.click()
		await self.page.wait_for_selector('[data-cauto-id="resume"]')
		resume_el = self.page.frame_locator('iframe[name="resume_frame"]').locator('div.rdp-html-container')
		return await resume_el.inner_html()


async def main_fn(url, session_data, search_params) -> list:
	async with async_playwright() as playwright:
		scraper = ResumeScraper(url, playwright)
		data = await scraper.scrape(search_params, session_data)
		return data


cookies = {
    'CTK': '1f1ub4mcto2du800',
    'indeed_rcc': 'CTK',
    'LOCALE': 'en',
    'SESSION_START_TIME': '1647404717126',
    'SESSION_ID': '1fu8fi526s7mg802',
    'SESSION_END_TIME': '1647404720091',
    'OptanonAlertBoxClosed': '2022-05-03T22:20:04.945Z',
    'OptanonConsent': 'isGpcEnabled=0&datestamp=Tue+May+03+2022+16%3A20%3A19+GMT-0600+(Mountain+Daylight+Time)&version=6.30.0&isIABGlobal=false&hosts=&consentId=9c89d04f-713e-48be-b744-30c611f52017&interactionCount=2&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0007%3A1&geolocation=%3B&AwaitingReconsent=false',
    'g_state': '{"i_p":1652388510101,"i_l":3}',
    'CSRF': 'YuHQMKeTnGL9tuoRxPJVNYaaTf5gjpso',
    'SHARED_INDEED_CSRF_TOKEN': 'spOrDvpsqPjfqu6YADsGAl9b3jRu2Upo',
    'MICRO_CONTENT_CSRF_TOKEN': 'Fq4plXBlgSa5fcncv5AjGMgBx3Rqs8wL',
    '_cfuvid': 'Sq66INerhGNBIOAaE7a0iu0KPBmDMvLDvPH2JE3AtGU-1661384186270-0-604800000',
    'OPTIMIZELY_GRPS': '',
    'ENC_CSRF': 'UYVIVYkSAN3HqRLsIbTssNOqAtLrDGBG',
    'IRF': '2OjkVS608cTo_XJDtiYIcDSAhaYlxPe_cPBU-zVb2-oOIc92TfyjuFXpfE3ektCq',
    'LC': 'co=CA&hl=en',
    'SURF': 'kPmje0M2hnOo8OaM6TwYYIscHwCVZGB2',
    'RF': '"lGf6n8c50g2aAVYfStGdKbGIoCEtu5SIptfQsmcc9aC2PYzuqSyAxA-a7R5mAtJZow4kkL5FEQkNuVM0UAkVMWftOGZRexS_CHOySP1fMdo5prG3mqaKOlzKmzOdzHtP9Gpa50nlm8e_dp8JT78cR8tkBlZlYmPX2aRt3-jHgGW42O9JAtjn8nd13GCL7ntcZtxD7yhBw1aH3R0qLmOVoQ=="',
    '__cf_bm': 'ziGTh9BS5q9bKwb5rdhStwFKX_.YUX.fcW7FBNmPOaw-1661412176-0-AeWG4Br/i0DLPcHeiALiu+ZbOG/vVYiSzIDbev0qWKIrAET5knfWnDbParOtWmPqk0hzAS1k5QF5Sip0XYdQvNA=',
    'PPID': 'eyJraWQiOiI3YmYwYzJmMy05OTdmLTQyNGItOWQ4Yi1hZmMzZWEwZmUwMGMiLCJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiI3YmRiNjdkODlhMzU1OTJiIiwiYXVkIjoiYzFhYjhmMDRmIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImNyZWF0ZWQiOjE2NjE0MDk4MDYwMDAsInJlbV9tZSI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL3NlY3VyZS5pbmRlZWQuY29tIiwiZXhwIjoxNjYxNDE0MDM0LCJpYXQiOjE2NjE0MTIyMzQsImxvZ190cyI6MTY2MTQxMjIzNDUxNiwiZW1haWwiOiJ0b3NpbkBha29zZS5jYSJ9.wjZ3I_nYjqdJgRfzDtKruiiUV9x9rbTJrXB_iSlQ5BpM4wA35jAasPKMlFm2JH96JU2mASDqRaSd1XqtQceqLw',
    'SOCK': '"zjVn0qjn7e5hDaCT36pyaM8bQow="',
    'SHOE': '"eUQ7IW-mkAF4ZWudL0GJb3YdHF2YDTIXNCZrMyX2-Pjebv0rHuHb5zdCXEBboxA2rEuOOHTTA-l74t_Di1TUNXg5z8hsCnwCM1ujr_8UzkH_Kg1tHQ8bT6h_v_Vc5R6b3P6yvb6aQCG_Yw=="',
    'PCA': '75dae34bb586e809',
    'ADOC': '3917235131607341',
    '_dd_s': 'rum=1&id=978b8fb4-24d7-4c78-a791-3272b2e4219b&created=1661412166565&expire=1661413141773',
}

headers = {
    'authority': 'resumes.indeed.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'cache-control': 'max-age=0',
    # Requests sorts cookies= alphabetically
    # 'cookie': 'CTK=1f1ub4mcto2du800; indeed_rcc=CTK; LOCALE=en; SESSION_START_TIME=1647404717126; SESSION_ID=1fu8fi526s7mg802; SESSION_END_TIME=1647404720091; OptanonAlertBoxClosed=2022-05-03T22:20:04.945Z; OptanonConsent=isGpcEnabled=0&datestamp=Tue+May+03+2022+16%3A20%3A19+GMT-0600+(Mountain+Daylight+Time)&version=6.30.0&isIABGlobal=false&hosts=&consentId=9c89d04f-713e-48be-b744-30c611f52017&interactionCount=2&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0007%3A1&geolocation=%3B&AwaitingReconsent=false; g_state={"i_p":1652388510101,"i_l":3}; CSRF=YuHQMKeTnGL9tuoRxPJVNYaaTf5gjpso; SHARED_INDEED_CSRF_TOKEN=spOrDvpsqPjfqu6YADsGAl9b3jRu2Upo; MICRO_CONTENT_CSRF_TOKEN=Fq4plXBlgSa5fcncv5AjGMgBx3Rqs8wL; _cfuvid=Sq66INerhGNBIOAaE7a0iu0KPBmDMvLDvPH2JE3AtGU-1661384186270-0-604800000; OPTIMIZELY_GRPS=; ENC_CSRF=UYVIVYkSAN3HqRLsIbTssNOqAtLrDGBG; IRF=2OjkVS608cTo_XJDtiYIcDSAhaYlxPe_cPBU-zVb2-oOIc92TfyjuFXpfE3ektCq; LC=co=CA&hl=en; SURF=kPmje0M2hnOo8OaM6TwYYIscHwCVZGB2; RF="lGf6n8c50g2aAVYfStGdKbGIoCEtu5SIptfQsmcc9aC2PYzuqSyAxA-a7R5mAtJZow4kkL5FEQkNuVM0UAkVMWftOGZRexS_CHOySP1fMdo5prG3mqaKOlzKmzOdzHtP9Gpa50nlm8e_dp8JT78cR8tkBlZlYmPX2aRt3-jHgGW42O9JAtjn8nd13GCL7ntcZtxD7yhBw1aH3R0qLmOVoQ=="; __cf_bm=ziGTh9BS5q9bKwb5rdhStwFKX_.YUX.fcW7FBNmPOaw-1661412176-0-AeWG4Br/i0DLPcHeiALiu+ZbOG/vVYiSzIDbev0qWKIrAET5knfWnDbParOtWmPqk0hzAS1k5QF5Sip0XYdQvNA=; PPID=eyJraWQiOiI3YmYwYzJmMy05OTdmLTQyNGItOWQ4Yi1hZmMzZWEwZmUwMGMiLCJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiI3YmRiNjdkODlhMzU1OTJiIiwiYXVkIjoiYzFhYjhmMDRmIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImNyZWF0ZWQiOjE2NjE0MDk4MDYwMDAsInJlbV9tZSI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL3NlY3VyZS5pbmRlZWQuY29tIiwiZXhwIjoxNjYxNDE0MDM0LCJpYXQiOjE2NjE0MTIyMzQsImxvZ190cyI6MTY2MTQxMjIzNDUxNiwiZW1haWwiOiJ0b3NpbkBha29zZS5jYSJ9.wjZ3I_nYjqdJgRfzDtKruiiUV9x9rbTJrXB_iSlQ5BpM4wA35jAasPKMlFm2JH96JU2mASDqRaSd1XqtQceqLw; SOCK="zjVn0qjn7e5hDaCT36pyaM8bQow="; SHOE="eUQ7IW-mkAF4ZWudL0GJb3YdHF2YDTIXNCZrMyX2-Pjebv0rHuHb5zdCXEBboxA2rEuOOHTTA-l74t_Di1TUNXg5z8hsCnwCM1ujr_8UzkH_Kg1tHQ8bT6h_v_Vc5R6b3P6yvb6aQCG_Yw=="; PCA=75dae34bb586e809; ADOC=3917235131607341; _dd_s=rum=1&id=978b8fb4-24d7-4c78-a791-3272b2e4219b&created=1661412166565&expire=1661413141773',
    'referer': 'https://secure.indeed.com/account/login/emailtwofactorauth?hl=en_CA&co=CA&continue=https%3A%2F%2Fresumes.indeed.com%2Fsearch%3Fl%3D%26q%3DSoftware%2BEngineer%26searchFields%3Djt%26start%3D150%26from%3Dgnav-util-rezemp--zurg&from=gnav-util-rezemp--zurg&__email=AAAAAfFY0dbzEfws9aZApm7vaLwSTqlwb%2F9gazMe8JXg8MFH0xGnsvhM1hy%2F3g%3D%3D',
    'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-site',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
}

def parse_cookies(cookies):
	return [{'name': k, 'value': v, 'domain':'.indeed.com', 'path':'/'} for k, v in cookies.items()]

def main():
	parser = argparse.ArgumentParser()
	
	parser.add_argument('-o', '--output', help='output folder', default='resumes')
	#parser.add_argument('-c', '--cookies', help='cookies file', required=True)
	parser.add_argument('-t', '--titles', help='job titles file', required=True)
	args = parser.parse_args()
	url = "https://resumes.indeed.com/search"
	#cookies = json.load(open(args.cookies, encoding='utf-8'))
	
	titles = open(args.titles, 'r', encoding='utf-8').readlines()
	out_folder = args.output
	os.makedirs(out_folder, exist_ok=True)

	search_params = {
		'q': '',
		'start': '0',
		'l': '',
		'searchFields':'jt',
		'msg': 'enable2fa',
   		'from': 'gnav-util-rezemp--zurg',

	}
	session_data = {
		'cookies': parse_cookies(cookies),
	}
	
	

	for title in tqdm(titles):
		search_params['q'] = title.strip()
		result = asyncio.get_event_loop().run_until_complete(main_fn(url, session_data, search_params))
		with open(os.path.join(out_folder, title.strip() + '.json'), 'w', encoding='utf-8') as f:
			json.dump(result, f, ensure_ascii=False)
	
if __name__ == '__main__':
	main()
	
	
