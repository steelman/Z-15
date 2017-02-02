#!/usr/bin/python
# -*- coding: utf-8 -*-
# https://www.cairographics.org/cookbook/pycairo_pango/
#
# python Z-15.py && pdftk Z-15.pdf background Z-15-template.pdf output out.pdf
#
import cairo
import pango
import pangocairo
import datetime
import sys
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--datafile', help='plik YAML z danym')
parser.add_argument('--parent', help='rodzic występujący o zasiłek')
parser.add_argument('--child', help='dziecko pozostające pod opieką')
parser.add_argument('--since', help='pierwszy dzień zwolnienia')
parser.add_argument('--until', help='ostatni dzień zwolnienia')
args = parser.parse_args()

### PESEL ###
class PeselError(Exception):
    def __init__(self,komunikat):
        self.value=komunikat
    def __str__(self):
        return repr(self.value)

def pesel_11(nrid):
    '''Podaje ostatnią cyfrę peselu (jako znak) na podstawie poprzednich.'''
    wagi='1379137913'
    def _mn(a):
        return int(a[0])*int(a[1])
    x=sum(map(_mn,zip(nrid[0:10],wagi)))
    return str((10-x%10)%10)

def pesel_ok(nrid):
    '''Określa poprawność PESELu na podstawie cyfry kontrolnej.'''
    if len(nrid)<11:
        return False
    else:
        return (nrid[10]==pesel_11(nrid))

def pesel_data(nrid):
    '''Podaje datę urodzenia na podstawie PESELu o ile jest poprawny'''
    if pesel_ok(nrid):
        d,m,r=int(nrid[4:6]),int(nrid[2:4]),int(nrid[0:2])
        r,m=(m>80)*1800+(m<80)*(1900+(m/20)*100)+r,m%20
        if m in range(1,13):
            return datetime.date(r,m,d)
        else:
          raise PeselError('Blad 3 lub 4 cyfry!')
    else:
        raise PeselError('Blad numeru PESEL')
### /PESEL ###

# Rozmiar kratki
# 62.049-43.311 18.738 px
# 709,934
# 14.99pt
surf = cairo.PDFSurface('Z-15.pdf', 595.275590551, 841.88976378)
context = cairo.Context(surf)

part1_layout={
    'parent_id': (38.140625, 113.25),
    'parent_last_name': (38.140625, 140.),
    'parent_first_name': (38.140625, 166.75),
    'parent_born': (391.906625, 166.75),
    'address_post_code': (38.140625, 237.),
    'address_post_office': (141.320625, 237.),
    'address_district': (38.140625, 263.75),
    'address_locality': (38.140625, 290.5),
    'address_street': (38.140625, 317.25),
    'address_house': (38.140625, 344.),
    'address_flat': (156.065625, 344.),
    'child_id': (38.140625, 484.48),
    'child_last_name': (38.140625, 511.23),
    'child_first_name': (38.140625, 537.98),
    'child_relation': (38.140625, 564.73),
    'child_born': (377.167625, 564.73),
    'leave_since': (88.311625, 634.5),
    'leave_until': (235.713625, 634.5),
}
#get font families:

font_map = pangocairo.cairo_font_map_get_default()
families = font_map.list_families()

pangocairo_context = pangocairo.CairoContext(context)
pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

layout = pangocairo_context.create_layout()
fontname = 'M+ 1m 12'
font = pango.FontDescription(fontname)
layout.set_font_description(font)

def boxed_text(ctx, x, y, text):
    ctx.save()
    ctx.translate(x,y)
    t = pango.parse_markup(u"<span letter_spacing=\"6880\">" + text.upper() + "</span>")
    layout.set_attributes(t[0])
    layout.set_text(t[1])
    ctx.set_source_rgb(0,0,0)
    pangocairo_context.update_layout(layout)
    pangocairo_context.show_layout(layout)
    ctx.restore()

opt_parent=args.parent
opt_child=args.child
opt_datafile=args.datafile

part1_date=''
with open(opt_datafile,'r') as file:
    part1_data=load(file,Loader=Loader)

(x,y)=part1_layout['parent_id']
t=unicode(part1_data['parents'][opt_parent]['id'])
d=pesel_data(t).strftime("%d%m%Y")
boxed_text(context, x, y, t)

(x,y)=part1_layout['parent_last_name']
t=unicode(part1_data['parents'][opt_parent]['last_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['parent_first_name']
t=unicode(part1_data['parents'][opt_parent]['first_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['parent_born']
boxed_text(context, x, y, d)

(x,y)=part1_layout['address_post_code']
t=unicode(part1_data['part1']['address']['post_code'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_post_office']
t=unicode(part1_data['part1']['address']['post_office'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_district']
t=unicode(part1_data['part1']['address']['district'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_locality']
t=unicode(part1_data['part1']['address']['locality'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_street']
t=unicode(part1_data['part1']['address']['street'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_house']
t=unicode(part1_data['part1']['address']['house'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_flat']
t=unicode(part1_data['part1']['address']['flat'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_id']
t=unicode(part1_data['part1']['child'][opt_child]['id'])
d=pesel_data(t).strftime("%d%m%Y")
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_last_name']
t=unicode(part1_data['part1']['child'][opt_child]['last_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_first_name']
t=unicode(part1_data['part1']['child'][opt_child]['first_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_relation']
t=unicode(part1_data['part1']['child'][opt_child]['relation'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_born']
boxed_text(context, x, y, d)


(x,y)=part1_layout['leave_since']
d=part1_data['part1']['leaves'][-1]['since'].strftime('%d%m%Y')
boxed_text(context, x, y, d)

(x,y)=part1_layout['leave_until']
d=part1_data['part1']['leaves'][-1]['until'].strftime('%d%m%Y')
boxed_text(context, x, y, d)


#layout.set_text(u"Hello World")
#layout.set_text(u"NNNNNNNNNNN")
#layout.set_attributes(pango.parse_markup(u"<span letter_spacing=\"6880\">NNNNNNNNNNN</span>")[0])
#context.set_source_rgb(0, 0, 0)
#pangocairo_context.update_layout(layout)
#pangocairo_context.show_layout(layout)
context.show_page()

#with open("cairo_text.png", "wb") as image_file:
#    surf.write_to_png(image_file)
