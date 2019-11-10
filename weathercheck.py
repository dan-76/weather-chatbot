# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 18:30:55 2019

@author: ccccc
"""


from urllib.request import urlopen
from bs4 import BeautifulSoup, CData
import dateutil.parser
from dateutil import tz
import unittest
import re
import os
from textwrap import dedent

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

try:
    import urlparse
    from urllib import urlencode
except: # For Python 3
    import urllib.parse as urlparse
    from urllib.parse import urlencode

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from textwrap import dedent
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)


class currentWeather:
    url = 'http://rss.weather.gov.hk/rss/CurrentWeather.xml' 
    url_uc = 'http://rss.weather.gov.hk/rss/CurrentWeather_uc.xml' 

    def __init__(self):
        pass

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


class rainNowcast:
    url = ''
    driver_path = r'..\chromedriver.exe'

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        self.driver = webdriver.Chrome(self.driver_path, options=options)

    def __del__(self):
        self.driver.quit()
    
    def update_url(self, lat, lon):
        base_url = r'https://www.weather.gov.hk/m/nowcast/hk_rainfall_uc.htm'
        params = {'lat':str(lat),'lon':str(lon)}
        url_parts = list(urlparse.urlparse(base_url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query)
        return urlparse.urlunparse(url_parts)

    def map_rain_result(self, in_list, long=False):
        result_dict_long = {
            'noRain' : "無雨或0.5毫米以下",
            'rain01' : "小雨: 0.5 毫米 - 2.5 毫米",
            'rain02' : "中雨: 2.5 毫米 - 10 毫米",
            'rain03' : "大雨: 10 毫米或以上圖示",
            'none' : "無"
        }
        result_dict_short = {
            'noRain' : "無雨",
            'rain01' : "小雨",
            'rain02' : "中雨",
            'rain03' : "大雨",
            'none' : "無"
        }
        if not long:
            return [result_dict_short[x] for x in in_list]
        else:
            return [result_dict_long[x] for x in in_list]

    def noRain_or_result(self, rpath):
        p = re.search(r'images/(.*).png', rpath)
        if p is None:
            return 'none'
        else:
            return p.group(1)

    def initiate_with_url(self, url):
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, './/div[@id="fcImageDiv01"]')))
        except TimeoutException:
            pass

    def get_src_by_xpath(self, xpath):
        return [x.get_attribute("src") for x in self.driver.find_elements_by_xpath(xpath)]
    
    def get_text_by_xpath(self,xpath):
        return [x.text for x in self.driver.find_elements_by_xpath(xpath)]

    def forcast_will_rain(self):
        return any(x in ['rain01','rain02','rain03'] for x in self.result_img_list)

    def get_nowcast_data(self, lat, lon):
        """This is to download default url with parameter data as below:

        Parameters
        ----------
        lat : latitude of location in Hong Kong
        lon : longitude of location in Hong Kong


        url -- url + parameters(lat, lon)
        result_img_list -- images of forcasts in url
        result_list -- keywords of rain forcasts in url
        time_list -- time frame accordingly of rain forcasts in url
        zip_result -- zipping of time_list & result_list
        """
        self.url = self.update_url(lat,lon)
        self.initiate_with_url(self.url)
        
        result_imgs = self.get_src_by_xpath('.//div[contains(@id,"timeSeriesImgDiv0")]/img')
        self.result_img_list = [self.noRain_or_result(x) for x in result_imgs]
        self.result_list = self.map_rain_result(self.result_img_list)
        self.time_list = self.get_text_by_xpath('.//td[contains(@id,"timeLabel0")]')

        self.zip_result = [x for x in zip(['<' + x for x in self.time_list[1:]], self.result_list)]

    def scrape_result(self):
        if self.forcast_will_rain():
            result_umb = '來緊兩小時會落雨, 記得帶遮'
        else:
            result_umb = ''
        result_nowcast = '\n'.join(["{}: {}".format(z,y) for z,y in self.zip_result])
        result = dedent(f"""
        {result_umb}

        天氣預測:
        """)
        result += dedent(f"""{result_nowcast}""")

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
            
            /weather - get the current weather report
            Send location - get rain forcast for the location"""))

        start_handler = CommandHandler('start', start)
        dispatcher.add_handler(start_handler)

        def get_weather(bot, update):
            c1 = currentWeather()
            c1.get_rss_data()
            bot.send_message(chat_id=update.message.chat_id, text=c1.scrape_result())
            del c1

        get_weather_handler = CommandHandler('weather', get_weather)
        dispatcher.add_handler(get_weather_handler)

        def echo_location(bot, update):
            r1 = rainNowcast()
            r1.get_nowcast_data(update.message.location.latitude,update.message.location.longitude)
            bot.send_message(chat_id=update.message.chat_id, text=r1.scrape_result())
            del r1

        echolo_handler = MessageHandler(Filters.location, echo_location)
        dispatcher.add_handler(echolo_handler)

    def start_bot_host(self):
        self.updater.start_polling()


class TestRainNowcast(unittest.TestCase):
    def setUp(self):
        pass

    def test_driver_path(self):
        self.assertTrue(os.path.isfile(rainNowcast.driver_path))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Host the telegram bot of weather')
    parser.add_argument('tgToken', metavar='string token',
                        help='This is the token for bot')
    args = parser.parse_args()

    t1 = weathertelebot(args.tgToken)
    t1.start_def_bot()
    t1.start_bot_host()