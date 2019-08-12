# Info

This scripts job is to find all urls (hrefs, src) and check their status. If status is different then 200 it will be reported in genereted csv at the end. 

# How to run

To run this script go into console > repo location:
```
python link_checker.py https://domain-you-want-to-crawl.com/
```
It will automatically find all pages that start with url given above and crawl them looking for all links and images.
