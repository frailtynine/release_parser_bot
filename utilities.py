import re
from datetime import datetime, timedelta
import asyncio

import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from consts import (
    COS_PATTERN,
    COS_URL,
    STEREOGUM_PATTERN,
    SG_URL,
    FRIDAY_DATETIME,
    ReleaseInfo
)


def get_friday_date() -> datetime:
    next_friday = datetime.now()
    while next_friday.weekday() != FRIDAY_DATETIME:
        next_friday += timedelta(days=1)
    return next_friday


async def parse_cos_releases() -> ReleaseInfo:
    release_info: ReleaseInfo = ReleaseInfo()
    async with aiohttp.ClientSession() as session:
        next_friday: datetime = get_friday_date()
        after_next_friday = (
            next_friday + timedelta(days=7)
        ).strftime('%B %d')
        next_friday = str(next_friday.strftime('%B %d')).replace(' 0', ' ')
        after_next_friday = str(after_next_friday).replace(' 0', ' ')
        async with session.get(COS_URL) as response:
            if response.status != 200:
                release_info.set_message('CoS doesn\'t respond')
                return release_info
            response_text = await response.text()
            soup = BeautifulSoup(response_text, features='html.parser')
            friday_tag = soup.find(
                'p',
                string=lambda t: t and next_friday in t)
            for tag in friday_tag.find_next_siblings():
                if tag.name == 'p' and after_next_friday in tag.get_text():
                    break
                album_match = re.match(COS_PATTERN, tag.get_text())
                if album_match:
                    artist = album_match.group(1).strip()
                    album = album_match.group(2).strip()
                    release_info.add_release(
                        band_name=artist.lower(),
                        album_name=album.lower()
                    )
            return release_info


async def parse_sg_releases() -> ReleaseInfo:
    release_info: ReleaseInfo = ReleaseInfo()
    # Set up Chrome options with JavaScript disabled
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # Disable JavaScript to bypass paywall
    chrome_options.add_experimental_option('prefs', {
        'profile.managed_default_content_settings.javascript': 2
    })
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(SG_URL)
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CLASS_NAME, 'article-card__title'
            ))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, features='html.parser')
        url_tag = soup.find('p', attrs={'class': 'article-card__title'})
        if not url_tag:
            release_info.set_message(
                'Could not find article card on Stereogum'
            )
            return release_info

        link_soup = url_tag.find('a')
        if not link_soup:
            release_info.set_message(
                'Could not find article link on Stereogum'
            )
            return release_info

        link = link_soup.get('href')

        # Navigate to the article page
        driver.get(link)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'title'))
        )

        article_page_source = driver.page_source
        article_soup = BeautifulSoup(
            article_page_source, features='html.parser'
        )

        title_text = article_soup.title.string
        band_name, album_title = map(str.strip, title_text.split("'")[:2])
        album_of_the_week = (
            f'Steregum album of the week: {band_name} — {album_title}'
        )

        # TODO: refactor to helper function
        date = article_soup.find('span', attrs={'class': 'date'})
        if not date:
            release_info.set_message(
                'Could not find date on Stereogum article'
            )
            return release_info

        date_object = datetime.strptime(
            date.text,
            "%B %d, %Y"
        )
        next_friday = get_friday_date()
        if date_object < next_friday - timedelta(days=7):
            release_info.set_message(
                'Stereogum has no releases for this week'
            )
            return release_info

        p_tag = article_soup.find(
            lambda tag: tag.name == 'p'
            and 'Other albums of note out this week:' in tag.text
        )
        if not p_tag:
            release_info.set_message(
                'Something wrong with Stereogum\'s list.'
            )
            return release_info

        p_tag_list = p_tag.text.split('\n')
        for line in p_tag_list:
            album_match = re.match(STEREOGUM_PATTERN, line)
            if album_match:
                artist = album_match.group(1).strip()
                album = album_match.group(2).strip()
                release_info.add_release(
                    band_name=artist.lower(),
                    album_name=album.lower()
                )
        release_info.set_message(album_of_the_week)
        return release_info

    except Exception as e:
        release_info.set_message(f'Error scraping Stereogum: {str(e)}')
        return release_info
    finally:
        if driver:
            driver.quit()


# TODO: Create a bullet-proof filtering
def combine_lists(
    data1: ReleaseInfo,
    data2: ReleaseInfo
) -> ReleaseInfo:
    releases: ReleaseInfo = ReleaseInfo()
    message = f'{data1.get_message()} \n {data2.get_message()}'
    releases.set_message(message.strip())
    all_releases = data1.get_releases()
    all_releases.update(data2.get_releases())
    releases.add_releases_bulk(all_releases)
    return releases


# # Testing purposes
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    cos_releases = loop.run_until_complete(parse_cos_releases())
    sg_releases = loop.run_until_complete(parse_sg_releases())
    merged_list = combine_lists(cos_releases, sg_releases)
    print(merged_list.get_releases(title=True))
