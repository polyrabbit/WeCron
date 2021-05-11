# WeCron

[![license](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/polyrabbit/WeCron/blob/master/LICENSE)
[![Build Status](https://api.travis-ci.org/polyrabbit/WeCron.svg)](https://travis-ci.org/polyrabbit/WeCron)
[![codecov](https://codecov.io/gh/polyrabbit/WeCron/branch/master/graph/badge.svg)](https://codecov.io/gh/polyrabbit/WeCron)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/polyrabbit/WeCron/pulls)

微信上的定时提醒 - Cron on WeChat

<p>
<a href="http://wecron.betacat.io" class="rich-diff-level-one">
  <img src="https://user-images.githubusercontent.com/2657334/34242455-7c9ae230-e656-11e7-8420-3da003d87ce5.jpeg" height="500" alt="图片描述" align=center />
</a>
</p>

## 本地运行

1. Clone代码

```bash
git clone https://github.com/polyrabbit/WeCron.git
```

2. 安装依赖包

```bash
cd WeCron
pip install -r requirements.txt
```

3. 初始化数据库

```bash
# 创建数据库
psql -c 'CREATE DATABASE "wecron" WITH OWNER "postgres" TEMPLATE template0 ENCODING="UTF8" CONNECTION LIMIT=-1;'
psql -c 'GRANT ALL PRIVILEGES ON DATABASE "wecron" to "postgres";'

# 建表
python WeCron/manage.py migrate
```

4. 启动本地Server

```bash
python WeCron/manage.py runserver
```

### 扫码关注微定时公众号，体验一下吧
<p>
<a href="http://wecron.betacat.io" class="rich-diff-level-one">
  <img src="https://user-images.githubusercontent.com/2657334/117764620-64571d00-b25f-11eb-857a-d8c12932065f.png" alt="微定时二维码" data-canonical-src="https://mp.weixin.qq.com/misc/getqrcode?fakeid=3937213371&token=849973266" height="150">
</a>
</p>

## 关于

* 文档：[WeCron是怎样处理定时任务的
](http://blog.betacat.io/post/how-wecron-schedules/)
* 感谢[@messense](https://github.com/messense)贡献的微信公众平台SDK [wechatpy](http://docs.wechatpy.org)！
* WeCron开始于2015年，一直稳定运行着，并将持续维护下去（因为我个人也是重度用户）
