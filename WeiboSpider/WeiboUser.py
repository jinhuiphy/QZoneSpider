# -*- coding: UTF-8 -*-

import re
import requests
import sys
import traceback
from datetime import datetime
from datetime import timedelta
from lxml import etree
import pymongo
import random
import time as systime
from agent import agents
from cookies import cookies


class WeiboUser:
    """将一个微博用户抽象为一个类，该类主要用来爬取用户个人信息及其微博数据"""

    # WeiboUser类初始化
    def __init__(self, user_id, start_page, filte=0):
        self.user_id = user_id  # 用户id，即需要我们输入的数字，如昵称为“Dear-迪丽热巴”的id为1669879400
        self.filter = filte  # 取值范围为0、1，程序默认值为0，代表要爬取用户的全部微博，1代表只爬取用户的原创微博
        self.username = ''  # 用户名，如“Dear-迪丽热巴”
        self.weibo_num = 0  # 用户全部微博数
        self.weibo_num2 = 0  # 爬取到的微博数
        self.following = 0  # 用户关注数
        self.followers = 0  # 用户粉丝数
        self.start_page = start_page    # 开始爬的微博页数

        # 判断爬取的微博是所有微博还是仅原创微博
        if self.filter:
            self.flag = "原创微博内容"
        else:
            self.flag = "所有微博内容"

        # 建立微博数据库
        dbClient = pymongo.MongoClient(host='localhost', port=27017)
        Weibo = dbClient['Weibo']
        self.WeiboData = Weibo[str(user_id)]
        if self.start_page == 1:
            if self.WeiboData.find():
                print("正在清空数据库")
                self.WeiboData.remove({})
        else:
            print("上次爬到第%s页,正在续爬" % self.start_page)

        # 随机选取浏览器
        ua = random.choice(agents)
        self.headers = {'User-Agent': ua}

        # 随机选取cookies
        # self.cookie = random.choice(cookies)
        self.cookie = cookies[0]

    # 获取用户昵称
    def get_username(self):
        try:
            url = "https://weibo.cn/%d/info" % self.user_id
            html = requests.get(url, cookies=self.cookie, headers=self.headers).content
            selector = etree.HTML(html)
            username = selector.xpath("//title/text()")[0]
            self.username = username[:-3]
            print(u"用户名: " + self.username)
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    # 获取用户微博数、关注数、粉丝数
    def get_user_info(self):
        try:
            url = "https://weibo.cn/u/%d?filter=%d&page=1" % (
                self.user_id, self.filter)
            html = requests.get(url, cookies=self.cookie, headers=self.headers).content
            selector = etree.HTML(html)
            pattern = r"\d+\.?\d*"

            # 微博数
            str_wb = selector.xpath(
                "//div[@class='tip2']/span[@class='tc']/text()")[0]
            guid = re.findall(pattern, str_wb, re.S | re.M)
            wb_num = 0
            for value in guid:
                wb_num = int(value)
                break
            self.weibo_num = wb_num
            print(u"微博数: " + str(self.weibo_num))

            # 关注数
            str_gz = selector.xpath("//div[@class='tip2']/a/text()")[0]
            guid = re.findall(pattern, str_gz, re.M)
            self.following = int(guid[0])
            print(u"关注数: " + str(self.following))

            # 粉丝数
            str_fs = selector.xpath("//div[@class='tip2']/a/text()")[1]
            guid = re.findall(pattern, str_fs, re.M)
            self.followers = int(guid[0])
            print(u"粉丝数: " + str(self.followers))

        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    # 将用户信息保存到数据库
    def save_user_info(self):
        if self.filter:
            flag = "原创微博内容"
        else:
            flag = "所有微博内容"
        try:
            # 保存用户信息
            user_info = {
                '用户名': self.username,
                '用户ID': str(self.user_id),
                '微博数': self.weibo_num,
                '关注数': self.following,
                '粉丝数': self.followers,
                '爬取微博类型': flag
            }
            self.WeiboData.insert_one(user_info)
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    # 获取并保存用户微博ID、微博内容及对应的发布时间、发布设备、点赞数、转发数、评论数
    def get_save_weibo(self):
        try:
            url = "https://weibo.cn/u/%d?filter=%d&page=1" % (
                self.user_id, self.filter)
            html = requests.get(url, cookies=self.cookie, headers=self.headers).content
            selector = etree.HTML(html)

            # 获得微博的总页数，如果没有找到该元素，则定为1
            page_info = selector.xpath("//input[@name='mp']")
            if not page_info:
                page_num = 1
            else:
                page_num = int(page_info[0].attrib["value"])
            pattern = r"\d+\.?\d*"

            for page in range(self.start_page, page_num + 1):
                # 每爬50页就切换个cookie并随机切换浏览器
                if page % 30 == 0:

                    ua = random.choice(agents)
                    self.headers = {'User-Agent': ua}

                    num = page / 30

                    choice = int(num % len(cookies))
                    self.cookie = cookies[choice]
                    print("Cookie已切换为第%s个" % (choice + 1))

                print("正在爬取第%s/%s页微博" % (page, page_num))

                url2 = "https://weibo.cn/u/%d?filter=%d&page=%d" % (
                    self.user_id, self.filter, page)
                html2 = requests.get(url2, cookies=self.cookie, headers=self.headers).content
                selector2 = etree.HTML(html2)
                info = selector2.xpath("//div[@class='c']")
                id_info = selector2.xpath("//div/@id")
                if len(info) > 3:
                    for i in range(0, len(info) - 2):

                        # 微博ID，为后面爬取某一条微博的评论做准备
                        weibo_id = str(id_info[i])[2:]

                        # 微博内容
                        str_t = info[i].xpath("div/span[@class='ctt']")
                        weibo_content = str_t[0].xpath("string(.)").encode(
                            sys.stdout.encoding, "ignore").decode(
                            sys.stdout.encoding)
                        # self.weibo_content.append(weibo_content)
                        # print (u"微博内容：" + weibo_content)

                        # 微博发布时间及设备
                        str_info = info[i].xpath("div/span[@class='ct']")
                        str_info = str_info[0].xpath("string(.)").encode(
                            sys.stdout.encoding, "ignore").decode(
                            sys.stdout.encoding)

                        # 微博发布设备
                        try:
                            publish_device = str_info.split(u'来自')[1]
                        except Exception as e:
                            # print("第%s条微博发布设备Error: %s" % (self.weibo_num2, e))
                            publish_device = 'null'
                        # self.publish_device.append(publish_device)

                        # 微博发布时间
                        publish_time = str_info.split(u'来自')[0]
                        if u"刚刚" in publish_time:
                            publish_time = datetime.now().strftime(
                                '%Y-%m-%d %H:%M')
                        elif u"分钟" in publish_time:
                            minute = publish_time[:publish_time.find(u"分钟")]
                            minute = timedelta(minutes=int(minute))
                            publish_time = (
                                datetime.now() - minute).strftime(
                                "%Y-%m-%d %H:%M")
                        elif u"今天" in publish_time:
                            today = datetime.now().strftime("%Y-%m-%d")
                            time = publish_time[3:]
                            publish_time = today + " " + time
                        elif u"月" in publish_time:
                            year = datetime.now().strftime("%Y")
                            month = publish_time[0:2]
                            day = publish_time[3:5]
                            time = publish_time[7:12]
                            publish_time = (
                                year + "-" + month + "-" + day + " " + time)
                        else:
                            publish_time = publish_time[:16]
                        # self.publish_time.append(publish_time)

                        # 点赞数
                        str_zan = info[i].xpath("div/a/text()")[-4]
                        guid = re.findall(pattern, str_zan, re.M)
                        try:
                            up_num = int(guid[0])
                        except Exception as e:
                            print("第%s条微博点赞数Error: %s" % (self.weibo_num2, e))
                            up_num = 0
                        # self.up_num.append(up_num)

                        # 转发数
                        try:
                            retweet = info[i].xpath("div/a/text()")[-3]
                            guid = re.findall(pattern, retweet, re.M)
                            retweet_num = int(guid[0])
                        except Exception as e:
                            print("第%s条微博转发数Error: %s" % (self.weibo_num2, e))
                            retweet_num = 0
                        # self.retweet_num.append(retweet_num)

                        # 评论数
                        comment = info[i].xpath("div/a/text()")[-2]
                        guid = re.findall(pattern, comment, re.M)
                        try:
                            comment_num = int(guid[0])
                        except Exception as e:
                            print("第%s条微博评论数Error: %s" % (self.weibo_num2, e))
                            comment_num = 0
                        # self.comment_num.append(comment_num)

                        # 保存微博信息
                        data = {
                            '微博ID': weibo_id,
                            '内容': weibo_content,
                            '发布时间': publish_time,
                            '发布设备': publish_device,
                            '点赞数': up_num,
                            '转发数': retweet_num,
                            '评论数': comment_num
                        }

                        self.WeiboData.insert_one(data)

                        self.weibo_num2 += 1

                systime.sleep(0.2 + float(random.randint(1, 5)) / 20)
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    # 对数据库里的信息进行去重
    def remove_same(self):
        print("正在去重，请稍后")
        id_set = set()
        for weibo in self.WeiboData.find({})[1::]:
            if weibo["微博ID"] in id_set:
                self.WeiboData.remove(weibo)
            else:
                id_set.add(weibo["微博ID"])
        print("去重完毕")

    # 自动获取该用户所有信息
    def auto_get(self):
        try:
            if self.start_page == 1:
                self.get_username()
                self.get_user_info()
                self.save_user_info()
            self.get_save_weibo()
            self.remove_same()
            print(u"该用户所有信息抓取完毕")
        except Exception as e:
            print("Error: ", e)
