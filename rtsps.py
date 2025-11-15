from multiprocessing import Pool,Value,Manager
import cv2,os,json,time,requests,codecs,sys,redis,multiprocessing
from func_timeout import func_set_timeout


def get_config():
    config = json.loads(open("C:\\jiankong\\rtsp.json", encoding='utf-8').read())  #读取配置文件
    return config

rtsp_config = get_config()
path1 = ("C:\\jiankong\\")
nowtime = time.strftime("%Y%m%d", time.localtime())
try:
    os.mkdir(path1 + "\\" + nowtime)
    print("创建当日目录")
except:
    print("当日目录已存在")
nowdir = (path1 + "\\" + nowtime)
rtsp_config = get_config()
readredis = redis.Redis(connection_pool=redis.ConnectionPool(host="IP地址", port="端口", password="密码",decode_responses=True)) #redis连接信息

#企业微信机器人
def post_weixin(stats):
    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=用你自己的'
    body = {
        "msgtype": "news",
        "news": {
            "articles": [
                {
                    "title": "监控摄像头自动巡检多进程版",
                    "description": stats,
                    "url": "90apt.com",
                    "picurl": "https://www.hikvision.com/content/dam/hikvision/cn/product/network-camera/fixed-ipc/%E7%BB%8F%E9%94%80%E7%B3%BB%E5%88%97/%E7%BB%8F%E9%94%80%E7%B3%BB%E5%88%97%E5%AF%BC%E8%88%AA%E7%9B%AE%E5%BD%95.jpg"
                }
            ]
        }}
    response = requests.post(url, json=body)
    print(response.text)
    print(response.status_code)


@func_set_timeout(5)  #连接失败超时时间5秒
def linkvideo(link):
    video = cv2.VideoCapture(link)
    return video

def dayin(rtspconfig):
    video1 = "rtsp://" + rtspconfig['name'] + ":" + rtspconfig['password'] + "@" + rtspconfig['ip'] + rtsp_config[rtspconfig['brand']]  #拼接rtsp参数
    try:
        cap = linkvideo(video1)
        i = 0
        for i in range(5):
            i = i + 1
            ret, frame = cap.read()
            if ret == False:  # 若没有帧返回，则重新刷新rtsp视频流
                print("重新获取图像")
                print(i)
                if i == 5:
                    readredis.set(rtspconfig['ip'], "fail")
                    print("重新连接5次失败")
            else:
                cv2.imwrite(nowdir + "\\" + rtspconfig['ip'] + ".jpeg", frame)  #保存图像
                print("图像保存成功")
                readredis.set(rtspconfig['ip'], "success")
                cap.release()  #关闭摄像头
                break

    except:
        print("连接失败，网络或用户名密码错误")
        readredis.set(rtspconfig['ip'], "fail")


if __name__ == '__main__':
    total = 0
    fail = 0
    weixindata = ""
    readredis.flushall()
    print("初始化redis数据库")
    multiprocessing.freeze_support() #防止windows无限创建进程
    with Pool(8) as p:  #8进程
        p.map(dayin, rtsp_config["rtsp"])
    for key in rtsp_config["rtsp"]:
        if readredis.get(key["ip"]) == "fail":
            weixindata = weixindata + (key["ip"]+" 网络或账号密码错误\n")
            fail = fail + 1
        total = total + 1
    weixinpost = "总计巡检:"+str(total)+"台"+"，故障摄像头："+str(fail)+"台\n"+weixindata
    post_weixin(weixinpost)
    flog = codecs.open(nowdir + "\\" + nowtime + ".log", 'w', encoding='utf-8')
    flog.write(weixinpost)
    flog.close()
    print("程序执行完成")
