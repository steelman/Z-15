#!/usr/bin/python
# -*- coding: utf-8 -*-
# https://www.cairographics.org/cookbook/pycairo_pango/
#
# python Z-15.py && pdftk Z-15.pdf multibackground Z-15-template.pdf output out.pdf
#
import cairo
import pango
import pangocairo
import dateutil.parser
import datetime
import sys
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import argparse

class DateArgAction(argparse.Action):
    # def __init__(self, option_strings, dest, nargs=None, **kwargs):
    #     if nargs is not None:
    #         raise ValueError("nargs not allowed")
    #     super(FooAction, self).__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        _date = dateutil.parser.parse(values)
        print '%r %r %r' % (namespace, values, option_string)
        setattr(namespace, self.dest, _date)

parser = argparse.ArgumentParser()
parser.add_argument('--datafile', help='plik YAML z danym', required=True)
parser.add_argument('--parent', help='rodzic występujący o zasiłek', required=True)
parser.add_argument('--child', help='dziecko pozostające pod opieką', required=True)
parser.add_argument('--since', help='pierwszy dzień zwolnienia')
parser.add_argument('--until', help='ostatni dzień zwolnienia')
parser.add_argument('--date', help='data wypełnienia formularza', action=DateArgAction)
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

# cairo    inkscape
# (0,0) -> (0.8, 824.690)

# |      x1 |     y_1 |      x2 |       xm |   y_pdf |         x |      y |
# |---------+---------+---------+----------+---------+-----------+--------|
# |  49.029 | 775.252 |  63.769 |   56.399 |  66.638 | 52.273625 | 47.908 |
# | 181.690 | 775.252 | 196.430 |   189.06 |  66.638 | 184.93463 | 47.908 |
# |  63.518 | 754.843 |  78.758 |   71.138 |  87.047 | 67.012625 | 68.317 |
# | 181.439 | 754.843 | 196.679 |  189.059 |  87.047 | 184.93363 | 68.317 |
# | 358.321 | 734.434 | 373.561 |  365.941 | 107.456 | 361.81563 | 88.726 |
# | 417.281 | 734.434 | 432.522 | 424.9015 | 107.456 | 420.77613 | 88.726 |
# #+TBLFM: $4=($1+$3)/2::$5=841.89-$2::$6=$4 - (8.25075/2)::$7=$5-17.2-1.53

# 17.2pt położenie linii podstawowej tekstu na Y=0
# 1.53pt przesunięcie na środek kratki
# 8.pt szerokość komórki znaku

part2_layout={
    'other_caregiver_p': ((52.634625, 695.602), (126.33563, 695.602)),
    'shift_work':  ((52.634625, 756.378), (126.33563, 756.378)),
    # Strona 2.
    'other_caregiver_d': ((52.399, 47.908), (184.93463, 47.908),
                          (67.012625, 68.317), (184.93363, 68.317),
                          (361.81563, 88.726), (420.77613, 88.726)),
    'former_insurance': ((420.4035, 143.719), ( 479.364, 143.719)),
    'other_parent_care': ((52.399, 503.74),  # matka
                          (52.399, 524.149), # ojciec
                          (52.399, 544.559), # małżonek/małżonka
                          (31.039, 565.684), # dane osoby
                          (170.887, 726.563), # TAK, porała zasiłek
                          (229.848, 726.563), # NIE pobrała zasiłku
                          (52.399, 746.973),  # <14 lat
                          (52.399, 767.382),  # >= 14 lat
    # Strona 3.
                          (30.958, 48.25),
                      ),
}

#get font families:
#font_map = pangocairo.cairo_font_map_get_default()
#families = font_map.list_families()

pangocairo_context = pangocairo.CairoContext(context)
pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

layout = pangocairo_context.create_layout()
fontname = 'M+ 1m 12'
font_desc = pango.FontDescription(fontname)
font_desc.set_size(12*pango.SCALE)
layout.set_font_description(font_desc)

def _text(ctx, x, y, text, spacing):
    ctx.save()
    ctx.translate(x,y)
    t = pango.parse_markup(u"<span letter_spacing=\"" + str(spacing) +"\">" + text.upper() + "</span>")
    layout.set_attributes(t[0])
    layout.set_text(t[1])
    ctx.set_source_rgb(0,0,0)
    pangocairo_context.update_layout(layout)
    pangocairo_context.show_layout(layout)
    ctx.restore()

def boxed_text(ctx, x, y, text):
    _text(ctx, x, y, text, 6880)

def line_text(ctx, x, y, text):
    _text(ctx, x, y, text, 0)

def boxed_mark(ctx, x, y):
    ctx.save()
    ctx.translate(x,y)
    t = pango.parse_markup(u"<span letter_spacing=\"6880\">X</span>")
    layout.set_attributes(t[0])
    layout.set_text(t[1])
    ctx.set_source_rgb(0,0,0)
    pangocairo_context.update_layout(layout)
    pangocairo_context.show_layout(layout)
    ctx.restore()

def other_caregiver_p(ctx, leave):
    (yes, no)=part2_layout['other_caregiver_p']
    try:
        t = leave['other_caregiver']
    except KeyError:
        t = False
    if t:
        boxed_mark(ctx, yes[0], yes[1])
    else:
        boxed_mark(ctx, no[0], no[1])

def shift_work(ctx, parent):
    (yes, no)=part2_layout['shift_work']
    try:
        t = parent['shift_work']
    except KeyError:
        t = False
    if t:
        boxed_mark(ctx, yes[0], yes[1])
    else:
        boxed_mark(ctx, no[0], no[1])

def other_caregiver(ctx, parent):
    (_parent, spouse, work_y, work_n, shift_w_y, shift_w_n)=part2_layout['other_caregiver_d']
    if parent['parent'].upper() == 'OJECIEC' or \
       parent['parent'].upper() == 'MATKA':
        print "a parent"
        boxed_mark(ctx, _parent[0], _parent[1])
    else:
        print "a spouse"
        boxed_mark(ctx, spouse[0], spouse[1])

    try:
        t = parent['employer']
    except KeyError:
        t = None
    if not t is None:
        boxed_mark(ctx, work_y[0], work_y[1])
    else:
        boxed_mark(ctx, work_n[0], work_n[1])

    try:
        t = parent['shift_work']
    except KeyError:
        t = False
    if t:
        boxed_mark(ctx, shift_w_y[0], shift_w_y[1])
    else:
        boxed_mark(ctx, shift_w_n[0], shift_w_n[1])
    # TODO shift work hours

def former_insurance(ctx, parent):
    (yes, no) = part2_layout['former_insurance']

    try:
        t = parent['former_employer']
    except KeyError:
        t = None
    if t is None:
        boxed_mark(ctx, no[0], no[1])
    else:
        #TODO Sprawdzić czy u poprzedniego pracodawcy było wypłacane
        boxed_mark(ctx, yes[0], yes[1])

def leaves_this_year(leaves):
    ret = []
    y1 = datetime.date(opt_date.year, 1, 1)
    y2 = datetime.date.today()
    for l in leaves:
        since = l['since']
        until = l['until'] + datetime.timedelta(days=1)
        if  y1 <= since and since < y2 or \
            y1 <= until and until < y2:
            ret.append(l)
    return ret

def other_parent_took_care(ctx, parent):
    (mother, father, \
     spouse, other_parent_info_box, \
     yes, no, lt14, ge14,
     employer_info_box) = part2_layout['other_parent_care']
    if parent['parent'].upper() == 'MATKA':
        boxed_mark(ctx, mother[0], mother[1])
    elif parent['parent'].upper() == 'OJCIEC':
        boxed_mark(ctx, father[0], father[1])
    else:
        boxed_mark(ctx, spouse[0], spouse[1])

    personal_info(context, other_parent_info_box[0], other_parent_info_box[1], parent)

    if len(leaves_this_year(parent['leaves'])) > 0:
        boxed_mark(ctx, yes[0], yes[1])
    else:
        boexd_mark(ctx, no[0], no[1])

    for l in leaves_this_year(parent['leaves']):
        _s = l['since']
        _c = part1_data['part1']['child'][l['child']]
        _d = pesel_data(_c['id'])
        _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
        if _s < _age14:
            boxed_mark(ctx, lt14[0], lt14[1])
            break

    for l in leaves_this_year(parent['leaves']):
        _s = l['since']
        _c = part1_data['part1']['child'][l['child']]
        _d = pesel_data(_c['id'])
        _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
        if _s >= _age14:
            boxed_mark(ctx, ge14[0], ge14[1])
            break

    ctx.show_page()

    employer_info(ctx, employer_info_box[0], employer_info_box[1])

def personal_info(ctx, x, y, parent):
    boxed_text(ctx, x+3.249+3.62, y+35.99-1.53, parent['id'])
    line_text(ctx, x+6.82, y+72.9265-1.53, parent['last_name'])
    line_text(ctx, x+6.82, y+101.9265-1.53, parent['first_name'])

def employer_info(ctx, x, y, employer):
    pass

opt_date=args.date or datetime.datetime.now()
opt_date = datetime.datetime(opt_date.year, opt_date.month, opt_date.day)
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

this_parent=part1_data['parents'][opt_parent]
this_leave=this_parent['leaves'][-1]
(x,y)=part1_layout['leave_since']
d=this_leave['since'].strftime('%d%m%Y')
boxed_text(context, x, y, d)

(x,y)=part1_layout['leave_until']
d=this_leave['until'].strftime('%d%m%Y')
boxed_text(context, x, y, d)

other_caregiver_p(context, this_leave)
shift_work(context, this_parent)

context.show_page()

other_parent=part1_data['parents'][this_parent['other_parent']]
other_caregiver(context, other_parent)

former_insurance(context, this_parent)

this_child = part1_data['part1']['child'][opt_child]
other_parent_took_care(context, other_parent)

#layout.set_text(u"Hello World")
#layout.set_text(u"NNNNNNNNNNN")
#layout.set_attributes(pango.parse_markup(u"<span letter_spacing=\"6880\">NNNNNNNNNNN</span>")[0])
#context.set_source_rgb(0, 0, 0)
#pangocairo_context.update_layout(layout)
#pangocairo_context.show_layout(layout)
context.show_page()

#with open("cairo_text.png", "wb") as image_file:
#    surf.write_to_png(image_file)
