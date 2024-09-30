import os
import re
import sys
import json
import time
import signal
import requests
import tldextract
from datetime import datetime
from collections import Counter
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential

#获取项目路径
Project = os.path.realpath(sys.argv[0])
MainPath = os.path.dirname(Project)
MainName = os.path.basename(Project)

#获取启动参数
try:
    RunningInput = sys.argv[1]
    RunningInput = RunningInput.replace('-','')
except:
    RunningInput = ('None')

#[参数说明]
HelpData = ('''
[使用方法]
1：注册阿里云并获取账号AccessKeyID和AccessKeySecret
2：运行程序，首次运行会自动生成配置文件
3：将AccessKeyID和AccessKeySecret填入配置文件
4：将需要动态解析的域名填入配置文件
5：再次运行程序


[配置说明]
RegionID：阿里云地区设置 (默认:cn-hangzhou)
AccessKeyID：主账号或RAM账号AccessKeyID
AccessKeySecret：主账号或RAM账号AccessKeySecret
UpdateDelay：更新间隔 (默认:500)
print：是否(将输出内容)保存日志 (默认:True)

IPv6Prefix：公网IPv6地址开头，可以确保获取到公网IPv6而不是局域网IPv6 (默认:Auto)
IPv4_API_x：查询本机公网IPv4地址的API接口，不懂不建议更改

IPv4_List：用于IPv4动态解析的域名列表
IPv6_List：用于IPv6动态解析的域名列表


[运行参数]
-once   仅更新一次，更新完成立即退出程序
-config 重置/生成配置文件
-help   获取帮助


[作者信息]
程序作者：ZZYDD
作者主页：https://space.bilibili.com/543085311
项目地址：https://github.com/zzydd/SimpleDDNS-Aliyun
''')

#运行模式
MainMode = True
OnceMode = False


#【获取时间】
def DatetimeNow():
    #获取时间
    now = datetime.now()
    #格式化
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")    
    return formatted_time
def DateNow():
    #获取时间
    now = datetime.now()
    #格式化
    formatted_date = now.strftime("%Y-%m-%d")    
    return formatted_date


#【写日志】
def WriteLogMain(LogData):
    pass


#手动退出程序
def ControlC_Exit(sig, frame):
    global MainMode
    print('[主程序]-收到Control+C，准备退出')
    print('[主程序]-退出')
    MainMode = False
    #sys.exit(0)

#系统关机信号
def Shutdown_Exit(sig, frame):
    global MainMode
    print('[主程序]-检测到系统关闭，准备退出')
    print('[主程序]-退出')
    MainMode = False
    #sys.exit(0)

#信号处理器
signal.signal(signal.SIGINT, ControlC_Exit)
signal.signal(signal.SIGTERM, Shutdown_Exit)


#配置文件模板
ConfigFile=('''{
  "RegionID":"cn-hangzhou",
  "AccessKeyID": "FILL YOUR AccessKeyID",
  "AccessKeySecret": "FILL YOUR AccessKeySecret",
  "UpdateDelay":500,
  "WriteLog":true,
  
  "IPv6Prefix":"Auto",
  "IPv4_API_1":"https://4.ipw.cn",
  "IPv4_API_2":"https://myip.ipip.net",
  "IPv4_API_3":"https://ipv4.icanhazip.com",
  "IPv4_API_4":"https://www.ipplus360.com/getIP",
  "IPv4_API_5":"https://ip.cn/api/index?ip=&type=0",
  
  "IPv4_List": [
    "example.com",
    "ipv4.example.com"
  ],
  
  "IPv6_List": [
    "ddns.example.com",
    "ipv6.example.com"
  ]
}
''')


#【特殊运行模式判断】

#仅运行一次
if RunningInput=='once':
    OnceMode = True

#重置配置文件
elif RunningInput=='config':
    MainMode = False
    print(f'[{DatetimeNow()}] [信息] 重置配置文件模式')
    with open(MainPath+"/config.json","w",encoding="utf-8") as file:
        file.write(ConfigFile)
    print(f'[{DatetimeNow()}] [信息] 配置文件已重置')
    print(f'[{DatetimeNow()}] [信息] 程序将在5秒后关闭')
    time.sleep(5)
    sys.exit(1)

#显示帮助
elif RunningInput in ['help','/help','?','/?']:
    print('')
    print(f'[{DatetimeNow()}] [信息] 显示帮助')
    print(HelpData)
    print(f'[{DatetimeNow()}] [信息] 程序将在5秒后关闭')
    time.sleep(5)
    sys.exit(1)


#【读取配置文件】
print('')
print(f'[{DatetimeNow()}] [信息] 程序运行')
print(f'[{DatetimeNow()}] [信息] 正在读取配置')
try:
    #读取配置文件
    with open(MainPath+'/config.json', 'r', encoding='utf-8') as file:
        config = json.load(file)

    #读取配置
    RegionID = config['RegionID']
    AccessKeyID = config['AccessKeyID']
    AccessKeySecret = config['AccessKeySecret']
    UpdateDelayTimes = config['UpdateDelay']
    WriteLogSet = config['WriteLog']
    IPv6Prefix = config['IPv6Prefix']
    IPv4_API_1 = config['IPv4_API_1']
    IPv4_API_2 = config['IPv4_API_2']
    IPv4_API_3 = config['IPv4_API_3']
    IPv4_API_4 = config['IPv4_API_4']
    IPv4_API_5 = config['IPv4_API_5']
    IPv4_List = config['IPv4_List']
    IPv6_List = config['IPv6_List']
    print(f'[{DatetimeNow()}] [信息] 配置文件读取完成')

except FileNotFoundError:
    with open(MainPath+"/config.json","w",encoding="utf-8") as file:
        file.write(ConfigFile)
    print(f'[{DatetimeNow()}] [警告] 配置文件未创建')
    print(f'[{DatetimeNow()}] [警告] 已创建配置文件，请先编辑')
    print(f'[{DatetimeNow()}] [警告] 程序将在5秒后关闭')
    time.sleep(5)
    sys.exit(1)

except json.JSONDecodeError as ErrorMsg:
    print(f'[{DatetimeNow()}] [错误] 配置文件格式错误！')
    print(f'[{DatetimeNow()}] [错误] 配置文件错误提示: {ErrorMsg}')
    print(f'[{DatetimeNow()}] [警告] 程序将在5秒后关闭')
    time.sleep(5)
    sys.exit(1)

except Exception as ErrorMsg:
    print(f'[{DatetimeNow()}] [错误] 发生未知错误: {ErrorMsg}')
    print(f'[{DatetimeNow()}] [警告] 程序将在5秒后关闭')
    time.sleep(5)
    sys.exit(1)





# 创建AcsClient对象
client = AcsClient(credential=AccessKeyCredential(AccessKeyID, AccessKeySecret), region_id=RegionID)
print(f'[{DatetimeNow()}] [信息] AcsClient对象创建成功')

print('')
print(f'[{DatetimeNow()}] [信息] 程序初始化完毕！'+'='*50)


#【切割域名 [主域名,子域名]】
def ExtractDomain(domain):
    try:
        #切割
        extracted = tldextract.extract(domain)
        #主域名
        main_domain = (f"{extracted.domain}.{extracted.suffix}")
        #子域名
        subdomain = extracted.subdomain
        if subdomain=='':
            subdomain = '@'
        #返回
        print(f'[{DatetimeNow()}] [信息] 域名识别成功')
        return main_domain, subdomain
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [错误] 域名识别错误！')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        return 'error','example.com'


#【获取DNS记录 [ID,值] 】(主域名，子域名)
def GetRecordInfo(domain_main, sub_domain,record_type):
    #发送请求
    try:
        request = DescribeDomainRecordsRequest()
        request.set_DomainName(domain_main)
        request.set_Type(record_type)
        response = client.do_action_with_exception(request)
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [错误] 获取DNS记录失败！')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        #解析错误
        if "InvalidAccessKeyId" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】AccessKeyID无效！请检查AccessKeyID！')
        elif "InvalidAccessKeySecret" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】AccessKeySecret无效！请检查AccessKeySecret！')
        elif "Forbidden" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】拒绝访问！请检查账号权限！')
        elif "DomainRecordNotBelongToUser" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】拒绝更新！请检查账号权限！')
        return None,None
    
    try:
        #解析返回的JSON
        records = json.loads(response.decode('utf-8'))['DomainRecords']['Record']
        
        #查找匹配的记录
        for record in records:
            if record['RR'] == sub_domain:
                #返回数据
                print(f'[{DatetimeNow()}] [信息] DNS记录获取成功')
                return record['RecordId'],record['Value']
            else:
                pass
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [错误] DNS记录解析失败！')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        pass
    print(f'[{DatetimeNow()}] [错误] 未找到相关DNS记录！')
    return None,None


#【更新DNS记录】(记录ID，子域名，记录类型，记录值)
def UpdateDNS(record_id, sub_domain, record_type, record_value):
    #发送请求
    try:
        request = UpdateDomainRecordRequest()
        request.set_RecordId(record_id)
        request.set_RR(sub_domain)
        request.set_Type(record_type)
        request.set_Value(record_value)
        #返回结果
        response = client.do_action_with_exception(request)
        response = response.decode('utf-8')
        print(f'[{DatetimeNow()}] [信息] DNS记录更新成功')
        return response
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [错误] DNS记录更新失败！')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        #解析错误
        if "InvalidAccessKeyId" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】AccessKeyID无效！请检查AccessKeyID！')
        elif "InvalidAccessKeySecret" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】AccessKeySecret无效！请检查AccessKeySecret！')
        elif "Forbidden" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】拒绝访问！请检查账号权限！')
        elif "DomainRecordNotBelongToUser" in str(ErrorMsg):
            print(f'[{DatetimeNow()}] [错误] 【错误提示】拒绝更新！请检查账号权限！')
        
        return False



#【获取IPv4】
def GetIPv4():

    #创建列表
    IPv4_List = []
    print(f'[{DatetimeNow()}] [信息] 正在获取公网IPv4')

    #请求接口1
    try:
        Response1 = requests.get(IPv4_API_1)#接口1
        IPv4_1 = re.findall(r'\d+.\d+.\d+.\d+',Response1.text)
        IPv4_List.extend(IPv4_1)
        print(f'[{DatetimeNow()}] [信息] 公网IPv4获取接口1：{IPv4_1}')
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取接口1：获取失败')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv4_1 = ('127.0.0.1')

    #请求接口2
    try:
        Response2 = requests.get(IPv4_API_2)#接口2
        IPv4_2 = re.findall(r'\d+.\d+.\d+.\d+',Response2.text)
        IPv4_List.extend(IPv4_2)
        print(f'[{DatetimeNow()}] [信息] 公网IPv4获取接口2：{IPv4_2}')
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取接口2：获取失败')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv4_2 = ('127.0.0.1')

    #请求接口3
    try:
        Response3 = requests.get(IPv4_API_3)#接口3
        IPv4_3 = re.findall(r'\d+.\d+.\d+.\d+',Response3.text)
        IPv4_List.extend(IPv4_3)
        print(f'[{DatetimeNow()}] [信息] 公网IPv4获取接口3：{IPv4_3}')
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取接口3：获取失败')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv4_3 = ('127.0.0.1')

    #请求接口4
    try:
        Response4 = requests.get(IPv4_API_4)#接口4
        IPv4_4 = re.findall(r'\d+.\d+.\d+.\d+',Response4.text)
        IPv4_List.extend(IPv4_4)
        print(f'[{DatetimeNow()}] [信息] 公网IPv4获取接口4：{IPv4_4}')
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取接口4：获取失败')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv4_4 = ('127.0.0.1')

    #请求接口5
    try:
        Response5 = requests.get(IPv4_API_5)#接口5
        IPv4_5 = re.findall(r'\d+.\d+.\d+.\d+',Response5.text)
        IPv4_List.extend(IPv4_5)
        print(f'[{DatetimeNow()}] [信息] 公网IPv4获取接口5：{IPv4_5}')
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取接口5：获取失败')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv4_5 = ('127.0.0.1')

    #统计结果
    try:
        ip_count = Counter(IPv4_List)
        IPv4 = ip_count.most_common(1)[0][0] #获取出现次数最多的IP
        print(f'[{DatetimeNow()}] [信息] 公网IPv4获取结果：{IPv4}')
    except IndexError:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取失败')
        IPv4 = ('127.0.0.1')
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv4获取出错')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv4 = ('127.0.0.1')

    #返回结果
    return(IPv4)
        


#【获取IPv6】
def GetIPv6():
    try:
        #执行命令
        ReturnText = os.popen('ipconfig /all').read()

        #获取数据
        if IPv6Prefix=='Auto':
            print(f'[{DatetimeNow()}] [警告] 未设置IPv6开头，可能会误获取到局域网IPv6')
            Format = (r'(([a-f0-9]{1,4}:){7}[a-f0-9]{1,4})') #IPv6地址格式
        else:
            print(f'[{DatetimeNow()}] [信息] 已设置IPv6开头：[{IPv6Prefix}:]')
            Format = (r'(('+str(IPv6Prefix)+'[a-f0-9]{0,3}(:[a-f0-9]{1,4}){0,7}))') #特殊格式IPv6
        Match = re.search(Format, ReturnText)

        #处理数据
        if Match:
            print(f'[{DatetimeNow()}] [信息] 公网IPv6获取成功！')
            IPv6 = Match.group()
        else:
            print(f'[{DatetimeNow()}] [警告] 公网IPv6获取失败！')
            IPv6 = ('fe80::')

        #返回数据
        print(f'[{DatetimeNow()}] [信息] 公网IPv6获取结果：{IPv6}')
        return IPv6
    
    except Exception as ErrorMsg:
        print(f'[{DatetimeNow()}] [警告] 公网IPv6获取出错')
        print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
        IPv6 = ('fe80::')
        return IPv6








#【主程序】

while MainMode:

    try:

        print('')
        print(f'[{DatetimeNow()}] [信息] 开始更新！')

        #获取当前IPv4
        print(f'[{DatetimeNow()}] [信息] 获取本机公网IPv4')
        NewIPv4 = GetIPv4()

        #获取当前IPv6
        print(f'[{DatetimeNow()}] [信息] 获取本机公网IPv6')
        NewIPv6 = GetIPv6()
        print('')
        print(f'[{DatetimeNow()}] [信息] 当前IPv4：{NewIPv4}')
        print(f'[{DatetimeNow()}] [信息] 当前IPv6：{NewIPv6}')
        print('')


        #[更新IPv4]
        for IPv4 in IPv4_List:
            print('')
            print(f'[{DatetimeNow()}] [信息] 更新IPv4域名：{IPv4}')

            #切割域名
            main_domain,sub_domain = ExtractDomain(IPv4)

            #获取DNS记录信息 (记录ID,记录值)
            record_id, record_value = GetRecordInfo(main_domain,sub_domain, "A")
            print(f'[{DatetimeNow()}] [信息] 当前记录值：{record_value}')

            #判断记录
            if record_value==NewIPv4:
                print(f'[{DatetimeNow()}] [信息] 记录值相同，无需更新')
            elif NewIPv4=='127.0.0.1':
                print(f'[{DatetimeNow()}] [警告] 无效IPv4，更新取消')
            else:
                #更新记录
                print(f'[{DatetimeNow()}] [信息] 更新记录值：【{record_value}】>>>【{NewIPv4}】')
                UpdateDNS(record_id, sub_domain, "A", NewIPv4)
                print(f'[{DatetimeNow()}] [信息] 更新成功')


        #[更新IPv6]
        for IPv6 in IPv6_List:
            print('')
            print(f'[{DatetimeNow()}] [信息] 更新IPv6域名：{IPv6}')

            #切割域名
            main_domain,sub_domain = ExtractDomain(IPv6)

            #获取DNS记录信息 (记录ID,记录值)
            record_id, record_value = GetRecordInfo(main_domain,sub_domain, "AAAA")
            print(f'[{DatetimeNow()}] [信息] 当前记录值：{record_value}')

            #判断记录
            if record_value==NewIPv6:
                print(f'[{DatetimeNow()}] [信息] 记录值相同，无需更新')
            elif NewIPv6=='fe80::':
                print(f'[{DatetimeNow()}] [警告] 无效IPv6，更新取消')
            else:
                #更新记录
                print(f'[{DatetimeNow()}] [信息] 更新记录值：【{record_value}】>>>【{NewIPv6}】')
                UpdateDNS(record_id, sub_domain, "AAAA", NewIPv6)
                print(f'[{DatetimeNow()}] [信息] 更新成功')


        #仅一次模式
        if OnceMode:
            print(f'[{DatetimeNow()}] [信息] 当前为单次更新模式！')
            print(f'[{DatetimeNow()}] [信息] 程序将在5秒后退出！')
            time.sleep(5)
            break
            

        #更新间隔
        print('')
        try:
            UpdateDelay = int(UpdateDelayTimes)
            print(f'[{DatetimeNow()}] [信息] 程序将在{UpdateDelayTimes}秒后再次检查更新')
        except ValueError:
            print(f'[{DatetimeNow()}] [错误] 更新间隔参数错误！')
            print(f'[{DatetimeNow()}] [警告] 已使用默认间隔500秒')
            UpdateDelay = 500
        except Exception as ErrorMsg:
            print(f'[{DatetimeNow()}] [错误] 更新间隔设置异常！')
            print(f'[{DatetimeNow()}] [错误] {ErrorMsg}')
            print(f'[{DatetimeNow()}] [警告] 已使用默认间隔500秒')
            UpdateDelay = 500

        print('')
        print(f'[{DatetimeNow()}] [信息] 更新完毕！程序挂起！'+'='*50)
        print('')
        

        #延时
        try:
            for i in range(UpdateDelayTimes):
                time.sleep(1)
                if not MainMode:
                    break
        except:
            for i in range(500):
                time.sleep(1)
                if not MainMode:
                    break
            
    #退出
    except:
        print('[主程序]-收到Control+C，准备退出')
        print('[主程序]-退出')
        MainMode = False
        break


#关闭程序
sys.exit(0)





















