from Weibo import Weibo
import time
import random
import traceback
import pymongo
import os

def save_as_txt(db, dataPath):
    """将数据库里的东西保存为文本"""
    with open(dataPath, 'w', encoding='utf-8') as f:
        for i in db.find({})[1::]:
            f.write(i["微博ID"] + '\t' + i["发布时间"] + '\n')

def getID(user_id, idPath):
    """获取微博ID"""
    dbClient = pymongo.MongoClient(host='localhost', port=27017)

    WeiboData = dbClient["Weibo"]
    WeiboID = WeiboData[str(user_id)]

    save_as_txt(WeiboID, idPath)


def main():
    user_id = 1980768563     # 可以改成任意合法的用户id（爬虫的微博id除外）

    # 读取微博的所有ID信息，如果ID.txt不存在，则自动创建
    startPath = "teiboID/"
    idPath = startPath + str(user_id) + '_id.txt'
    if not os.path.exists(idPath):
        print("ID文件不存在，将自动创建")
        if not os.path.exists(startPath):
            os.makedirs(startPath)
        getID(user_id, idPath)

    file = open(idPath, 'r')
    lines = file.readlines()

    last_start = 225      # 记录上一次爬到哪里，继续爬的话只需要将start改为last_start的值即可
    start = 0       # 开始爬取的微博位置，0代表从第一条开始爬取
    end = 1         # 结束的微博位置，比start大1就代表只爬一条，如果要爬取全部微博只要改为len（lines）即可
    for i in range(start, end):
        if (end - start) == 1:
            print("正在爬取第%s条微博" % (i+1))
        else:
            print("正在爬取第%d/%d条微博" % (i+1, end+1))
        line = lines[i].strip('\n')
        weibo_id, publish_time = line[:9], line[10:27]
        # print(weibo_id, publish_time)
        part = 20       # 分组的标号，1代表第一个分组，长度为默认分组大小
        part_length = 1600      # 分组大小，每分组标号每增加1，实际的页码就增加分组大小
        try:
            # start_page = 119787
            start_page = 109000 + part_length * ((part-13)-1)
            end_page = 109000 + part_length * (part-13)
            Comment = Weibo(user_id, weibo_id, publish_time, start_page, end_page, part, part_length)
            Comment.auto_get()
        except Exception as e:
            print("Cookie 出故障，请更新cookie")
            print("Error: ", e)
            traceback.print_exc()
        # 每一条微博加个3s的延迟
        time.sleep(3 + float(random.randint(1, 10)) / 20)

if __name__ == "__main__":
    main()
