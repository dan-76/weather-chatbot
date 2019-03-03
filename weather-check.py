# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 18:30:55 2019

@author: ccccc
"""


from urllib.request import urlopen
from bs4 import BeautifulSoup, CData
import dateutil.parser
from dateutil import tz
import re
import unittest
from textwrap import dedent


class current_weather:
    url = 'http://rss.weather.gov.hk/rss/CurrentWeather.xml' 
    url_uc = 'http://rss.weather.gov.hk/rss/CurrentWeather_uc.xml' 

    def search_or_empty(self, pattern, string):
        result = re.search(pattern, string)
        if result is None:
            return ''
        else:
            return result.group(1)
    
    def get_soup_from_url(self, url):
        html = urlopen(url)
        assert(html.status == 200)
        page = html.read()
        return BeautifulSoup(page, 'html.parser')
    
    def get_soup_for_cdata(self, htmlsoup):
        des_html = html_soup.find(text=lambda tag: isinstance(tag, CData)).string.strip()
        return BeautifulSoup(des_html, 'html.parser')

    def get_rss_data(self):
        """This is to download default url data as below:
        status -- html status
        lang -- language
        author
        pub_date -- publish date
        warning_msg -- weather warning message
        temp -- tempature
        rel_humidity -- relative humidity
        uv_index -- UV index of past 1 hour
        uv_level -- UV level of past 1 hour
        """
        html_soup = self.get_soup_from_url(self.url)
        des_item = self.get_soup_for_cdata(html_soup)
        des_text = des_item.get_text()
        self.status = html.status
        self.lang = html_soup.language.text
        self.author = html_soup.author.text
        pub_date_text = html_soup.pubdate.text
        self.pub_date = dateutil.parser.parse(pub_date_text)

        self.temp = self.search_or_empty(r'Air temperature.* (\d+).*degrees Celsius', des_text)
        self.rel_humidity = self.search_or_empty(r'Relative Humidity.* (\d+).*per cent', des_text)
        self.uv_index = self.search_or_empty(r"the mean UV Index recorded at King's Park : (\d+.\d+)", des_text)
        self.uv_level = self.search_or_empty(r'Intensity of UV radiation : (.*) ', des_text)

        #Warning in Chinese Source
        html_soup_uc = self.get_soup_from_url(self.url_uc)
        des_item_uc = self.get_soup_for_cdata(html_soup_uc)
        des_text_warning_item = des_item_uc.find('span', {'id':'warning_message'})
        if des_text_warning_item is None:
            self.warning_msg = ""
        else:
            self.warning_msg = des_text_warning_item.text
    
    def store_scrape_result(self):
        pass

    def scrape_result(self):
        if self.status == 200:
            result = dedent(f"""
            時間: {self.pub_date.astimezone(tz.tzlocal()):%Y-%m-%d %H:%M:%S}
            氣溫: {self.temp} 度
            相對濕度: 百分之 {self.rel_humidity}""")

            if self.uv_index != '':
                result += dedent(f"""
                紫外線指數: {self.uv_index}
                曝曬級數: {self.uv_level}""")

            if self.warning_msg !='':
                result += dedent(f"""
                {self.warning_msg}""")
            return result
        else:
            return ''


if __name__ == '__main__':
    c1 = current_weather()
    c1.get_rss_data()
    print(c1.scrape_result())