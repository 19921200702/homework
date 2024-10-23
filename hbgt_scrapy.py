import scrapy
# pip install scrapy
from scrapy.crawler import CrawlerProcess
import os
import csv
from urllib.parse import urljoin
import re
import datetime

class ExtractAllPagesSpider(scrapy.Spider):
    name = 'extract_all_pages'

    # 初始化需要抓取的网站url
    init_urls = [
        'https://www.hbgt.edu.cn/djkxh/dqgz.htm',
        'https://www.hbgt.edu.cn/zhxw/jcdt2.htm',
        'https://www.hbgt.edu.cn/index/tzgg.htm',
        'https://www.hbgt.edu.cn/index/xxxw.htm'
    ]
    
    start_urls = init_urls
    start_urls_dict = {}
    year_threshold = 2024  # 设置年份界限，小于该年份的数据不会被导出

    def parse(self, response):
        base_url = re.match(r'^(.*\/)[^\/]*\.htm$', response.url).group(1)
        
        # Check if the page has <ul> content in <div class="side_nav">
        side_nav = response.css('div.side_nav ul li a')
        if side_nav:
            for nav_item in side_nav:
                li_text = nav_item.css('::text').get()
                href = nav_item.attrib['href'].replace('../', '')
                full_link = urljoin(base_url, href)
                self.start_urls_dict[f'{li_text}.csv'] = full_link
        else:
            # If no <ul> content, use the <h2> content as the file name
            h2_text = response.css('div.side_nav h2::text').get()
            if h2_text:
                file_name = f'{h2_text}.csv'
                self.start_urls_dict[file_name] = response.url

        # Once start_urls_dict is generated, start extracting data
        for file_name, start_url in self.start_urls_dict.items():
            yield scrapy.Request(url=start_url, callback=self.parse_list_content, meta={'file_name': file_name})

    def parse_list_content(self, response):
        # Extract the file name from meta
        file_name = response.meta['file_name']
        
        # Extract the desired information from <div class="list">
        list_items = response.css('div.list ul li a')

        # 写入csv
        data = []
        for item in list_items:
            title = item.css('p::text').get()  # Extract text from <p> tag
            date = item.css('span::text').get()
            if date:
                try:
                    date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
                    # TODO: Add any pre-processing needed before writing the date to CSV
                    date_str = date_obj.strftime("%Y%m%d")
                    if int(date_str[:4]) >= self.year_threshold:
                        date = date_str
                        href = item.attrib['href']
                        full_link = urljoin(response.url, href)
                        data.append([title, date, full_link])
                except ValueError:
                    pass

        # Write data to CSV
        self.write_to_csv(file_name, data)

        # Handle pagination
        next_page = response.css('div.page span.p_next a::attr(href)').get()
        if next_page:
            next_page_url = urljoin(response.url, next_page)
            yield response.follow(next_page_url, self.parse_list_content, meta={'file_name': file_name})

    def write_to_csv(self, file_name, data):
        # Create the directory for the CSV files if not exist
        if not os.path.exists('output'):
            os.makedirs('output')

        # Write content to a CSV file named with the file name
        filename = f'output/{file_name}'
        with open(filename, 'a', newline='', encoding='utf-8') as f:  # Use 'a' to append data if the file exists
            writer = csv.writer(f)
            if os.stat(filename).st_size == 0:
                writer.writerow(['XYDTXXBT', 'DTFBRQ', 'XYDTXXWBFWLJ'])  
                # XYDTXXBT 校园动态信息标题
                # DTFBRQ 动态发布日期
                # XYDTXXWBFWLJ 校园动态信息外部访问链接
            writer.writerows(data)

# Run the spider
process = CrawlerProcess()
process.crawl(ExtractAllPagesSpider)
process.start()
