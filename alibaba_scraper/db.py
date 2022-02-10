import mysql.connector


def init_db():
    """Create alibaba_item and scrape_progress tables in alibaba_scraper database"""

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='alibaba_scraper',
    )
    cursor = conn.cursor()

    schema = [
        "DROP TABLE IF EXISTS alibaba_item",
        "DROP TABLE IF EXISTS scrape_progress",
        "CREATE TABLE alibaba_item (id INTEGER PRIMARY KEY AUTO_INCREMENT,product_link VARCHAR(255) UNIQUE NOT NULL,"
        "name VARCHAR(255) NOT NULL,price VARCHAR(255),min_order VARCHAR(32),seller_year INTEGER,"
        "seller_country VARCHAR(32),seller_link VARCHAR(255),search_page_link VARCHAR(255))",
        "CREATE TABLE scrape_progress(id INTEGER PRIMARY KEY AUTO_INCREMENT,url VARCHAR(255),page_num INTEGER,"
        "completed BOOLEAN)"
    ]
    for query in schema:
        cursor.execute(query)

    file_path = '/google-10000-english.txt'
    with open(file_path, mode='r') as f:
        keywords = f.read().splitlines()
    query = "INSERT INTO scrape_progress (url,page_num,completed) VALUES (%s,%s,%s)"
    for keyword in keywords:
        url = f"https://www.alibaba.com/trade/search?IndexArea=product_en&SearchText={keyword}&page="
        cursor.execute(query, (url, 1, 0))
    conn.commit()


if __name__ == '__main__':
    init_db()
