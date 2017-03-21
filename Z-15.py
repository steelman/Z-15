#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Fill in ZUS Z-15 form according to data in a YAML file.
# Copyright (C) 2016,2017  Łukasz Stelmach
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import cairo
import pango
import pangocairo
import dateutil.parser
import datetime
import sys
from pesel import *
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

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''
Tworzy plik PDF zawierający wypełnienie formularza ZUS Z-15. Gdy nie
została podana nazwa pliku (opcja --outfile) zostanie utworzony plik
"Z-15.pdf". Utworzony plik należy połączyć z szablonem formularza
w pliku Z-15-template.pdf następującym poleceniem:

    pdftk Z-15.pdf multibackground Z-15-template.pdf output out.pdf
''')
parser.add_argument('--datafile', help='plik YAML z danym', required=True)
parser.add_argument('--parent', help='rodzic występujący o zasiłek', required=True)
parser.add_argument('--outfile', help='wyjściowy plik PDF', default='Z-15.pdf')
parser.add_argument('--font', help='czcionka', default='M+ 1m,mono')
# parser.add_argument('--child', help='dziecko pozostające pod opieką', required=True)
# parser.add_argument('--since', help='pierwszy dzień zwolnienia')
# parser.add_argument('--until', help='ostatni dzień zwolnienia')
parser.add_argument('--date', help='data wypełnienia formularza', action=DateArgAction)
args = parser.parse_args()

# cairo    inkscape
# (0,0) -> (0.8, 824.690)

# |      x1 |     y_1 |      x2 |       xm |   y_pdf |         x |      y |
# |---------+---------+---------+----------+---------+-----------+--------|
# |         |         |         |          |         |           |        |
# #+TBLFM: $4=($1+$3)/2::$5=841.89-$2::$6=$4 - (8.25075/2)::$7=$5-17.2-1.53
#
# 17.2pt położenie linii podstawowej tekstu na Y=0
# 1.53pt przesunięcie na środek kratki
# 8.pt szerokość komórki znaku

part1_layout={
    'parent_id': (34.649, 709.934),
    'parent_last_name' : (34.649, 683.194),
    'parent_first_name' : (34.649, 656.444),
    'parent_born' : (388.415, 656.444),
    'address_post_office' : (137.829, 586.194),
    'address_post_code' : (34.649, 586.194),
    'address_suburb' : (34.649, 559.444),
    'address_city' : (34.649, 532.694),
    'address_street' : (34.649, 505.944),
    'address_housenumber' : (34.649, 479.194),
    'address_door' : (152.574, 479.194),
    'child_id' : (34.649, 338.704),
    'child_last_name' : (34.649, 311.964),
    'child_first_name' : (34.649, 285.885),
    'child_relation' : (34.649, 259.145),
    'child_born' : (373.676, 259.145),
    'leave_since' : (84.818, 188.644),
    'leave_until' : (232.220, 188.644),
}

part2_layout={
    # Strona 1
    'other_caregiver_p': ((49.140, 127.542), (122.841, 127.542)),
    'shift_work': ((48.640, 66.766), (122.341, 66.766)),
    # Strona 2
    'other_caregiver_d': ((48.778, 775.252),  # Matka/ojciec
                          (181.439, 775.252), # małżonek/małżonka
                          (63.518, 754.843), (181.439, 754.843),   # pracuje/nie pracuej
                          (358.321, 734.434), (417.281, 734.434)), # praca zmianowa
    'former_insurance': ( (416.783, 679.441), (475.744, 679.411)),
    'other_parent_care': ((48.799, 319.420), # matka dziecka
                          (48.799, 299.011), # ojciec dziecka
                          (48.799, 278.601), # małżonek/małżonka
                          (31.039, 259.006), # dane osobowe
                          (167.267, 96.597), # TAK pobrał(a) zasiłek
                          (226.228, 96.597), # NIE pobrał(a) zasiłku
                          (48.779, 76.187),  # <14 lat
                          (48.779, 55.778),  # >=14 lat
    # Strona 3
                          (30.958, 793.640)), # płatnik składek
    # Strona 4
    'living_with_child': ((48.779, 775.252), (129.850, 775.252), ),
    'bank_account': (30.778, 713.104),
}

opt_outfile=args.outfile
surf = cairo.PDFSurface(opt_outfile, 595.276, 841.89)
context = cairo.Context(surf)

pangocairo_context = pangocairo.CairoContext(context)
pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

layout = pangocairo_context.create_layout()
fontname = 'M+ 10m,mono'
fontname = args.font
font_desc = pango.FontDescription(fontname)
font_desc.set_absolute_size(16*pango.SCALE)
layout.set_font_description(font_desc)

# TODO
pctx=layout.get_context()

#   TODO wydobyć to programowo indeks znaku "M"
#   "M" w większości czcionek jes pod indeksem 48
#   (x, y, width, height)
# font=pctx.load_font(font_desc)
# ink,log = font.get_glyph_extents(48)
# print repr(ink)
# print repr(log)
# font_ascent = pango.ASCENT(log)/float(pango.SCALE)
# font_descent = pango.DESCENT(log)/float(pango.SCALE)
# font_width = (pango.RBEARING(log) - pango.LBEARING(log))/float(pango.SCALE)
# print font_ascent
# print font_descent
# print font_width

pfm=pctx.get_metrics(font_desc, pango.Language('pl'))
font_ascent = pfm.get_ascent()/float(pango.SCALE)
font_descent = pfm.get_descent()/float(pango.SCALE)
font_width = pfm.get_approximate_char_width()/float(pango.SCALE)

def _text(ctx, x, y, text, spacing):
    _y = 841.89 - y - 0.45
    ctx.save()
    ctx.translate(x,_y)
    t = pango.parse_markup(u"<span letter_spacing=\"" + str(spacing) +"\">" + text.upper() + "</span>")
    layout.set_attributes(t[0])
    layout.set_text(t[1])
    ctx.set_source_rgb(0,0,0)
    #    DEBUG: rysuj skośną linię
    # rect = layout.get_extents()[1]
    # ctx.set_line_width(1)
    # ctx.move_to(rect[0]/float(pango.SCALE), rect[1]/float(pango.SCALE))
    # ctx.line_to(rect[2]/float(pango.SCALE), rect[3]/float(pango.SCALE))
    # ctx.stroke()
    # print ">" + repr([float(x)/pango.SCALE for x in rect])
    pangocairo_context.update_layout(layout)
    pangocairo_context.show_layout(layout)
    ctx.restore()

def boxed_text(ctx, x, y, text):
    # 14,74 pt - rozmiar kratki
    _y = y + font_ascent # - (14.74 - font_ascent)/2
    _x = x + (14.74 - font_width)/2
    _s = int((14.74 - font_width) * pango.SCALE)
    _text(ctx, _x, _y, text, _s)

def dotted_text(ctx, x, y, text):
    _y = y + font_ascent # - (14.74 - font_ascent)/2
    _x = x + (14.74 - font_width)/2
    _text(ctx, x, _y, text, 0)

def boxed_mark(ctx, x, y):
    _y = 841.89 - y - font_ascent
    _x = x + (14.74 - font_width)/2
    ctx.save()
    ctx.translate(_x,_y)
    t = pango.parse_markup(u"<span>X</span>")
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
    if parent['parent'].upper() == 'OJCIEC' or \
       parent['parent'].upper() == 'MATKA':
        boxed_mark(ctx, _parent[0], _parent[1])
    else:
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
    # TODO: Godziny pracy zmianowej

def former_insurance(ctx, parent):
    (yes, no) = part2_layout['former_insurance']

    try:
        t = parent['former_employer']
    except KeyError:
        t = None
    if t is None:
        boxed_mark(ctx, no[0], no[1])
    else:
        #TODO: Sprawdzić czy u poprzedniego pracodawcy było wypłacane
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
        _c = DATA['CHILDREN'][l['child']]
        _d = pesel_data(_c['id'])
        _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
        if _s < _age14:
            boxed_mark(ctx, lt14[0], lt14[1])
            break

    for l in leaves_this_year(parent['leaves']):
        _s = l['since']
        _c = DATA['CHILDREN'][l['child']]
        _d = pesel_data(_c['id'])
        _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
        if _s >= _age14:
            boxed_mark(ctx, ge14[0], ge14[1])
            break

    ctx.show_page()

    employer_info(ctx,
                  employer_info_box[0],
                  employer_info_box[1],
                  DATA['ADDRESSES'][parent['employer']])

def personal_info(ctx, x, y, parent):
    boxed_text(ctx, x+3.249, y-35.99, parent['id'])
    dotted_text(ctx, x+6.82, y-73.377, parent['last_name'])
    dotted_text(ctx, x+6.82, y-102.377, parent['first_name'])

def employer_info(ctx, x, y, employer):
    dotted_text(ctx, x+6.82, y-38.952, employer['name'])
    boxed_text(ctx, x+3.25, y-72.18, employer['post_code'])
    dotted_text(ctx, x+134.042, y-68.086, employer['post_office'])
    try:
        T=employer['city']
        T=employer['suburb']
    except KeyError:
        pass
    dotted_text(ctx, x+6.820000, y-103.237, T)
    dotted_text(ctx, x+6.820000, y-132.237, employer['city'])
    dotted_text(ctx, x+6.820000, y-161.237, employer['street'])
    dotted_text(ctx, x+6.820000, y-188.062, unicode(employer['housenumber']))
    try:
        T=unicode(employer['door'])
        dotted_text(ctx, x+109.784, y-188.062, T)
    except KeyError:
        pass
    # TODO:
    # + symbol państwa
    # + zagraniczny kod pocztowy
    # + nazwa państwa

def living_with_child_above_fourteen(ctx, parent, this_leave, child):
    (yes, no) = part2_layout['living_with_child']
    _s = this_leave['since']
    _d = pesel_data(child['id'])
    _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
    child_name = this_leave['child']
    if _s < _age14:
        return
    try:
        l = parent['living_with']
        if child_name in l:
            boxed_mark(ctx, yes[0], yes[1])
        else:
            boxed_mark(ctx, no[0], no[1])
    except KeyError:
        boxed_mark(ctx, yes[0], yes[1])

opt_date=args.date or datetime.date.today()
opt_date = datetime.datetime(opt_date.year, opt_date.month, opt_date.day)
opt_parent=args.parent
opt_datafile=args.datafile

with open(opt_datafile,'r') as file:
    DATA=load(file,Loader=Loader)

this_parent=DATA['PARENTS'][opt_parent]
this_leave=this_parent['leaves'][-1]
other_parent=DATA['PARENTS'][this_parent['other_parent']]
this_child = DATA['CHILDREN'][this_leave['child']]

(x,y)=part1_layout['parent_id']
t=unicode(DATA['PARENTS'][opt_parent]['id'])
d=pesel_data(t).strftime("%d%m%Y")
boxed_text(context, x, y, t)

(x,y)=part1_layout['parent_last_name']
t=unicode(DATA['PARENTS'][opt_parent]['last_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['parent_first_name']
t=unicode(DATA['PARENTS'][opt_parent]['first_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['parent_born']
boxed_text(context, x, y, d)

(x,y)=part1_layout['address_post_code']
t=unicode(DATA['ADDRESSES'][this_parent['address']]['post_code'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_post_office']
t=unicode(DATA['ADDRESSES'][this_parent['address']]['post_office'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_suburb']
t=unicode(DATA['ADDRESSES'][this_parent['address']]['suburb'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_city']
t=unicode(DATA['ADDRESSES'][this_parent['address']]['city'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_street']
t=unicode(DATA['ADDRESSES'][this_parent['address']]['street'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_housenumber']
t=unicode(DATA['ADDRESSES'][this_parent['address']]['housenumber'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['address_door']
try:
    t=unicode(DATA['ADDRESSES'][this_parent['address']]['door'])
    boxed_text(context, x, y, t)
except KeyError:
    pass

(x,y)=part1_layout['child_id']
t=unicode(this_child['id'])
d=pesel_data(t).strftime("%d%m%Y")
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_last_name']
t=unicode(this_child['last_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_first_name']
t=unicode(this_child['first_name'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_relation']
t=unicode(this_child['child'])
boxed_text(context, x, y, t)

(x,y)=part1_layout['child_born']
boxed_text(context, x, y, d)

(x,y)=part1_layout['leave_since']
d=this_leave['since'].strftime('%d%m%Y')
boxed_text(context, x, y, d)

(x,y)=part1_layout['leave_until']
d=this_leave['until'].strftime('%d%m%Y')
boxed_text(context, x, y, d)

other_caregiver_p(context, this_leave)
shift_work(context, this_parent)

context.show_page()

other_caregiver(context, other_parent)

former_insurance(context, this_parent)

other_parent_took_care(context, other_parent)
context.show_page()

# TODO: Wypisanie informacji o innym członku rodziny

living_with_child_above_fourteen(context, this_parent, this_leave, this_child)

(x,y)=part2_layout['bank_account']
t=unicode(this_parent['bank_account'])
boxed_text(context, x, y, t)
