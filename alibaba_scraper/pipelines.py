# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import mysql.connector
from mysql.connector import errorcode


class AlibabaPipeline(object):
    def __init__(self, **kwargs):
        try:
            self.conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='root',
                database='alibaba_scraper'
            )
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Wrong  username or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)

    def open_spider(self, spider):
        print('spider start')

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        """Insert information of AlibabaItem into database"""

        query = (
            "INSERT INTO alibaba_item "
            "(product_link,name,price,min_order,seller_year,seller_country,seller_link,search_page_link) "
            "VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
        )

        try:
            # Insert new row
            print("Saving item into db ...")
            self.cursor.execute(query, (item['productLink'], item['name'], item['price'], item['minOrder'],
                                        item['sellerYear'], item['sellerCountry'], item['sellerLink'],
                                        item['searchPageLink']))
            lastRecordId = self.cursor.lastrowid

            # Make sure data is committed to the database
            self.conn.commit()
            print("Item saved with ID: {}".format(lastRecordId))
        except Exception as err:
            print(err)

        return item
