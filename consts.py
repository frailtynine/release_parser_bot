COS_PATTERN = r'—([^-]+)–(.+)'
STEREOGUM_PATTERN = r'\•(.*?)’[ˆs](.*)'
MONTH__DAY_PATTERN = r'([A-Za-z]+ \d{1,2})'
DAY_PATTERN = r'(\d{1,2})'
FRIDAY_DATETIME = 4
COS_URL = 'https://consequence.net/upcoming-releases/'
SG_URL = 'https://www.stereogum.com/category/album-of-the-week/'
MM_TEXTS = [
    'modest mouse',
    'модест маус',
    'good news for people who love bad news',
    'айзек брок',
    'lonesome crowded west',
    'float on',
    'флоат он',
    'айзека брока',
    'модест маус',
]


class ReleaseInfo:
    def __init__(self, message='', releases=None):
        if releases is None:
            releases = {}
        self.data = {
            'message': message,
            'releases': releases
        }

    def set_message(self, message):
        self.data['message'] = message

    def add_release(self, band_name, album_name):
        self.data['releases'][band_name] = album_name

    def add_releases_bulk(self, release_dict):
        self.data['releases'].update(release_dict)

    def remove_release(self, band_name):
        if band_name in self.data['releases']:
            del self.data['releases'][band_name]

    def get_dict(self):
        return self.data

    def get_message(self):
        return self.data['message']

    def get_releases(self, title=False):
        if title and self.data['releases']:
            return {
                k.title():
                v.title() for k, v in self.data['releases'].items()
            }
        return self.data['releases'] or {}

    def __repr__(self):
        return (
            f"ReleaseInfo(message={self.data['message']},"
            f"releases={self.data['releases']})"
        )
