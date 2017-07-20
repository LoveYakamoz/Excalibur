#!/usr/bin/env python
# coding: utf-8
import codecs
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import requests
import xml.dom.minidom
import json
import time
import re
import sys
import os
import subprocess
import random
import multiprocessing
import platform
import logging
import http.client
from collections import defaultdict
import logging.handlers

LOG_FILE = 'webchat.log'

# 实例化handler
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 4*1024*1024, backupCount = 5)
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)
handler.setFormatter(formatter)

logger = logging.getLogger('Robot')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def catchKeyboardInterrupt(fn):
    def wrapper(*args):
        try:
            return fn(*args)
        except KeyboardInterrupt:
            print('\n[*] Force Quit')

    return wrapper


def SaveContact(ContactList, GroupList):
    filepath = r"./Contact_List.txt"
    try:
        fp = open(filepath, 'w+', encoding='UTF-8')
        for contact in ContactList:
            fp.write('NickName: %s, RemarkName: %s, City: %s, Signature: %s, UserName: %s \n' % (
                contact['NickName'], contact['RemarkName'], contact['City'], contact['Signature'], contact['UserName']))

        fp.write("==============================================================================\n")

        for group in GroupList:
            fp.write('NickName: %s, RemarkName: %s, City: %s, Signature: %s, UserName: %s \n' % (
                group['NickName'], group['RemarkName'], group['City'], group['Signature'], group['UserName']))
    finally:
        if fp:
            fp.close()


class WebWeixin(object):
    def __str__(self):
        description = \
            "=========================\n" + \
            "[#] Web Weixin\n" + \
            "[#] Debug Mode: " + str(self.DEBUG) + "\n" + \
            "[#] Uuid: " + self.uuid + "\n" + \
            "[#] Uin: " + str(self.uin) + "\n" + \
            "[#] Sid: " + self.sid + "\n" + \
            "[#] Skey: " + self.skey + "\n" + \
            "[#] DeviceId: " + self.deviceId + "\n" + \
            "[#] PassTicket: " + self.pass_ticket + "\n" + \
            "[#] NickName: " + self.User['NickName'] + "\n" + \
            "========================="
        return description

    def __init__(self):
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = ''
        self.redirect_uri = ''
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.deviceId = 'e' + repr(random.random())[2:17]
        self.BaseRequest = {}
        self.synckey = ''
        self.SyncKey = []
        self.User = []
        self.MemberList = []
        self.ContactList = []
        self.GroupList = []
        self.GroupMemeberList = []
        self.PublicUsersList = []
        self.SpecialUsersList = []

        self.NotifyPersionList_1 = []
        self.NotifyPersionList_2 = []
        self.KeyWords_1 = []
        self.KeyWords_2 = []
        self.ListenGroupList = []

        self.autoReplyMode = False
        self.syncHost = ''
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36'
        self.interactive = False
        self.autoOpen = False
        self.saveFolder = os.path.join(os.getcwd(), 'saved')
        self.saveSubFolders = {'webwxgeticon': 'icons', 'webwxgetheadimg': 'headimgs', 'webwxgetmsgimg': 'msgimgs',
                               'webwxgetvideo': 'videos', 'webwxgetvoice': 'voices', '_showQRCodeImg': 'qrcodes'}
        self.appid = 'wx782c26e4c19acffb'
        self.lang = 'zh_CN'
        self.lastCheckTs = time.time()
        self.memberCount = 0
        self.SpecialUsers = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'fmessage', 'tmessage', 'qmessage',
                             'qqsync', 'floatbottle', 'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp',
                             'blogapp', 'facebookapp', 'masssendapp', 'meishiapp', 'feedsapp',
                             'voip', 'blogappweixin', 'weixin', 'brandsessionholder', 'weixinreminder',
                             'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'officialaccounts', 'notification_messages',
                             'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm',
                             'notification_messages']
        self.TimeOut = 20
        self.media_count = -1

        self.cookie = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie))
        opener.addheaders = [('User-agent', self.user_agent)]
        urllib.request.install_opener(opener)

    def changeToNonbomFile(self, filepath):
        try:
            fp = open(filepath, 'rb')
            content = fp.read()
            if content[:3] == codecs.BOM_UTF8:
                content = content[3:]
                fp.close()
                fp = open(filepath, 'wb')
                fp.write(content)
                fp.close
            else:
                return
        finally:
            if fp:
                fp.close()

    def getNotifyPersonFromFile(self):
        self.changeToNonbomFile(r"./Notify_Person_1.txt")
        self.changeToNonbomFile(r"./Notify_Person_2.txt")
        try:
            fp = open(r"./Notify_Person_1.txt", mode='r', encoding='UTF-8')
            lines = fp.readlines()
            for line in lines:
                self.NotifyPersionList_1.append(line.strip())

            #logger.info("Notify_Person_1: ", self.NotifyPersionList_1)
        finally:
            if fp:
                fp.close()
        try:
            fp = open(r"./Notify_Person_2.txt", mode='r', encoding='UTF-8')
            lines = fp.readlines()
            for line in lines:
                self.NotifyPersionList_2.append(line.strip())
            #logger.info("Notify_Person_2: ", self.NotifyPersionList_2)
        finally:
            if fp:
                fp.close()

    def getKeyWordsFromFile(self):
        self.changeToNonbomFile(r"./Key_Words_1.txt")
        self.changeToNonbomFile(r"./Key_Words_2.txt")
        try:
            fp = open(r"./Key_Words_1.txt", mode='r', encoding='UTF-8')
            lines = fp.readlines()
            for line in lines:
                self.KeyWords_1.append(line.strip())
            #logger.info("KeyWords_1: ", self.KeyWords_1)
        finally:
            if fp:
                fp.close()
        try:
            fp = open(r"./Key_Words_2.txt", mode='r', encoding='UTF-8')
            lines = fp.readlines()
            for line in lines:
                self.KeyWords_2.append(line.strip())
            #logger.info("KeyWords_2: ", self.KeyWords_2)
        finally:
            if fp:
                fp.close()

    def getListenGroupFromFile(self):
        for group in self.GroupList:
            self.ListenGroupList.append(group)

    def getUUID(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': self.appid,
            'fun': 'new',
            'lang': self.lang,
            '_': int(time.time()),
        }
        data = self._post(url, params, False).decode("utf-8")
        if data == '':
            return False
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            self.uuid = pm.group(2)
            return code == '200'
        return False

    def genQRCode(self):
        if sys.platform.startswith('win'):
            self._showQRCodeImg('win')
        elif sys.platform.find('darwin') >= 0:
            self._showQRCodeImg('macos')
        else:
            pass

    def _showQRCodeImg(self, str):
        url = 'https://login.weixin.qq.com/qrcode/' + self.uuid
        params = {
            't': 'webwx',
            '_': int(time.time())
        }

        data = self._post(url, params, False)
        if data == '':
            return
        QRCODE_PATH = self._saveFile('qrcode.jpg', data, '_showQRCodeImg')
        if str == 'win':
            os.startfile(QRCODE_PATH)
        elif str == 'macos':
            subprocess.call(["open", QRCODE_PATH])
        else:
            pass
            return

    def waitForLogin(self, tip=1):
        time.sleep(tip)
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (
            tip, self.uuid, int(time.time()))
        data = self._get(url)
        if data == '':
            return False
        pm = re.search(r"window.code=(\d+);", data)
        code = pm.group(1)

        if code == '201':
            return True
        elif code == '200':
            pm = re.search(r'window.redirect_uri="(\S+?)";', data)
            r_uri = pm.group(1) + '&fun=new'
            self.redirect_uri = r_uri
            self.base_uri = r_uri[:r_uri.rfind('/')]
            return True
        elif code == '408':
            self._echo('[login timeout] \n')
        else:
            self._echo('[login abnormal] \n')
        return False

    def login(self):
        data = self._get(self.redirect_uri)
        if data == '':
            return False
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.BaseRequest = {
            'Uin': int(self.uin),
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.deviceId,
        }
        return True

    def webwxinit(self):
        url = self.base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        params = {
            'BaseRequest': self.BaseRequest
        }
        dic = self._post(url, params)
        if dic == '':
            return False
        self.SyncKey = dic['SyncKey']
        self.User = dic['User']
        # synckey for synccheck
        self.synckey = '|'.join(
                [str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.SyncKey['List']])

        return dic['BaseResponse']['Ret'] == 0

    def webwxstatusnotify(self):
        url = self.base_uri + \
              '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % (self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Code": 3,
            "FromUserName": self.User['UserName'],
            "ToUserName": self.User['UserName'],
            "ClientMsgId": int(time.time())
        }
        dic = self._post(url, params)
        if dic == '':
            return False

        return dic['BaseResponse']['Ret'] == 0

    def webwxgetcontact(self):
        SpecialUsers = self.SpecialUsers
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        dic = self._post(url, {})
        if dic == '':
            return False

        self.MemberCount = dic['MemberCount']
        self.MemberList = dic['MemberList']
        ContactList = self.MemberList[:]

        for i in range(len(ContactList) - 1, -1, -1):
            Contact = ContactList[i]
            if Contact['VerifyFlag'] & 8 != 0:  # public user
                ContactList.remove(Contact)
                self.PublicUsersList.append(Contact)
            elif Contact['UserName'] in SpecialUsers:  # special user
                ContactList.remove(Contact)
                self.SpecialUsersList.append(Contact)
            elif '@@' in Contact['UserName']:  # group user
                ContactList.remove(Contact)
                self.GroupList.append(Contact)
            elif Contact['UserName'] == self.User['UserName']:  # self
                ContactList.remove(Contact)

        self.ContactList = ContactList

        SaveContact(self.ContactList, self.GroupList)

        return True

    def webwxbatchgetcontact(self):
        url = self.base_uri + \
              '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                  int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": len(self.GroupList),
            "List": [{"UserName": g['UserName'], "EncryChatRoomId": ""} for g in self.GroupList]
        }
        dic = self._post(url, params)
        if dic == '':
            return False

        ContactList = dic['ContactList']
        self.GroupList = ContactList

        for i in range(len(ContactList) - 1, -1, -1):
            Contact = ContactList[i]
            MemberList = Contact['MemberList']
            for member in MemberList:
                self.GroupMemeberList.append(member)
        return True

    def getNameById(self, id):
        url = self.base_uri + \
              '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                  int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": 1,
            "List": [{"UserName": id, "EncryChatRoomId": ""}]
        }
        dic = self._post(url, params)
        if dic == '':
            return None

        return dic['ContactList']

    def get_valid_sync_channel(self):
        SyncHost = ['wx2.qq.com',
                    'webpush.wx2.qq.com',
                    'wx8.qq.com',
                    'webpush.wx8.qq.com',
                    'qq.com',
                    'webpush.wx.qq.com',
                    'web2.wechat.com',
                    'webpush.web2.wechat.com',
                    'wechat.com',
                    'webpush.web.wechat.com',
                    'webpush.weixin.qq.com',
                    'webpush.wechat.com',
                    'webpush1.wechat.com',
                    'webpush2.wechat.com',
                    'webpush.wx.qq.com',
                    'webpush2.wx.qq.com']
        for host in SyncHost:
            self.syncHost = host
            [retcode, selector] = self.synccheck()
            if retcode == '0':
                logger.info('sync channel is : %s' % (self.syncHost))
                return True
        logger.error('no valid channel for sync')
        return False

    def synccheck(self):
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.deviceId,
            'synckey': self.synckey,
            '_': int(time.time()),
        }
        url = 'https://' + self.syncHost + '/cgi-bin/mmwebwx-bin/synccheck?' + urllib.parse.urlencode(params)
        data = self._get(url)
        if data == '':
            return [-1, -1]

        pm = re.search(
                r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    def webwxsync(self):
        url = self.base_uri + \
              '/webwxsync?sid=%s&skey=%s&pass_ticket=%s' % (
                  self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'SyncKey': self.SyncKey,
            'rr': ~int(time.time())
        }
        dic = self._post(url, params)
        if dic == '':
            logger.error('请求失败: %s' % (url))
            return None
        if self.DEBUG:
            print(json.dumps(dic, indent=4))
            (json.dumps(dic, indent=4))

        if dic['BaseResponse']['Ret'] == 0:
            self.SyncKey = dic['SyncKey']
            self.synckey = '|'.join(
                    [str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.SyncKey['List']])
        return dic

    def webwxsendtextmsg(self, word, to='filehelper'):
        url = self.base_uri + \
              '/webwxsendmsg?pass_ticket=%s' % (self.pass_ticket)
        clientMsgId = str(int(time.time() * 1000)) + \
                      str(random.random())[:5].replace('.', '')
        params = {
            'BaseRequest': self.BaseRequest,
            'Msg': {
                "Type": 1,
                "Content": self._transcoding(word),
                "FromUserName": self.User['UserName'],
                "ToUserName": to,
                "LocalID": clientMsgId,
                "ClientMsgId": clientMsgId
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        r = requests.post(url, data=data, headers=headers)
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def _saveFile(self, filename, data, api=None):
        fn = filename
        if self.saveSubFolders[api]:
            dirName = os.path.join(self.saveFolder, self.saveSubFolders[api])
            if not os.path.exists(dirName):
                os.makedirs(dirName)
            fn = os.path.join(dirName, filename)
            logging.debug('Saved file: %s' % fn)
            with open(fn, 'wb') as f:
                f.write(data)
                f.close()
        return fn

    def webwxgeticon(self, id):
        url = self.base_uri + \
              '/webwxgeticon?username=%s&skey=%s' % (id, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'img_' + id + '.jpg'
        return self._saveFile(fn, data, 'webwxgeticon')

    def webwxgetheadimg(self, id):
        url = self.base_uri + \
              '/webwxgetheadimg?username=%s&skey=%s' % (id, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'img_' + id + '.jpg'
        return self._saveFile(fn, data, 'webwxgetheadimg')

    def webwxgetmsgimg(self, msgid):
        url = self.base_uri + \
              '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'img_' + msgid + '.jpg'
        return self._saveFile(fn, data, 'webwxgetmsgimg')

    def webwxgetvoice(self, msgid):
        url = self.base_uri + \
              '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'voice_' + msgid + '.mp3'
        return self._saveFile(fn, data, 'webwxgetvoice')

    def getGroupName(self, id):
        name = '未知群'
        for member in self.GroupList:
            if member['UserName'] == id:
                name = member['NickName']
        if name == '未知群':
            # not find in current groups
            GroupList = self.getNameById(id)
            for group in GroupList:
                self.GroupList.append(group)
                if group['UserName'] == id:
                    name = group['NickName']
                    MemberList = group['MemberList']
                    for member in MemberList:
                        self.GroupMemeberList.append(member)
        return name

    def getUserRemarkName(self, id):
        name = '未知群' if id[:2] == '@@' else 'stranger'
        if id == self.User['UserName']:
            return self.User['NickName']  # self

        if id[:2] == '@@':
            name = self.getGroupName(id)
        else:
            for member in self.SpecialUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            for member in self.PublicUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            for member in self.ContactList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            for member in self.GroupMemeberList:
                if member['UserName'] == id:
                    name = member['DisplayName'] if member[
                        'DisplayName'] else member['NickName']

        if name == '未知群' or name == 'stranger':
            logging.debug(id)
        return name

    def getUSerIDByRemarkName(self, name):
        idlist = []
        print("getUserIDByRemarkName or NickName", name)
        for member in self.ContactList:

            if name == member['RemarkName'] or name == member['NickName']:
                ret = member['UserName']
                print("FIND", ret)
                idlist.append(ret)
        for member in self.GroupList:
            print("remark name: %s, NickName: %s" % (member['RemarkName'], member['NickName']))
            if name == member['RemarkName'] or name == member['NickName']:
                ret = member['UserName']
                print("FIND", ret)
                idlist.append(ret)
        return idlist

    def _showMsg(self, message, card=''):

        srcName = None
        dstName = None
        groupName = None
        content = None

        msg = message

        if msg['raw_msg']:
            srcName = self.getUserRemarkName(msg['raw_msg']['FromUserName'])
            dstName = self.getUserRemarkName(msg['raw_msg']['ToUserName'])
            content = msg['raw_msg']['Content'].replace(
                    '&lt;', '<').replace('&gt;', '>')
            message_id = msg['raw_msg']['MsgId']

            if msg['raw_msg']['FromUserName'][:2] == '@@':
                # a message from group
                if ":<br/>" in content:
                    [people, content] = content.split(':<br/>', 1)
                    groupName = srcName
                    srcName = self.getUserRemarkName(people)
                    dstName = 'GROUP'
                else:
                    groupName = srcName
                    srcName = 'SYSTEM'

        if (groupName is not None):
            if (card == ''):
                logger.info('%s |%s| %s -> %s: %s' % (
                        message_id, groupName.strip(), srcName.strip(), dstName.strip(),
                        content.replace('<br/>', '\n')))
                self.notifyPerson(groupName.strip(), srcName.strip(), content.replace('<br/>', '\n'))
            else:
                content = "标题：" + r"<a href=" + card['url'] + ">" + card['title'] + "</a>" + "\n" + "摘要：" + card[
                        'description']
                logger.info('%s |%s| %s -> %s: %s' % (
                        message_id, groupName.strip(), srcName.strip(), dstName.strip(), content))
                self.notifyPerson(groupName.strip(), srcName.strip(), content)

    def _searchContent(self, key, content, fmat='attr'):
        if fmat == 'attr':
            pm = re.search(key + '\s?=\s?"([^"<]+)"', content)
            if pm:
                return pm.group(1)
        elif fmat == 'xml':
            pm = re.search('<{0}>([^<]+)</{0}>'.format(key), content)
            if not pm:
                pm = re.search(
                        '<{0}><\!\[CDATA\[(.*?)\]\]></{0}>'.format(key), content)
            if pm:
                return pm.group(1)
        return '未知'

    def handleMsg(self, r):
        for msg in r['AddMsgList']:
            logger.info('[*] a new message come... please check')

            msgType = msg['MsgType']
            name = self.getUserRemarkName(msg['FromUserName'])
            content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')

            if msgType == 1:
                raw_msg = {'raw_msg': msg}
                self._showMsg(raw_msg)
            elif msgType == 51:
                raw_msg = {'raw_msg': msg, 'message': '[*] Access to contact information Successfully'}
                self._showMsg(raw_msg)
            elif msgType == 49:  # link
                appMsgType = defaultdict(lambda: "")
                appMsgType.update({5: '链接', 3: '音乐', 7: '微博'})
                logger.info('=========================')
                logger.info('= Title: %s' % msg['FileName'])
                logger.info('= Desc : %s' % self._searchContent('des', content, 'xml'))
                logger.info('= Link : %s' % msg['Url'])
                logger.info('= From : %s' % self._searchContent('appname', content, 'xml'))
                logger.info('=========================')
                card = {
                    'title': msg['FileName'],
                    'description': self._searchContent('des', content, 'xml'),
                    'url': msg['Url'],
                    'appname': self._searchContent('appname', content, 'xml')
                }
                raw_msg = {'raw_msg': msg, 'message': '%s 分享了一个%s: %s' % (
                    name, appMsgType[msg['AppMsgType']], json.dumps(card))}
                self._showMsg(raw_msg, card)

            else:
                logger.info('[*] message type: %d, maybe emotion, picture, link or money' %
                      (msg['MsgType']))

    def listenMsgMode(self):
        logger.info('[*] Enter listen mode ... Successfully')
        self._run('[*] Enter sync check, select channel ... ', self.get_valid_sync_channel)

        while True:
            self.lastCheckTs = time.time()
            [retcode, selector] = self.synccheck()
            
            logger.info('retcode: %s, selector: %s' % (retcode, selector))
            if retcode == '1100':
                logger.info('[*] You logout wechat in phone, goodbye')
                break
            elif retcode == '1101':
                logger.info('[*] You have login web wechat other place, goodbye')
                break
            elif retcode == '1102':
                logger.warn('[*] current channel: %s lost heart-beat, so change channel' % (self.syncHost))
                self.get_valid_sync_channel()
                break
            elif retcode == '0':
                if selector == '2' or selector == '6':
                    r = self.webwxsync()
                    if r is not None:
                        self.handleMsg(r)
                elif selector == '0':
                    time.sleep(1)

            if (time.time() - self.lastCheckTs) <= 20:
                time.sleep(time.time() - self.lastCheckTs)

    def sendMsg(self, name, word, isfile=False):
        idlist = self.getUSerIDByRemarkName(name)
        if idlist:
            if isfile:
                with open(word, 'r') as f:
                    for line in f.readlines():
                        line = line.replace('\n', '')
                        self._echo('-> ' + name + ': ' + line)
                        for id in idlist:
                            if self.webwxsendtextmsg(line, id):
                                print(' [Successful]')
                            else:
                                print(' [Fail]')
                            time.sleep(1)
            else:
                for id in idlist:
                    print("[*] Send text message id: ", id)
                    if self.webwxsendtextmsg(word, id):
                        print('[*] Send text message successfully')
                    else:
                        print('[*] Send text message failed')

        else:
            print('[*] user is not exist')

    @catchKeyboardInterrupt
    def start(self):
        self._echo('[*] Web wechat ... start \n')
        while True:
            self._run('[*] Get uuid ... ', self.getUUID)
            self._echo('[*] Get QR code ... successfully \n')
            self.genQRCode()
            print('[*] Please scan QR code by phone ... ')
            if not self.waitForLogin():
                continue
                print('[*] Please click OK on your phone to sign in ... ')
            if not self.waitForLogin(0):
                continue
            break

        self._run('[*] Login ... ', self.login)
        self._run('[*] Wechat init ... ', self.webwxinit)
        self._run('[*] Turn on status notifications ... ', self.webwxstatusnotify)
        self._run('[*] Get contact ... ', self.webwxgetcontact)

        self._echo('[*] Group number: %d | Contact number: %d | Special number: %d | Public(service) number %d \n'
                   % (
                       len(self.GroupList), len(self.ContactList), len(self.SpecialUsersList),
                       len(self.PublicUsersList)))

        self._run('[*] Get Group ... ', self.webwxbatchgetcontact)

        print('[*] Get listen groups, keywords, notify persions information')
        self.getListenGroupFromFile()
        self.getKeyWordsFromFile()
        self.getNotifyPersonFromFile()

        print('[*] Myself information\n', self)

        if (self.uin != '1497306215') and (self.User['NickName'] != 'John') and (self.User['NickName'] != 'Johnny白恒'):
            print("[*] No permission... ")
            return

        if sys.platform.startswith('win'):
            import _thread
            _thread.start_new_thread(self.listenMsgMode())
        else:
            listenProcess = multiprocessing.Process(target=self.listenMsgMode)
            listenProcess.start()

        while True:
            text = input('')
            if text == 'quit':
                listenProcess.terminate()
                print('[*] Quit')
                exit()
            elif text[:2] == '->':
                [name, word] = text[2:].split(':')
                self.sendMsg(name, word)
            elif text[:3] == 'm->':
                [name, file] = text[3:].split(':')
                self.sendMsg(name, file, True)

    def _safe_open(self, path):
        if self.autoOpen:
            if platform.system() == "Linux":
                os.system("xdg-open %s &" % path)
            else:
                os.system('open %s &' % path)

    def _run(self, str, func, *args):
        self._echo(str)
        if func(*args):
            print('Successful')
        else:
            print('Failed\n[*] Quit')
            exit()

    def _echo(self, str):
        sys.stdout.write(str)
        sys.stdout.flush()

    def _transcoding(self, data):
        if not data:
            return data
        result = None
        if type(data) == str:
            result = data
        elif type(data) == str:
            result = data.decode('utf-8')
        return result

    def _get(self, url: object, api: object = None) -> object:
        request = urllib.request.Request(url=url)
        request.add_header('Referer', 'https://wx.qq.com/')
        if api == 'webwxgetvoice':
            request.add_header('Range', 'bytes=0-')
        if api == 'webwxgetvideo':
            request.add_header('Range', 'bytes=0-')
        try:
            response = urllib.request.urlopen(request)
            data = response.read().decode('utf-8')            
            response.close()
            time.sleep(3)  # 这里时间自己设定, 单位: seconds
            return data
        except urllib.error.HTTPError as e:
            logger.error('HTTPError = ' + str(e.code))
        except urllib.error.URLError as e:
            logger.error('URLError = ' + str(e.reason))
        except http.client.HTTPException as e:
            logger.error('HTTPException')
        except Exception:
            import traceback
            logger.error('generic exception: ' + traceback.format_exc())
        return ''

    def _post(self, url: object, params: object, jsonfmt: object = True) -> object:
        if jsonfmt:
            data = (json.dumps(params)).encode()

            request = urllib.request.Request(url=url, data=data)
            request.add_header(
                    'ContentType', 'application/json; charset=UTF-8')
        else:
            request = urllib.request.Request(url=url, data=urllib.parse.urlencode(params).encode(encoding='utf-8'))

        try:
            response = urllib.request.urlopen(request)
            data = response.read()
            response.close()
            if jsonfmt:
                return json.loads(data.decode('utf-8'))
            return data
        except urllib.error.HTTPError as e:
            logging.error('HTTPError = ' + str(e.code))
        except urllib.error.URLError as e:
            logging.error('URLError = ' + str(e.reason))
        except http.client.HTTPException as e:
            logging.error('HTTPException')
        except Exception:
            import traceback
            logging.error('generic exception: ' + traceback.format_exc())

        return ''

    def notifyPerson(self, groupName, groupmember, content):
        for keyword in self.KeyWords_1:
            if keyword in content:
                for person in self.NotifyPersionList_1:
                    self.sendMsg(person, u"【消息来自" + "#" + groupName + "#" + groupmember + "，由微信机器人发送，请勿回复】" + content)
                break

        for keyword in self.KeyWords_2:
            if keyword in content:
                for person in self.NotifyPersionList_2:
                    self.sendMsg(person, u"【消息来自" + "#" + groupName + "#" + groupmember + "，由微信机器人发送，请勿回复】" + content)
                break


class UnicodeStreamFilter:
    def __init__(self, target):
        self.target = target
        self.encoding = 'utf-8'
        self.errors = 'replace'
        self.encode_to = self.target.encoding

    def write(self, s):
        s = s.encode(self.encode_to, self.errors).decode(self.encode_to)
        self.target.write(s)

    def flush(self):
        self.target.flush()


if sys.stdout.encoding == 'cp936':
    sys.stdout = UnicodeStreamFilter(sys.stdout)

if __name__ == '__main__':
    logger.info("Version: %s" % "7.0 2017-07-14 BugFix: 不再从文件读取监听群信息")
    webwx = WebWeixin()
    webwx.start()
