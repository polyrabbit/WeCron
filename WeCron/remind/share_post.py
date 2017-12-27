#coding: utf-8
import os
from cStringIO import StringIO
import logging

import requests
from PIL import Image, ImageFont, ImageDraw
from django.utils import lru_cache
from remind.utils import get_qrcode_url


logger = logging.getLogger(__name__)
FONT = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'asserts/STHEITI.ttf'), 60)
TPL_IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'asserts/share_post_template.jpg')
LOGO_PATH = os.path.join(os.path.dirname(__file__), '../common/static/img/favicon.jpeg')
UGULU_LOGO_PATH = os.path.join(os.path.dirname(__file__), 'asserts/ugulu_logo.jpg')
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

    header_x = (im_width - region_width) // 2
    header_y = (360 - region_height) // 2

    tpl.paste(avatar, box=(header_x, header_y), mask=get_circular_mask(avatar))
    dr = ImageDraw.Draw(tpl)
    dr.text((header_x + avatar_width, header_y+(avatar_height-txt_height)/2.5), header_txt,
            font=FONT, fill='white')
    return tpl


def draw_body(tpl, text):
    text = text.strip()
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
            if line_width + chr_width >= container_width or chr == '\n':
                text_height += line_max_height + LINE_SPACING - 4.5  # some gap?
                if text_height > im_height * 0.4:
                    text_buf[-1] = '...'
                    text_height -= LINE_SPACING
                    break
                if line_width + chr_width >= container_width:
                    # If line exceeds container width, insert a carriage return
                    text_buf.append('\n')
                elif chr == '\n':
                    chr_width = 0
                line_width = 0
                line_max_height = 0
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
    text_offset = ((im_width - font_width) // 2, (im_height - text_height) // 2)
    dr.text(text_offset, text, font=FONT, fill='#545255', spacing=LINE_SPACING)

    # Draw quotes
    quote_font = FONT
    quote_offset = quote_font.getsize(u'“')
    dr.text((text_offset[0] - quote_offset[0], text_offset[1]),
            u'“', font=quote_font, fill='#3784f8')
    dr.text((text_offset[0] + line_width, text_offset[1] + text_height - line_max_height),
            u'”', font=quote_font, fill='#3784f8')
    return tpl


def draw_footer(tpl, qr, logo_path):
    qr = qr.resize((200, 200), Image.ANTIALIAS)
    qr_width, qr_height = qr.size
    qr = qr.convert('RGB')

    # Paste logo
    logo = Image.open(logo_path)
    logo = logo.resize((qr_width//4, qr_height//4), Image.ANTIALIAS)
    logo_width, logo_height = logo.size
    qr.paste(logo, box=((qr_width-logo_width)//2, (qr_height-logo_height)//2))

    # Paste QR code
    im_width, im_height = tpl.size
    box_x = im_width - qr_width - 70
    box_y = im_height - qr_height - 40
    tpl.paste(qr, box=(box_x, box_y))
    return tpl


@lru_cache.lru_cache(maxsize=128)
def http_get_bytes(url):
    # idempotent, so it can be cached
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content


def draw_post(remind, user=None):
    text = remind.desc

    if user is None:
        user = remind.owner

    try:
        avatar = Image.open(StringIO(http_get_bytes(user.headimgurl)))
    except Exception as e:
        logger.warning('Failed to build user avatar for %s, use a default one: %s', user.get_full_name(), e.message)
        avatar = Image.new('RGB', (128, 128), 'white')

    qr_url = get_qrcode_url(remind.id.hex)
    qr = Image.open(StringIO(http_get_bytes(qr_url)))

    tpl = Image.open(TPL_IMAGE_PATH)
    draw_header(tpl, avatar, user.get_full_name())
    draw_body(tpl, text)
    logo_path = LOGO_PATH
    if remind.owner.pk == 'owQF1vwl4GxUD8nTsiC0tVBla2H8':
        logo_path = UGULU_LOGO_PATH
    draw_footer(tpl, qr, logo_path)
    logger.info('%s requests a share post for %s', user.get_full_name(), text)
    return tpl
