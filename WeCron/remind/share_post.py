#coding: utf-8
import os
import requests
from cStringIO import StringIO
from PIL import Image, ImageFont, ImageDraw
from remind.utils import get_qrcode_url


FONT = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'asserts/STHEITI.ttf'), 60)
tpl_post_path = os.path.join(os.path.dirname(__file__), 'asserts/share_post_template.png')
LINE_SPACING = 20


def get_circular_mask(avatar):
    bigsize = (avatar.size[0] * 3, avatar.size[1] * 3)
    mask = Image.new('L', bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    # avatar.putalpha(mask)
    return mask.resize(avatar.size, Image.ANTIALIAS)


def draw_header(tpl, avatar, uname):
    avatar = avatar.resize((120, 120), Image.ANTIALIAS)
    header_txt = u' %s分享的提醒' % uname
    im_width, im_height = tpl.size
    avatar_width, avatar_height = avatar.size
    txt_width, txt_height = FONT.getsize(header_txt)
    region_width = txt_width + avatar_width
    region_height = txt_height + avatar_height

    header_x = (im_width - region_width) / 2
    header_y = (360 - region_height) / 2

    tpl.paste(avatar, box=(header_x, header_y), mask=get_circular_mask(avatar))
    dr = ImageDraw.Draw(tpl)
    dr.text((header_x + avatar_width, header_y+(avatar_height-txt_height)/2.5), header_txt,
            font=FONT, fill='white')
    return tpl


def draw_body(tpl, text):
    im_width, im_height = tpl.size
    dr = ImageDraw.Draw(tpl)
    font_width, font_height = dr.textsize(text, FONT, spacing=LINE_SPACING)

    text_buf = []
    line_width = 0
    line_max_height = FONT.getsize(text[0])[1]
    text_height = 0
    container_width = im_width * 0.8
    # Text is limited in a container
    if font_width >= container_width:
        for chr in text:
            chr_width, chr_height = FONT.getsize(chr)
            line_max_height = max(line_max_height, chr_height)
            if line_width + chr_width >= container_width:
                text_height += line_max_height + LINE_SPACING - 5
                if text_height > im_height * 0.4:
                    text_buf[-1] = '...'
                    text_height -= LINE_SPACING
                    break
                line_width = 0
                line_max_height = 0
                text_buf.append('\n')
            text_buf.append(chr)
            line_width += chr_width
        else:
            text_height += line_max_height
        text = ''.join(text_buf)
        font_width, font_height = dr.textsize(text, FONT, spacing=LINE_SPACING)
    else:
        line_width = font_width
        text_height = font_height

    # Draw text
    text_offset = ((im_width - font_width) / 2, (im_height - text_height) / 2)
    dr.text(text_offset, text, font=FONT, fill='#545255', spacing=LINE_SPACING)

    # Draw quotes
    quote_font = FONT
    quote_offset = quote_font.getsize(u'“')
    dr.text((text_offset[0] - quote_offset[0], text_offset[1]),
            u'“', font=quote_font, fill='#3784f8')
    dr.text((text_offset[0] + line_width, text_offset[1] + text_height - line_max_height),
            u'”', font=quote_font, fill='#3784f8')
    return tpl


def draw_footer(tpl, qr):
    qr = qr.resize((200, 200), Image.ANTIALIAS)
    im_width, im_height = tpl.size
    qr_width, qr_height = qr.size
    box_x = im_width - qr_width - 70
    box_y = im_height - qr_height - 40
    tpl.paste(qr, box=(box_x, box_y))
    return tpl


def draw_post(remind, user=None):
    text = remind.desc
    tpl = Image.open(tpl_post_path)

    if user is None:
        user = remind.owner

    avatar_resp = requests.get(user.headimgurl)
    avatar = Image.open(StringIO(avatar_resp.content))

    qr_resp = requests.get(get_qrcode_url(remind.id.hex))
    qr = Image.open(StringIO(qr_resp.content))

    draw_header(tpl, avatar, user.get_full_name())
    draw_body(tpl, text)
    draw_footer(tpl, qr)
    return tpl


# TODO: test one line, two lines, too much lines
# from remind.models import Remind
# from wechat_user.models import WechatUser
# draw_post(Remind.objects.order_by('id').first(), WechatUser.objects.first()).show()