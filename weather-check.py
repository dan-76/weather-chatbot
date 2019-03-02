# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 18:30:55 2019

@author: ccccc
"""


from urllib.request import urlopen
from bs4 import BeautifulSoup, CData
import dateutil.parser
import re
import unittest
from textwrap import dedent
from dateutil import tz


class current_weather:
    url = 'http://rss.weather.gov.hk/rss/CurrentWeather.xml' 

    def search_or_empty(pattern, string):
        result = re.search(pattern, string)
        if result is None:
            return ''
        else:
            return result.group(1)

    def get_rss_data(self):
        html = urlopen(self.url)
        assert(html.status == 200)
        page = html.read()
        lxml_soup = BeautifulSoup(page, 'lxml')
        html_soup = BeautifulSoup(page, 'html.parser')
        des_html = html_soup.find(text=lambda tag: isinstance(tag, CData)).string.strip()
        des_item = BeautifulSoup(des_html, 'html.parser')
        des_text = des_item.get_text()
        self.status = html.status
        self.lang = html_soup.language.text
        self.author = html_soup.author.text
        self.pub_date_text = html_soup.pubdate.text
        self.pub_date = dateutil.parser.parse(self.pub_date_text)
        des_text_warning_item = des_item.find('span', {'id':'warning_message'})
        if des_text_warning_item is None:
            self.warning_msg = ""
        else:
            self.warning_msg = des_text_warning_item.text

        self.temp = search_or_empty(r'Air temperature.* (\d+).*degrees Celsius', des_text)
        self.rel_humidity = search_or_empty(r'Relative Humidity.* (\d+).*per cent', des_text)
        self.uv_index = search_or_empty(r"the mean UV Index recorded at King's Park : (\d+.\d+)", des_text)
        self.uv_level = search_or_empty(r'Intensity of UV radiation : (.*) ', des_text)
    
    def store_scrape_result(self):
        pass

    def print_scrape_result(self):
        if self.status == 200:
            result = dedent(f"""時間: {self.pub_date.astimezone(tz.tzlocal()):%Y-%m-%d %H:%M:%S}
            氣溫: {self.temp} 度
            相對濕度: 百分之 {self.rel_humidity}""")
            if self.uv_index != '':
                result += dedent(f"""
                紫外線指數: {self.uv_index}
                曝曬級數: {self.uv_level}""")
            return result
        else:
            return ''


if __name__ == '__main__':
    c1 = current_weather()
    c1.get_rss_data()
    c1.print_scrape_result()