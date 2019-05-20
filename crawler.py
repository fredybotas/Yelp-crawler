import requests
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)

BASE_YELP_URL = 'https://www.yelp.ie/'

YELP_NOT_RECOMMENDED_REVIEWS_POSTFIX = 'not_recommended_reviews/'
YELP_RECOMMENDED_REVIEWS_POSTFIX = 'biz/'

NOT_RECOMMENDED_REVIEWS_OFFSET = '?not_recommended_start='
RECOMMENDED_REVIEWS_OFFSET = '?start='
REVIEW_REMOVED_TAG = 'This review has been removed' \
                     ' for violating our Terms of Service'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/70.0.3538.77 Safari/537.36'}


logger = logging.getLogger()


class Review:
    def __init__(self, review_container):
        self.review_container = review_container
        self.content = None
        self.author = None
        self.rating = None

    def get_review_content_from_container(self):
        logger.debug('Parsing review content')
        review_content = self.review_container \
            .find('div', class_='review-content') \
            .find('p')
        review = review_content.contents
        review = [str(a) for a in review]
        review = ''.join(review).replace('<br/>', ' ')
        self.content = review

    def get_review_author_from_container(self):
        logger.debug('Parsing review author')
        review_author_info = self.review_container \
            .find('div', class_='review-sidebar')

        review_author_name = review_author_info \
            .find(class_='user-display-name')
        if review_author_name is not None:
            review_author_name = review_author_name.contents
        else:
            review_author_name = 'Unknown'

        review_author_reviews_count = review_author_info \
            .find('li', class_='review-count') \
            .find('b').contents[0]

        review_author_friends_count = review_author_info \
            .find('li', class_='friend-count') \
            .find('b').contents[0]

        self.author = (''.join(review_author_name),
                       review_author_friends_count,
                       review_author_reviews_count)

    def get_review_rating_from_container(self):
        logger.debug('Parsing review rating')
        review_rating = self.review_container \
            .find('div', class_='review-content') \
            .find('div', class_='i-stars')['title'].split(' ')[0]
        self.rating = review_rating


class Business:

    def __init__(self, name):
        self.name = name

    def __parse_reviews_from_page(self, page):
        logger.info('Parsing reviews')
        soup = BeautifulSoup(page, 'html.parser')

        reviews_container = soup.find_all('div',
                                          class_='review review--with-sidebar')

        result = []
        for review_container in reviews_container:
            review = Review(review_container)
            review.get_review_content_from_container()
            if review.content == REVIEW_REMOVED_TAG:
                logger.debug('Review removed')
                continue
            review.get_review_rating_from_container()
            review.get_review_author_from_container()
            logger.info('Got review review={}, author={}, rating={}'
                        .format(review.content[:10], review.author,
                                review.rating))
            result.append(review)

        return result

    def __get_reviews_for_biz(self, url):
        offset = 0
        reviews = []
        while True:
            current_url = url.format(str(offset))
            page = requests.get(current_url, headers=HEADERS)
            logger.info('Gonna parse reviews for from={}'
                        .format(current_url))

            reviews_batch = self.__parse_reviews_from_page(page.content)
            if len(reviews_batch) == 0:
                break

            reviews += reviews_batch
            offset += len(reviews_batch)

        return reviews

    def get_recommended_reviews_for_biz(self):
        biz_recommended_review_url = BASE_YELP_URL \
                                     + YELP_RECOMMENDED_REVIEWS_POSTFIX \
                                     + self.name \
                                     + RECOMMENDED_REVIEWS_OFFSET \
                                     + '{}'
        return self.__get_reviews_for_biz(biz_recommended_review_url)

    def get_not_recommended_reviews_for_biz(self):
        biz_not_recommended_review_url = BASE_YELP_URL \
                                         + YELP_NOT_RECOMMENDED_REVIEWS_POSTFIX \
                                         + self.name \
                                         + NOT_RECOMMENDED_REVIEWS_OFFSET \
                                         + '{}'
        return self.__get_reviews_for_biz(biz_not_recommended_review_url)


def get_businesses(query, count):
    offset = 0
    businesses = []
    while True:
        url = BASE_YELP_URL + 'search?find_desc=&find_loc={}&start={}'.format(
            query, str(offset))
        page = requests.get(url, headers=HEADERS)
        logger.info('Parsing businesses at:{}'.format(url))

        businesses_batch = BeautifulSoup(page.content, 'html.parser') \
            .find_all(class_='lemon--a__373c0__IEZFH link__373c0__29943 '
                             'link-color--blue-dark__373c0__1mhJo '
                             'link-size--inherit__373c0__2JXk5')
        temp = []
        for business in businesses_batch:
            if '?' in business['href']:
                continue
            temp.append(business['href'].split('/')[2])

        businesses_batch = temp

        if len(businesses_batch) == 0:
            break
        businesses += businesses_batch
        offset += len(businesses_batch)

        if offset >= count:
            break

    return businesses[:count]


businesses = get_businesses('London', 100)
for business in businesses:
    print(Business(business).get_not_recommended_reviews_for_biz())
