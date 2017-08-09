2017/4/26: init project
Description:
1. a webchat robot: It can extract some group infomation with special key words and send these infomations to special groups
3. joinQuant: 在聚宽平台学习使用的策略 

![](https://raw.github.com/meolu/walle-web/master/docs/logo.jpg)

Quantitative_Trading
=========================
[![Build Status](https://travis-ci.org/meolu/walle-web.svg?branch=master)](https://travis-ci.org/meolu/walle-web)
[![Packagist](https://img.shields.io/packagist/v/meolu/walle-web.svg)](https://packagist.org/packages/meolu/walle-web)
[![Yii2](https://img.shields.io/badge/Powered_by-Yii_Framework-green.svg?style=flat)](http://www.yiiframework.com/)

A web deployment tool, Easy for configuration, Fully functional, Smooth interface, Out of the box.
support git/svn Version control system, no matter what language you are, php/java/ruby/python, just as jenkins. you can deploy the code or output to multiple servers easily by walle.

目前，超过百家企业生产环境部署使用，欢迎star、fork、试用 ：）

* 支持git、svn版本管理
* 用户分身份注册、登录
* 开发者发起上线任务申请、部署
* 管理者审核上线任务
* 支持多项目部署
* 支持多项目多任务并行
* 快速回滚
* 项目的用户权限管理
* 部署前准备任务pre-deploy（前置检查）
* 代码检出后处理任务post-deploy（如vendor）


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


快速开始
-------
* 注册一个管理员身份用户(已有`admin/admin`)，配置一个项目。
    * [git配置范例](https://walle-web.io/docs/git-configuration.html)
    * [svn配置范例](https://walle-web.io/docs/svn-configuration.html)
* 开发者注册用户(已有`demo/demo`)，提交上线单
* 管理员审核上线单
* 开发者发起上线

To Do List
----------

- Travis CI 集成
- 邮件提醒：可配置提醒事件
- 灰度发布：指定机器发布
- 引入websocket
- 静态资源管理器
- 自定义公司logo
- 自定义变量
- 支持国际化：增加英文语言
- 支持Docker
- 开放接口




## CHANGELOG
版本记录: [CHANGELOG](https://github.com/LoveYakamoz/Quantitative_Trading/releases)


交流讨论
----------
- [submit issue](https://github.com/LoveYakamoz/Quantitative_Trading/issues/new)
- email: yangpei3720@gmail.com

勾搭下
--------
<img src="https://raw.githubusercontent.com/meolu/walle-web/feature-weixin/docs/weixin.wushuiyong.jpg" width="244" height="314" alt="Yakamoz微信" align=left />