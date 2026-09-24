import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=python&txtLocation=India"
response = requests.get(url, timeout=10, verify=False)
print("Status Code:", response.status_code)
soup = BeautifulSoup(response.text, 'lxml')
cards = soup.find_all('li', class_='clearfix job-bx wht-shd-bx')
print("Number of cards found:", len(cards))
if len(cards) == 0:
    print(response.text[:500])
