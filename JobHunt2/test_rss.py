import requests
import feedparser

url = "https://in.indeed.com/rss?q=python"
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
feed = feedparser.parse(response.text)
print("Found entries:", len(feed.entries))
if feed.entries:
    print(feed.entries[0].title, feed.entries[0].link)
