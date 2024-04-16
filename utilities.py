import requests
import re
from datetime import datetime, timedelta
from typing import Optional
import asyncio

import aiohttp
from bs4 import BeautifulSoup


COS_PATTERN = r'—([^-]+)–(.+)'
STEREOGUM_PATTERN = r'\•(.*?)’[ˆs](.*)'
MONTH__DAY_PATTERN = r'([A-Za-z]+ \d{1,2})'
DAY_PATTERN = r'(\d{1,2})'
FRIDAY_DATETIME = 4
COS_URL = 'https://consequence.net/upcoming-releases/'
SG_URL = 'https://www.stereogum.com/category/album-of-the-week/'


def get_friday_date() -> datetime:
    next_friday = datetime.now()
    while next_friday.weekday() != FRIDAY_DATETIME:
        next_friday += timedelta(days=1)
    return next_friday


# TODO: refactor album parsing part to a helper function
async def parse_cos_releases() -> list[tuple[str, str]]:
    async with aiohttp.ClientSession() as session:
        next_friday: datetime = get_friday_date()
        after_next_friday: datetime = (
            next_friday + timedelta(days=7)
        ).strftime('%B %d')
        async with session.get(COS_URL) as response:
            if response.status != 200:
                return [('Consequence of Sound doesn\'t respond', '')]
            response_text = await response.text()
            soup = BeautifulSoup(response_text, features='html.parser')
            friday_tag = soup.find(
                'p',
                string=lambda t: t and next_friday.strftime('%B %d') in t)
            records = []
            for tag in friday_tag.find_next_siblings():
                if tag.name == 'p' and after_next_friday in tag.get_text():
                    break
                album_match = re.match(COS_PATTERN, tag.get_text())
                if album_match:
                    artist = album_match.group(1).strip()
                    album = album_match.group(2).strip()
                    records.append((artist.lower(), album.lower()))
            return records


async def parse_sg_releases():
    async with aiohttp.ClientSession() as session:
        async with session.get(SG_URL) as response:
            if response.status != 200:
                return [('Stereogum doesn\'t respond', '')]
            response_text = await response.text()
            soup = BeautifulSoup(response_text, features='html.parser')
            url_tag = soup.find('p', attrs={'class': 'article-card__title'})
            link_soup = url_tag.find('a')
            link = link_soup.get('href')
            article_response = requests.get(link)
            article_soup = BeautifulSoup(
                article_response.text,
                features='html.parser'
            )
            # TODO: refactor to helper function
            date = article_soup.find('span', attrs={'class': 'date'})
            date_object = datetime.strptime(
                date.text, 
                "%B %d, %Y"
            )
            next_friday = get_friday_date()
            if date_object < next_friday - timedelta(days=7):
                return [('__Stereogum has no releases for this week', 'come later')]
            p_tag = article_soup.find(
                lambda tag: tag.name == 'p'
                and 'Other albums of note out this week:' in tag.text
            )
            if not p_tag:
                return [('Something wrong with Stereogum\'s list.', '')]
            p_tag_list = p_tag.text.split('\n')
            records = []
            for line in p_tag_list:
                album_match = re.match(STEREOGUM_PATTERN, line)
                if album_match:
                    artist = album_match.group(1).strip()
                    album = album_match.group(2).strip()
                    records.append((artist.lower(), album.lower()))
            return records


# TODO: Create a bullet-proof filtering
def combine_lists(
    data1: Optional[list[tuple[str, str]]],
    data2: Optional[list[tuple[str, str]]]
) -> list[tuple[str, str]]:
    if not data1:
        return data2
    elif not data2:
        return data1
    elif not data1 and not data2:
        return [('No results at all', 'for some reason')]
    merged_list = set(data1 + data2)
    sorted_list = sorted(merged_list, key=lambda x: x[0])
    return sorted_list

# # Testing purposes 
# if __name__ == '__main__':
#     loop = asyncio.get_event_loop()
#     cos_releases = loop.run_until_complete(parse_cos_releases())
#     sg_releases = loop.run_until_complete(parse_sg_releases())
#     merged_list = combine_lists(cos_releases, sg_releases)
#     for item in merged_list:
#         print(f'{item[0].title()} — {item[1].title()}')
