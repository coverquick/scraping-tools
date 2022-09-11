import os
from typing import List
from urllib.parse import urlencode
import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from tqdm import tqdm
import re
import time
from bs4 import BeautifulSoup
import requests
from multiprocessing import Process
import argparse
def build_url(url, params):
    return url + "?" + urlencode(params)




class Scraper:
    """
    Scraper base class.
    Each scraper must implement the scrape method.
    """

    def __init__(self, query, **kwargs):
        self.query = query
        self.kwargs = kwargs
        # List for all our scraped data

        # List for all our scraped sentences/list elements
        self.jobs: List[dict] = []

        # Set up the webdriver add headless mode
        

    def __str__(self):
        return f"Scraper({self.query}, {self.kwargs})"

    def scrape(self, location: str = ""):
        raise NotImplementedError("Subclass must implement abstract method")


class LinkedInScraper(Scraper):
    def __init__(self, query, **kwargs):
        super().__init__(query, **kwargs)
        self.query = query
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        self.driver.set_window_size(2048, 768)
        self.start_url = "https://www.linkedin.com/jobs/search/"

    def scrape(self, location: str = "Canada"):
        full_url = build_url(
            self.start_url,
            {
                "keywords": self.query,
                "location": location,
                "trk": "public_jobs_jobs-search-bar_search-submit",
                "redirect": "false",
                "position": 1,
                "pageNum": 0,
            },
        )
        

        self.driver.get(full_url)
        rep = {",": "", "+": ""}
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))

        job_count = self.driver.find_element(By.CSS_SELECTOR, "h1>span").text
        job_count = pattern.sub(lambda m: rep[re.escape(m.group(0))], job_count)
        job_count = int(job_count)

        i = 2
        curr_len = 0
        pbar = tqdm(total=job_count // 25)
        while i <= int(job_count / 25) + 1:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            i = i + 1
            pbar.update(1)
            try:
                job_lists = self.driver.find_element(
                    By.CLASS_NAME, "jobs-search__results-list"
                )
                jobs = job_lists.find_elements(By.TAG_NAME, "li")
                if curr_len == len(jobs):
                    break
                curr_len = len(jobs)
                self.driver.find_element(
                    By.CLASS_NAME, "infinite-scroller__show-more-button"
                ).click()
                time.sleep(3)

            except Exception:
                time.sleep(3)
        # return a list
        job_lists = self.driver.find_element(By.CLASS_NAME, "jobs-search__results-list")
        jobs = job_lists.find_elements(By.TAG_NAME, "li")
        

        for item, job in enumerate(tqdm(jobs)):
            try:
                title = job.find_element(By.TAG_NAME, "h3").text
                company = job.find_element(By.TAG_NAME, "h4").text
                location = job.find_element(
                    By.CSS_SELECTOR, "span.job-search-card__location"
                ).text
                link = job.find_element(By.TAG_NAME, "a").get_attribute("href")
                job_click_path = (
                    f"/html/body/div[1]/div/main/section[2]/ul/li[{item + 1}]"
                )
                job.find_element(By.XPATH, job_click_path).click()
                time.sleep(2)

                description = self.driver.find_element(
                    By.CLASS_NAME, "show-more-less-html__markup"
                ).get_attribute("innerHTML")

                job_dict = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link,
                    "description": description,
                }
                self.jobs.append(job_dict)

            except Exception:
                pass
        
        
        self.driver.close()
        return self.jobs


class IndeedScraper(Scraper):
    def __init__(self, query, **kwargs):
        super().__init__(query, **kwargs)
        self.query = query
        self.start_url = "https://ca.indeed.com/jobs"
        self.jobs = []
        self.job_set = set()

    def scrape(self, location: str = "Canada"):
        url_dict = {"q": self.query, "l": location, "start": 0}
        full_url = build_url(self.start_url, url_dict)
        soup = BeautifulSoup(requests.get(full_url).text, "html.parser")

        jobs = soup.find_all('a', {'class':'result'})
        while not jobs:
            soup = BeautifulSoup(requests.get(full_url).text, "html.parser")
            jobs = soup.find_all('a', {'class':'result'})
        
        repeat = 0
        while True:
            
            for job in tqdm(jobs):
                try:
                    title = job.find('h2', {'class': 'jobTitle'})
                    company = job.find('span', {'class':'companyName'})
                    location = job.find('div', {'class':'companyLocation'})
                    if not title or not company or not location:
                        continue
                    link = f'https://ca.indeed.com{job.get("href")}'
                    
                    if title.get_text()+company.get_text()+location.get_text() in self.job_set:
                        repeat += 1
                        continue
                    else:
                        self.job_set.add(title.get_text()+company.get_text()+location.get_text())
                    
                    description_soup = BeautifulSoup(requests.get(link).text, "html.parser")
                    description = description_soup.find('div', {'class':'jobsearch-jobDescriptionText'})

                    job_dict = {
                        "title": title.get_text(),
                        "company": company.get_text(),
                        "location": location.get_text(),
                        "link": link,
                        "description": str(description),
                    }

                    
                
                    self.jobs.append(job_dict)
                except Exception:
                    pass
            
            if repeat >= len(self.jobs) // 10:
                break
            
            url_dict['start'] += 10
            url = build_url(self.start_url, url_dict)
            soup = BeautifulSoup(requests.get(url).text, "html.parser")
            jobs = soup.find_all('a', {'class':'result'})

            while not jobs:
                soup = BeautifulSoup(requests.get(url).text, "html.parser")
                jobs = soup.find_all('a', {'class':'result'})

            
        return self.jobs

class MonsterScraper(Scraper):
    def __init__(self, query, **kwargs):
        super().__init__(query, **kwargs)
        self.query = query
        self.start_url = "https://www.monster.ca/jobs/search/"

        options = Options()
        #options.add_argument("--user-data-dir=chrome-data")
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        self.driver.set_window_size(2048, 768)
    
    def scrape(self, location: str = "Canada"):
        url_dict = {"q": self.query, "where": location, "start": 0}
        full_url = build_url(self.start_url, url_dict)
        self.driver.get(full_url)
        self.driver.implicitly_wait(3)
        el = self.driver.find_element(By.CLASS_NAME, "splitviewstyle__CardGridSplitView-sc-zpzpmg-1")
        
        pbar = tqdm(total=100)
        
        while True and pbar.n <= 100:
            try:
                last_el = el.find_elements(By.TAG_NAME, "div")[-1]
                self.driver.execute_script("arguments[0].scrollIntoView(true)", last_el)

                button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".job-search-resultsstyle__LoadMoreContainer-sc-1wpt60k-1 > button")))
                
                if button.text.lower() == "No More Results".lower():
                    break

                self.driver.execute_script("arguments[0].click();", button)
                
            except Exception as e:
                if e.args[0] == '' and e.args[1] is None and e.args[2] is None:
                    break
            
            pbar.update(1)
            time.sleep(3)
            
            
        jobs = el.find_elements(By.TAG_NAME, "article")

        for index, job in enumerate(tqdm(jobs)):
            try:
                
                title = job.find_element(By.XPATH, f'/html/body/div/div[3]/main/div[2]/nav/section[1]/div[2]/div[1]/div/div/div/div/div[{index + 1}]/article/div/a')
                company = job.find_element(By.XPATH, f'/html/body/div/div[3]/main/div[2]/nav/section[1]/div[2]/div[1]/div/div/div/div/div[{index + 1}]/article/div/h3').text
                location = job.find_element(By.XPATH, f'/html/body/div/div[3]/main/div[2]/nav/section[1]/div[2]/div[1]/div/div/div/div/div[{index + 1}]/article/div/p[1]').text
                link = title.get_attribute("href")
                description_soup = BeautifulSoup(requests.get(link).text, "html.parser")
                
                title = title.text
                
                description = description_soup.find('section')
                
                job_dict = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link,
                    "description": str(description),
                }
                
                self.jobs.append(job_dict)
            except Exception:
                pass
            time.sleep(2)

        self.driver.quit()
        return self.jobs


class GlassdoorScraper(Scraper):
    def __init__(self, query, **kwargs):
        super().__init__(query, **kwargs)
        self.query = query
        self.start_url = "https://www.glassdoor.ca/Job/jobs.htm"
        self.headers = {
            'authority': 'www.glassdoor.ca',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            #'cookie': 'gdId=8ffde0fd-1f10-4a21-97a2-94a700d14256; trs=https%3A%2F%2Fwww.google.com%2F:SEO:SEO:2021-07-26+14%3A38%3A51.998:undefined:undefined; rttdf=true; indeedCtk=1fj3r00vuu3d1801; G_ENABLED_IDPS=google; G_AUTHUSER_H=0; g_state={"i_p":1651451910859,"i_l":1}; uc=8013A8318C98C51742B255930E2D13A8FF9942ADEF1ACD4B2FCBA8282BFB4B9ACA19C9D75D42E62D564213185F212F0280885A31D257BB0F44F14343B5B7100A9EE7E514ADD19AC25FD2C8682ADE4AAAE0D97F5699DF24FF25A98BD551F2966CE89D145711558E9578D6EF8983E78ED9CD6E3CD7B1233B705E4219489C1A80BD557CA5DE69F7DBD1BECF88A8E84A8197; JSESSIONID_JX_APP=3B1784CBA17F487E7F7683B058252F89; GSESSIONID=8ffde0fd-1f10-4a21-97a2-94a700d14256+1651443602616; cass=0; at=yXkr_oI86exa7_GnI8o6WnJ2gA3zMxbASgf5NUP4HoKGjL9RmMBk0y046zo24m07swokz6K53W0Ek117YsV8x-KDWsoca57bzRyH6uBYIj_g_r1W3tqj2v9ijtXwnKdn2vqwkYy21AUvdspryFklGcmtGWR-Jwbo4DvdTuEFTnEH22jXmjJ6VlNpy8R9k0rn5_6-ZNOhSZ1wqVcNObW-twaXx4Z8lq-lb6KmKoExlUUKJBxzZQhJgUFxaVNpYbn_tehEzX4YEGHsDZ8DZZ-HzzcJ03SshlDqYB1G0aJ4FMsVqLY8EQ0Gle_0xgz1HnH9ZzCUu6jVXdC6wcFraVDWrkCTUBq7glyrIR6YN4vzasunOS1tXb636lLhvCM9ePM5o99NnbPJBi-6FgpgKLF8uV4OpDyQlRhqMySX_k_GuUa9Y04j_0NbH2UDJPBdsqgRH1bwJEmI4TrtjTQHPgSZuDz7K7DgIaThNJBkdEnNAzva0TLsfWeNv3t7h9TbHPLDNwir-WsrZAatS51HqaegDMONruQfjh3PtFwGNgk2DKxVTF0ADHifpjdE1KNJ-2T9P3e16_Z4FCqZOHwweN7zil1XikLlcyDK1__A5kc99RtxBkjyvYnz1ctOTlsQDFK4tqNy8qW_v2sajzeYFgC5f-XgdhaLOTGo_HWSTXngqkAZwh3kdEgaabGOAUgQtiIQHVsjSbDX8JzPIBnt4-RTThcN9Y6ulT8sVZbr8rRv3zBvdykDKzVmn6bJ9sSbCptIGAsIuH0FqIdCJVEOoUExm9Bkwi_oTwqJygEuPRpkdZzeTXBsUSpbHaNe7396NebDNjUP7cB3hGXVRHsz5QBaBe8UZyhjmISn-RYrGILdgLtVVQ; asst=1651464663.0; __cf_bm=YscSee9EmMoEpFEq6_FXaYhHazQGb_TedGTzY41g7M8-1651464664-0-AeNhFRkoMfh3TarohJzWv6h14kN5M7/HTv3do7kc+bw4oW477GLvOlW5Om3ZrFDaVc4fMcUVGj/qslQGwkjTk3Y=; JSESSIONID=3B517AE2C830162F2EBD87241B2D8CC9; gdsid=1651443602616:1651465251004:3FFB714567A84C43B5AC0EF9464B5748; AWSALB=iO+2Eijg/MvnjQZ4Qzcn226i+3atEoNDVRDU+Q/PeNZYzwhj9mchFcJq0KUK750MtQ8V5gtdtWMjnzgdJbEVe8mcGvZwX5Zyh0p3UpfjGRoKTWPhhBpyOAZ5fBUkBtETRfaXZ4WagZRkUhUP3Hw2dSwa1W5DKVfpULxqLmDuOI6Pe2K10ivJxH4Cpc6tTXImjAtIpGBK7iMKpI4dj65zrsSEKAI3ial2GkZQ6tDypbJpogl9+KvGY+jPb74VcS4=; AWSALBCORS=iO+2Eijg/MvnjQZ4Qzcn226i+3atEoNDVRDU+Q/PeNZYzwhj9mchFcJq0KUK750MtQ8V5gtdtWMjnzgdJbEVe8mcGvZwX5Zyh0p3UpfjGRoKTWPhhBpyOAZ5fBUkBtETRfaXZ4WagZRkUhUP3Hw2dSwa1W5DKVfpULxqLmDuOI6Pe2K10ivJxH4Cpc6tTXImjAtIpGBK7iMKpI4dj65zrsSEKAI3ial2GkZQ6tDypbJpogl9+KvGY+jPb74VcS4=; bs=dsHT2qIuA7HCvBoW_Jryng:AP5v4RUa2EwwTpwqoaYaiRZ8074XITouL3oQHRdLsfrgDwjPrr3B3EkHZ0BhBj9Ppljq0e_BSrACThJ5T4nU-1bV4ct6BZpMjdZIfZLlUoA:4RHICND803TNTI3YcIwYAeiKz_ZAvaguiZ2KAhXR1vs',
        }

        self.cookies = {
            'gdId': '8ffde0fd-1f10-4a21-97a2-94a700d14256',
            'trs': 'https%3A%2F%2Fwww.google.com%2F:SEO:SEO:2021-07-26+14%3A38%3A51.998:undefined:undefined',
            'rttdf': 'true',
            'indeedCtk': '1fj3r00vuu3d1801',
            'G_ENABLED_IDPS': 'google',
            'G_AUTHUSER_H': '0',
            'g_state': '{"i_p":1651451910859,"i_l":1}',
            'uc': '8013A8318C98C51742B255930E2D13A8FF9942ADEF1ACD4B2FCBA8282BFB4B9ACA19C9D75D42E62D564213185F212F0280885A31D257BB0F44F14343B5B7100A9EE7E514ADD19AC25FD2C8682ADE4AAAE0D97F5699DF24FF25A98BD551F2966CE89D145711558E9578D6EF8983E78ED9CD6E3CD7B1233B705E4219489C1A80BD557CA5DE69F7DBD1BECF88A8E84A8197',
            'JSESSIONID_JX_APP': '3B1784CBA17F487E7F7683B058252F89',
            'GSESSIONID': '8ffde0fd-1f10-4a21-97a2-94a700d14256+1651443602616',
            'cass': '0',
            'asst': '1651464663.0',
            'JSESSIONID': '3B517AE2C830162F2EBD87241B2D8CC9',
            '__cf_bm': 'lluqVowfn.AZIeeTxF6SZ8hofumsekoYqTUfqq1MpHU-1651466768-0-AcMaDqK/bxUu4cpIAq+4Wmk1+X8gdMuLGrsNAh4eYNmHiA0q923Ro5TMDN8CzFTgtylTTT+6anwJoO+tsOyX9ds=',
            'SameSite': 'None',
            'gdsid': '1651443602616:1651466771122:05020ED41C8BA6EE8C7E423AA4BF9ACC',
            'at': 'xz3zalV8xswJG_BvBnBywljt7RoXbUZ_nShzlA4eYNj1AsTdlGO-DcKWQ3YNdMt3LwxI6-8CY-9JNo6jnr1FizHAuYQxC1S29DRrCKxY7gF1VMppnqL_lQEyFb-e2VhTe1DZZRQkCv7S0pzrDLzFfivb4rbWrt4kZZLjP2z1iYeqpHI6VW7-s09UqhBcH-sWIqq9kR4cD68OzUJl3ZeMJdEc4sQSvDdbVhgXpYmV2LbG4qZVkhVWsjuALrNzEL0wqXQrC9tLhOiN0649NTgQEFpVG8nGG-BBE2bwGB4a3zSwGZ4TtPunWuB617Ptnt2Kua7D3Q1BN2ox0VPA7Ql7pk-Rqgzg9NpkmLLr3qB1-N5kPPMYSBLny4uxp6Iv5ajpKSlvJ3aTPmySuCiqPrzC53fH8l41yHP-TPymaYBMvhkEoYdlUl6fd6j8E7cjyiGn6B6y2g_MphO3AQEMZFmQHHLH35iNmtNLP1HUBzHnAyF3692wXRWyBjxlkDu6_jX6PVl_7zZHJbnKeN_NvupXGyjhNYcKUlInr76xXov2dWY9uO4DZ30Sw2lDlpru7FL7LSrRg66w1HasWor3_rwAeKz2iUs7rJUUE5o6jRU9UEv1_U3dVndxj2fLAUF-Nwy9o5eqVCN5YGZUkQ3o3iZDAETTdJ1q9Zx6GqSCNJBCoVpM_xCwEZPiyR_82KM-_fQ9NP95GeT76VtWLHH6dabaroS1ROhaio2j_onb_XRGwsDWTVtt-p5D_LJcae8YGA7xrnUerU4W2xeKXeZKwDVjJ6PCv7koEayivfhc_lvEZSfVecxLGceoTDrTPCOHacuJJnBZ6BaXEY6VLRoaxL8m9cuF9cgCoT9jAUtqticu7jLyqA',
            'bs': 'mg78t8x9gaXUWUGcOfayeA:QzyiM_zFw6mPvFBD8aluzE0Qe9eeUZRkftPsx_7q3IywewATzeI2nugeZ6YwPmTQ0D0jADIPXsUYsLvSVj1AnzGDwzIAzRljEusBFUGkxJw:ZZIWd1540tK5Ft9ZqCtYX_KuQL-uZFHq5MA-HWFZKfA',
            'AWSALB': 'N6KtrlI+R6EdqWIY++fHPwnjj9G5z7AYoIyyYjEFCEqKgODTAjBVCjQ6Po8ZInj2m/h5J+hqlO23iMA3PRRjrVkHS6xIV4bHK0hl+thMp1NMP5otXioGMoWAZWe4SqJ4BtK106chdMtqh4pvArD/H2IshBrQiaStSAF3X/z71Xt4u/O8XSxii4AIQoxjZBlwE0/n75fNRygsrIXelVGVutiLMd3tCT156An3NCruJ0SbTRKJb3wTu1GNZZ8C6IY=',
            'AWSALBCORS': 'N6KtrlI+R6EdqWIY++fHPwnjj9G5z7AYoIyyYjEFCEqKgODTAjBVCjQ6Po8ZInj2m/h5J+hqlO23iMA3PRRjrVkHS6xIV4bHK0hl+thMp1NMP5otXioGMoWAZWe4SqJ4BtK106chdMtqh4pvArD/H2IshBrQiaStSAF3X/z71Xt4u/O8XSxii4AIQoxjZBlwE0/n75fNRygsrIXelVGVutiLMd3tCT156An3NCruJ0SbTRKJb3wTu1GNZZ8C6IY=',
            'ADRUM_BTa': 'R:25|g:45e22f21-af48-47c5-bc6b-90aac7cf9169|n:glassdoor_17d346a0-2ec1-4454-86b0-73b3b787aee9',
        }
   
        options = Options()
        #options.add_argument("--user-data-dir=chrome-data")

        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        self.driver.set_window_size(2048, 768)

    def scrape(self, location: str = "Canada"):
        url_dict = {"suggestCount": 0, "suggestChosen":'false', "clickSource":'searchBtn', "typedKeyword":self.query, "typedLocation":location, "locT":'N', "locId":3, "jobType":'', "context":'Jobs', "sc.keyword":self.query}
        full_url = build_url(self.start_url, url_dict)
        self.driver.get(full_url)
        content = self.driver.page_source
        soup = BeautifulSoup(content, "html.parser")

        try:
            page_num = soup.find('div', {'class':'paginationFooter'}).text
            page_num = int(page_num.split(' ')[-1])
        except Exception:
            page_num = 30
        
        url = self.driver.current_url
        
        for i in tqdm(range(page_num)):
            full_url = url.split('htm')[0] + f'_IP{i+1}.htm'
            try:
                self.driver.get(full_url)
            except Exception:
                print("Error in getting page")
                continue

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            jobs = soup.find_all('li', {'class':'react-job-listing'})
            
            for job in tqdm(jobs):
                try:
                    company = job.find_all('a', {'class':'jobLink'})[1].text
                    title = job.find_all('a', {'class':'jobLink'})[2].text
                    location = job.find('span', {'class':'pr-xxsm'}).text
                    link = job.find_all('a', {'class':'jobLink'})[1].get('href')

                    description_soup = BeautifulSoup(requests.get('https://glassdoor.ca' + link, headers=self.headers, cookies=self.cookies).text, "html.parser")
                    
                    description = description_soup.find('div', {'id':'JobDescriptionContainer'})

                    job_dict = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "link": 'https://glassdoor.ca' + link,
                        "description": str(description),
                    }
                    self.jobs.append(job_dict)
                except Exception:
                    pass
        
        self.driver.quit()
        return self.jobs


class ScrapeJobs:
    """
    Class to instantiate all scraper classes and return them as a list of jobs
    """
    def __init__(self, query:str):
        self.indeed = IndeedScraper(query)
        self.glassdoor = GlassdoorScraper(query)
        self.linkedin = LinkedInScraper(query)
        self.monster = MonsterScraper(query)

def scrape_indeed(query:str, out_dir:str):
    """
    Function to scrape indeed jobs
    """
    indeed = IndeedScraper(query)
    jobs = indeed.scrape()
    
    df = pd.DataFrame(jobs)
    df.to_csv(os.path.join(out_dir, query + '.csv'), mode='a', header=not os.path.exists(f'{query}.csv'), index=False)

    print("Indeed jobs scraped", len(jobs))

def scrape_linkedin(query:str, out_dir:str):
    """
    Function to scrape linkedin jobs
    """
    linkedin = LinkedInScraper(query)
    jobs = linkedin.scrape()

    df = pd.DataFrame(jobs)
    df.to_csv(os.path.join(out_dir, query + '.csv'), mode='a', header=not os.path.exists(f'{query}.csv'), index=False)

    print("Linkedin jobs scraped", len(jobs))

def scrape_monster(query:str, out_dir):
    """
    Function to scrape monster jobs
    """

    monster = MonsterScraper(query)
    jobs = monster.scrape()
    df = pd.DataFrame(jobs)
    df.to_csv(os.path.join(out_dir, query + '.csv'), mode='a', header=not os.path.exists(f'{query}.csv'), index=False)

    print("Monster jobs scraped", len(jobs))

def scrape_glassdoor(query:str, out_dir:str):
    """
    Function to scrape glassdoor jobs
    """

    glassdoor = GlassdoorScraper(query)
    jobs = glassdoor.scrape()

    df = pd.DataFrame(jobs)
    df.to_csv(os.path.join(out_dir, query + '.csv'), mode='a', header=not os.path.exists(f'{query}.csv'),index=False)

    print("Glassdoor jobs scraped", len(jobs))


def find_jobs(query, out_dir='./'):
    """
    Function to scrape all jobs
    """
    p1 = Process(target=scrape_indeed, args=(query, out_dir))
    p2 = Process(target=scrape_linkedin, args=(query, out_dir))
    p3 = Process(target=scrape_monster, args=(query, out_dir))
    p4 = Process(target=scrape_glassdoor, args=(query, out_dir))
    p1.start()
    p2.start()
    p3.start()
    p4.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()



def main():
    parser = argparse.ArgumentParser(description='Scrape jobs from across the web.')
    parser.add_argument('--query', type=str, default=[], help='Query to search for', nargs='+',)
    parser.add_argument('--file', type=str, default='', help='File to read queries from')
    parser.add_argument('--out_dir', type=str, default='./jobs', help='Directory to save jobs to')
    parser.add_help=True
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)

    if args.file:
        with open(args.file, 'r') as f:
            queries = f.read().splitlines()
            for query in queries:
                if os.path.exists(f"{os.path.join(args.file, query + '.csv')}"):
                    continue
                find_jobs(query, out_dir=args.out_dir)
    elif args.query:
        for query in args.query:
            find_jobs(query)

if __name__ == "__main__":
    main()
    
 