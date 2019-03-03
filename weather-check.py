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

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from textwrap import dedent
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)


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
        des_html = htmlsoup.find(text=lambda tag: isinstance(tag, CData)).string.strip()
        return BeautifulSoup(des_html, 'html.parser')

    def get_rss_data(self):
        """This is to download default url data as below:
        status -- html status
        lang -- language
        author
        pub_date -- publish date
        weather_img_no -- image icon number for the weather summary
        temp -- tempature
        rel_humidity -- relative humidity
        uv_index -- UV index of past 1 hour
        uv_level -- UV level of past 1 hour
        predict -- HKO special prediction
        warning_msg -- weather warning message
        """
        html_soup = self.get_soup_from_url(self.url)
        des_item = self.get_soup_for_cdata(html_soup)
        self.des_text = des_item.get_text()
        self.lang = html_soup.language.text
        self.author = html_soup.author.text
        pub_date_text = html_soup.pubdate.text
        self.pub_date = dateutil.parser.parse(pub_date_text)
        weather_img_url = des_item.find('img')['src']
        self.weather_img_no = self.search_or_empty(r'http://rss.weather.gov.hk/img/pic(\d+).png', weather_img_url)
        self.temp = self.search_or_empty(r'Air temperature.* (\d+).*degrees Celsius', self.des_text)
        self.rel_humidity = self.search_or_empty(r'Relative Humidity.* (\d+).*per cent', self.des_text)
        self.uv_index = self.search_or_empty(r"the mean UV Index recorded at King's Park.* (\d+)", self.des_text)
        self.uv_level = self.search_or_empty(r'Intensity of UV radiation : (\S*) ', self.des_text)
        self.rainfall_exist = self.search_or_empty(r'(.*the rainfall recorded in various regions were.*)', self.des_text)
        if self.rainfall_exist != '':
            rainfall_table = des_item.find_all('table')[1]
            self.rainfall_data = [x.text for x in rainfall_table.find_all('tr')]

        #Warning in Chinese Source
        html_soup_uc = self.get_soup_from_url(self.url_uc)
        des_item_uc = self.get_soup_for_cdata(html_soup_uc)
        self.predict = self.search_or_empty(u'(預 料 .*)', des_item_uc.get_text())
        des_text_warning_item = des_item_uc.find('span', {'id':'warning_message'})
        if des_text_warning_item is None:
            self.warning_msg = ""
        else:
            self.warning_msg = des_text_warning_item.text

    def store_scrape_result(self):
        pass

    def scrape_result(self):
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

        if self.predict !='':
            result += dedent(f"""
            {self.predict}""")

        return result


class weathertelebot:
    def __init__(self, tgToken):
        self.token = tgToken
    
    def start_def_bot(self):
        self.updater = Updater(token=self.token)
        dispatcher = self.updater.dispatcher

        def start(bot, update):
            bot.send_message(chat_id=update.message.chat_id, 
            text=dedent("""
            You can control me by sending these commands:
            
            /weather - get the current weather report"""))

        start_handler = CommandHandler('start', start)
        dispatcher.add_handler(start_handler)

        def get_weather(bot, update):
            c1 = current_weather()
            c1.get_rss_data()
            bot.send_message(chat_id=update.message.chat_id, text=c1.scrape_result())
            del c1

        get_weather_handler = CommandHandler('weather', get_weather)
        dispatcher.add_handler(get_weather_handler)

    def start_bot_host(self):
        self.updater.start_polling()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Host the telegram bot of weather')
    parser.add_argument('tgToken', metavar='string token',
                        help='This is the token for bot')
    args = parser.parse_args()

    t1 = weathertelebot(args.tgToken)
    t1.start_def_bot()
    t1.start_bot_host()