# 提醒即服务 - Reminder as a Service

`微定时`是一个基于微信的定时提醒服务，为适应广大程序员小伙伴们的接入需求，`微定时`开放了动态创建提醒的接口，希望把提醒也做成一种服务，即**RaaS(Reminder as a Service)**，这样当一个系统需要定时提醒功能的时候，就可以直接集成`微定时`而不需要从头开发一个完整的定时提醒系统。

## 应用场景

* 组织活动 - 一个活动/会议管理系统可以在每次创建活动/会议的时候，通过`微定时`提供的接口，获取订阅二维码或者海报，让参与者扫码后就能订阅提醒。
* 你的场景？

## 优势

* 扫码订阅 - 创建提醒后，调用方可以获得一个二维码，这个二维码可以贴到活动宣传海报或者活动页面上，用户用微信扫码后，就自动订阅了该提醒，而无需额外操作。
* 自然语言中的时间实体识别 - ~~在没有提供`time`字段的情况下，`微定时`能自动提取`desc`字段中的时间信息，转化成提醒时间。~~

## REST请求

### 请求地址

```http
http://wecron.betacat.io/reminds/api/
```

### 认证授权

每一个对提醒的操作均需在 HTTP 请求头部增加一个 Authorization 字段，其值为认证凭证的字符串，示例如下：

```http
Authorization: Token <my_secret_token>
```

认证凭证目前是手动生成的，有需求的小伙伴可以通过邮箱与我取得联系：

<a href="http://wecron.betacat.io" class="rich-diff-level-one">
  <img src="https://user-images.githubusercontent.com/2657334/84649270-cf598000-af38-11ea-8bd9-6ad7e65f5d2f.png" alt="个人微信号：bytewalker" height="30">
</a>


### 请求格式

```js
POST /reminds/api/
Authorization: Token <my_secret_token>
Content-Type: application/json

{
    "time": <remind_time>,
    "title": <title>,
    "desc": <description>,
    "defer": <defer>，
    “external_url”: <external_url>
}
```

|       参数       |   类型  | 必须 |     说明       |
| --------------- | ------- | --- | ------------- |
| `<remind_time>` |  long   |  是 | unix timestamp形式的提醒时间，**单位是毫秒(ms)**，例如：1507695258535 |
| `<title>`       |  string |  否 | 提醒显示的标题，例如：还信用卡  |
| `<description>` |  string |  是 | 提醒的描述，例如：每月25号提醒我还信用卡 |
| `<defer>`       |  int    |  否 | 提醒提前/延后时间，以分钟为单位，例如：`-60`代表提前1小时，`60`代表延后1小时提醒 |
| `<external_url>`|  string |  否 | 活动的详细链接，这里填写的是该活动的详细页面，当用户点击`微定时`弹出的提醒时跳转的页面，例如：`http://www.huodongxing.com/event/4406039677700` |

## REST响应

### HTTP响应状态码

|       HTTP状态码       |        含义        | 说明                                    |
| --------------------- | ----------------- | --------------------------------------- |
|          200          |  Success          | 成功                                     |
|          400          |  Invalid params   | 请求参数错误或者格式不正确                   |
|          401          |  Unauthorized     | 认证授权失败，请检查`<access_token>`是否正确 |

### 响应格式

```js
HTTP/1.1 200 OK
Content-Type: application/json

{
  "title": <title>,
  "time": <remind_time>,
  "owner": {
    "nickname": <owner_name>,
    "headimgurl": <owner_avatar_url>
  },
  "id": <remind_id>,
  "defer": <defer>,
  "desc": <description>,
  "participate_qrcode": <participate_qrcode_url>,
  "post_url": <post_url>
}
```

|          参数         |   类型  |     说明       |
| -------------------- | ------- | ------------- |
| `<remind_time>`             |  long   | unix timestamp形式的设置的提醒时间 |
| `<title>`                   |  string | 提醒显示的标题  |
| `<owner_name>`              |  string | `<access_token>`所标志的用户名  |
| `<owner_avatar_url>`        |  string | `<access_token>`所标志的用户的头像url  |
| `<remind_id>`               |  string | 32位长度的提醒id  |
| `<description>`             |  string | 提醒的描述 |
| `<defer>`                   |  int    | 提醒提前/延后时间，以分钟为单位 |
| `<participate_qrcode_url>`  |  string | 微信二维码地址，用户扫描后可以订阅该提醒 |
| `<post_url>`                |  string | 提醒海报的地址， |

## 示例

### 请求示例 - curl

```bash
curl -H "Content-Type: application/json" -H 'Authorization: Token <my_secret_token>' -X POST -d '{"time":1514297534431,"desc":"我是测试提醒","title":"测试一下","defer": -60,"external_url": "https://www.baidu.com/s?wd=wecron"}' http://wecron.betacat.io/reminds/api/
```

### 响应示例

```js
HTTP/1.1 200 OK
Content-Type: application/json

{
  "title": "测试一下",
  "time": 1514297534431,
  "owner": {
    "nickname": "awk",
    "headimgurl": "http://wx.qlogo.cn/mmopen/PoLd0uGbcFiacCQXjyibsQoBiaxm4t0icricq90yfyBHvgueupXFnzhdqMM9DtEZnCTq00UCkAqvgWBTp5ricqb69UicsQKjN6VfOYJ/0"
  },
  "id": "fa14853c329a4d21901c72c0e7ff1867",
  "defer": -60,
  "desc": "我是测试提醒",
  "external_url": "https://www.baidu.com/s?wd=wecron",
  "participate_qrcode": "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=gQGC8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAybzIyZ2NWMTE5Ul8xMDAwMGcwN2gAAgRQVUJaAwQAAAAA",
  "post_url": "http://wecron.betacat.io/reminds/api/fa14853c329a4d21901c72c0e7ff1869/share_post/"
}
```