from urllib.parse import urlencode
from path import path
import requests
from pyquery import PyQuery as pq


project_root = path(__file__).abspath().parent.parent


class Scraper(object):

    def __init__(self, session=None):
        self.session = session or requests.Session()

    def fetch_url(self, url, args=None):
        if args:
            if '?' not in url:
                url += '?'
            elif url[-1] not in ['?', '&']:
                url += '&'
            url += urlencode(args)
        def opener(url):
            resp = self.session.get(url)
            text = resp.content.decode('iso-8859-2')
            # we use utf-16 because the parser's autodetect works fine with it
            return text.encode('utf-16')
        page = pq(url, opener=opener, parser='html')
        page.make_links_absolute()
        return page


def get_cached_session():
    import requests_cache
    cache_path = project_root / '_data' / 'http_cache'
    return requests_cache.CachedSession(cache_path)


def pqitems(ob, selector=None):
    cls = type(ob)
    if selector is None:
        found = ob
    else:
        found = ob(selector)
    return (cls(el) for el in found)
