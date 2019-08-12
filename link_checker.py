import requests
from bs4 import BeautifulSoup
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import logging
import time
import configparser
import csv
import sys
import re
import os
from pathlib import Path


class LinkScrapper:
    def __init__(self, site_url):
        self.site_url = site_url
        self.passed = set()
        self.failed = set()
        self.seen = set()
        self.to_crawl = Queue()
        self.pool = ThreadPoolExecutor(max_workers=10)
        self.cfg = configparser.ConfigParser()
        self.element_found = set()
        self.csv_name = str(self.site_url[7:]).replace('/', '_')
        self.to_crawl.put((None, site_url))

    def find_href(self, link, url):
        href = link['href']
        if href not in self.seen:
            if re.match('^https?://', href):
                self.to_crawl.put((url, link.get('href')))
            elif re.match('^\/[a-z0-9]+', href):
                self.to_crawl.put(
                    (url, self.site_url.strip('/') + link.get('href')))
            elif re.match('^\/\/[a-z0-9]+', href):
                self.to_crawl.put(
                    (url, 'http://' + link.get('href').strip('/')))

    def find_image(self, images, url):
        keywords = ['script', 'iframe']
        if any(word in str(images) for word in keywords):
            return
        else:
            image = images['src']
            if image not in self.seen:
                if re.match('^https?://', image):
                    self.to_crawl.put((url, images.get('src')))
                elif image.startswith('//'):
                    self.to_crawl.put(
                        (url, 'http://' + images.get('src').strip('//')))

    def get_sublinks(self, html, url):
        soup = BeautifulSoup(html, 'lxml')
        body = soup.find('body')
        hrefs = body.find_all(href=True)
        images = body.find_all(src=True)
        # tables = body.find_all('div', {'class': 'how-to-apply-table'})
        # if tables:
        #     self.element_found.add(url)
        for link in hrefs:
            self.find_href(link, url)
        for src in images:
            self.find_image(src, url)

    def scrape_page(self, target):
        parent = target[0]
        data = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'
            }
        url = target[1].lower()
        request = requests.get(url, headers=data)
        status = request.status_code
        if status != 200:
            self.failed.add((parent, url, status))
        else:
            self.passed.add((url))
            if url.startswith(self.site_url) and not url.endswith((".png", ".jpg", ".pdf", ".gif")):
                self.get_sublinks(request.text, url)

    def run_scraper(self):
        while True:
            try:
                target = self.to_crawl.get(timeout=1)
                url = target[1]
                if url not in self.seen:
                    print("Scraping URL: {}".format(url))
                    self.seen.add(url)
                    self.pool.submit(self.scrape_page, target)
            except Empty:
                self.pool.shutdown(wait=True)
                if self.to_crawl.empty():
                    return self.passed, self.failed
                else:
                    self.pool = ThreadPoolExecutor(max_workers=10)

    def save_to_csv(self):
        root = Path(os.path.dirname(os.path.abspath(__file__)))
        csv_folder = root / 'csv'
        csv_file = csv_folder / f'{self.csv_name}.csv'
        with open(csv_file, "w") as output:
            titles = ['Code', 'Broken Link', 'Parent']
            writer = csv.DictWriter(output, fieldnames=titles)
            writer.writeheader()
            for val in list(self.failed):
                writer.writerow({
                    'Code': val[2],
                    'Broken Link': val[1],
                    'Parent': val[0],
                })


def main():
    # If logging is needed for debugging use below
    # logging.basicConfig(
    #     filename='scrap.log',
    #     level=logging.DEBUG,
    #     format="%(asctime)s:%(levelname)s: %(threadName)10s %(message)s"
    # )
    scrap = LinkScrapper(sys.argv[1])
    if len(sys.argv[1]) < 2:
        print(
            "Error: Missing link. Make sure Your link starts with http(s):// and ends with /")
        quit()
    start = time.time()
    scrap.run_scraper()
    print("Entire job took: ", time.time() - start)
    print("Links passed: " + str(len(scrap.passed)))
    print("Links failed: " + str(len(scrap.failed)))
    scrap.save_to_csv()


if __name__ == "__main__":
    main()
