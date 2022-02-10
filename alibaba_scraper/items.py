# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.item import Field


class AlibabaItem(scrapy.Item):
    productLink=Field()
    name=Field()
    price=Field()
    minOrder=Field()
    sellerYear=Field()
    sellerCountry=Field()
    sellerLink=Field()
    searchPageLink=Field()


