![](https://raw.github.com/meolu/walle-web/master/docs/logo.jpg)

Quantitative_Trading
=========================
[![Build Status](https://travis-ci.org/meolu/walle-web.svg?branch=master)](https://travis-ci.org/meolu/walle-web)
[![Packagist](https://img.shields.io/packagist/v/meolu/walle-web.svg)](https://packagist.org/packages/meolu/walle-web)
[![Yii2](https://img.shields.io/badge/Powered_by-Yii_Framework-green.svg?style=flat)](http://www.yiiframework.com/)

微信机器人：实现微信群组信息的自动化过滤

    * 支持自定义关键字词
    * 支持发送到指定群组
    * 支持定义两组不同关键字词

聚宽策略: 在聚宽平台学习使用的策略，当前主要包含以下内容： 

* 日内交易策略
* 均线多头策略
* 小市值策略
* 主观交易系统


依赖
---

* Bash(git、ssh)
* LNMP/LAMP(php5.4+)
* Composer
* Ansible(可选)

安装
----
```
git clone https://github.com/LoveYakamoz/Quantitative_Trading.git
cd Quantitative_Trading

```

快速开始
----
* 注册一个管理员身份用户(已有`admin/admin`)，配置一个项目。
    * [git配置范例](https://walle-web.io/docs/git-configuration.html)
    * [svn配置范例](https://walle-web.io/docs/svn-configuration.html)
* 开发者注册用户(已有`demo/demo`)，提交上线单
* 管理员审核上线单
* 开发者发起上线

To Do List
----

- Travis CI 集成
- 邮件提醒：可配置提醒事件
- 灰度发布：指定机器发布
- 引入websocket
- 静态资源管理器
- 自定义公司logo
- 自定义变量
- 支持国际化：增加英文语言



版本记录
----
[CHANGELOG](https://github.com/LoveYakamoz/Quantitative_Trading/releases)


交流讨论
----
- [submit issue](https://github.com/LoveYakamoz/Quantitative_Trading/issues/new)
- email: yangpei3720@gmail.com

勾搭下
----
<img src="https://raw.githubusercontent.com/meolu/walle-web/feature-weixin/docs/weixin.wushuiyong.jpg" width="244" height="314" alt="Yakamoz微信" align=left />