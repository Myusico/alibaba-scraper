from twisted.internet import reactor
from alibaba_scraper.spiders.alibaba import AlibabaSpider
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerRunner


def crawl_job():
    """
    Job to start spiders.
    Return Deferred, which will execute after crawl has completed.
    """
    settings = get_project_settings()
    runner = CrawlerRunner(settings)
    return runner.crawl(AlibabaSpider)


def schedule_next_crawl(null, sleep_time):
    """Schedule the next crawl"""
    reactor.callLater(sleep_time, crawl)


def crawl():
    """A "recursive" function that schedules a crawl 300 seconds after each crawl."""
    # crawl_job() returns a Deferred
    d = crawl_job()
    # call schedule_next_crawl(<scrapy response>, n) after crawl job is complete
    d.addCallback(schedule_next_crawl, 300)
    d.addErrback(catch_error)


def catch_error(failure):
    print(failure.value)


if __name__ == "__main__":
    crawl()
    reactor.run()
