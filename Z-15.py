#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Fill in ZUS Z-15 form according to data in a YAML file.
# Copyright (C) 2016-2018  Łukasz Stelmach
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

import dateutil.parser
import datetime
import sys
from fdfgen import forge_fdf, FDFIdentifier
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
        print('{} {} {}'.format(namespace, values, option_string))
        setattr(namespace, self.dest, _date)

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''
Tworzy plik PDF zawierający wypełnienie formularza ZUS Z-15. Gdy nie
została podana nazwa pliku (opcja --outfile) zostanie utworzony plik
"Z-15.fdf". Utworzony plik należy połączyć z szablonem formularza
w pliku Z-15-template.pdf następującym poleceniem:

    pdftk Z-15-template.pdf fill_form Z-15.fdf output out.pdf
''')
parser.add_argument('--datafile', help='plik YAML z danym', required=True)
parser.add_argument('--parent', help='rodzic występujący o zasiłek', required=True)
parser.add_argument('--outfile', help='wyjściowy plik PDF', default='Z-15.fdf')
parser.add_argument('--font', help='czcionka', default='M+ 1m,mono')
# parser.add_argument('--child', help='dziecko pozostające pod opieką', required=True)
# parser.add_argument('--since', help='pierwszy dzień zwolnienia')
# parser.add_argument('--until', help='ostatni dzień zwolnienia')
parser.add_argument('--date', help='data wypełnienia formularza', action=DateArgAction)
args = parser.parse_args()

opt_outfile=args.outfile

FDFTrue = FDFIdentifier('1')
FDFFalse = FDFIdentifier('0')
FDFOff = FDFIdentifier('Off')

def former_insurance(parent):
    try:
        t = parent['former_employer']
    except KeyError:
        t = None
    if t is None:
        return FDFOff
    else:
        #TODO: Sprawdzić czy u poprzedniego pracodawcy było wypłacane
        return FDFTrue

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

def other_parent_took_care(parent):
    fields = []
    days_lt14 = 0
    days_gt14 = 0

    f = u'topmostSubform[0].Page3[0].WybórTAKNIE3[0]'
    if len(leaves_this_year(parent['leaves'])) <= 0:
        fields.append((f, FDFFalse))
        return fields

    fields.append((f, FDFTrue))

    for l in leaves_this_year(parent['leaves']):
        _s = l['since']
        _u = l['until']
        _c = DATA['CHILDREN'][l['child']]
        _d = pesel_data(_c['id'])
        _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
        if _s < _age14:
            print("_s: {}".format(_s.strftime("%Y-%m-%d")))
            print("_u: {}".format(_u.strftime("%Y-%m-%d")))
            days_lt14 += (_u - _s).days + 1
        else:
            days_gt14 += (_u - _s).days

    if days_lt14 > 0:
        fields.append((u'topmostSubform[0].Page3[0].Liczbadni3a[0]', days_lt14))

    if days_gt14 >0:
        fields.append((u'topmostSubform[0].Page3[0].Liczbadni3b[0]', days_gt14))

    return fields

def living_with_child_above_fourteen(parent, this_leave, child):
    _s = this_leave['since']
    _d = pesel_data(child['id'])
    _age14 = datetime.date(_d.year + 14, _d.month, _d.day)
    child_name = this_leave['child']
    if _s < _age14:
        return FDFOff
    try:
        l = parent['living_with']
        if child_name in l:
            return FDFTrue
        else:
            return FDFFalse
    except KeyError:
        return FDFTrue

opt_date = args.date or datetime.date.today()
opt_date = datetime.datetime(opt_date.year, opt_date.month, opt_date.day)
opt_parent = args.parent
opt_datafile = args.datafile

with open(opt_datafile,'r') as file:
    DATA = load(file, Loader = Loader)

this_parent = DATA['PARENTS'][opt_parent]
this_leave = this_parent['leaves'][-1]
other_parent = DATA['PARENTS'][this_parent['other_parent']]
this_child = DATA['CHILDREN'][this_leave['child']]

fields = []

# Okres, za który ubiegasz się o zasiłek opiekuńczy
fields.append((u'topmostSubform[0].Page1[0].Tekst1[0]',
               this_leave['since'].strftime('%Y-%m-%d') + " - " +
               this_leave['until'].strftime('%Y-%m-%d')))

# Zwolnienie lekarske
fields.append((u'topmostSubform[0].Page1[0].Tekst2[0]',
               this_leave['since'].strftime('%Y-%m-%d') + " - " +
               this_leave['until'].strftime('%Y-%m-%d')))

# Dane dziecka
fields.append((u'topmostSubform[0].Page1[0].PESEL[0]', this_child['id'])) # PESEL
# (u'topmostSubform[0].Page1[0].Rodzajseriainumerdokumentu[0]', None),   # Dokument tożsamości
fields.append((u'topmostSubform[0].Page1[0].Imię[0]', this_child['first_name'])) # Imię
fields.append((u'topmostSubform[0].Page1[0].Nazwisko[0]', this_child['last_name']))
fields.append((u'topmostSubform[0].Page1[0].Dataurodzenia[0]', pesel_data(this_child['id']).strftime("%d%m%Y")))

# Dane rodzica
fields.append((u'topmostSubform[0].Page2[0].PESEL[0]', this_parent['id']))
# (u'topmostSubform[0].Page2[0].Rodzajseriainumerdokumentu[0]', None),   # Dokument tożsamości
fields.append((u'topmostSubform[0].Page2[0].Imię[0]', this_parent['first_name']))
fields.append((u'topmostSubform[0].Page2[0].Nazwisko[0]', this_parent['last_name']))
fields.append((u'topmostSubform[0].Page2[0].Ulica[0]', DATA['ADDRESSES'][this_parent['address']]['street']))
fields.append((u'topmostSubform[0].Page2[0].Numerdomu[0]', DATA['ADDRESSES'][this_parent['address']]['housenumber']))
fields.append((u'topmostSubform[0].Page2[0].Numerlokalu[0]', DATA['ADDRESSES'][this_parent['address']]['door']))
fields.append((u'topmostSubform[0].Page2[0].Kodpocztowy[0]', DATA['ADDRESSES'][this_parent['address']]['post_code']))
fields.append((u'topmostSubform[0].Page2[0].Poczta[0]', DATA['ADDRESSES'][this_parent['address']]['post_office']))

# Oświadczenia
# Jest domownik mogący zapewnić opiekę dziecku
try:
    t = this_leave['other_caregiver']
except KeyError:
    t = False
fields.append((u'topmostSubform[0].Page2[0].WybórTAKNIE[0]', FDFTrue if t else FDFFalse))

# Praca zmianowa
try:
    t = this_parent['shift_work']
except KeyError:
    t = False
fields.append((u'topmostSubform[0].Page2[0].WybórTAKNIE4[0]', FDFTrue if t else FDFFalse))


# Pozostajesz we wspólnym gospodarstwie z dzieckiem pow. 14 lat.
fields.append((u'topmostSubform[0].Page2[0].WybórTAKNIE2[0]',
               living_with_child_above_fourteen(this_parent, this_leave, this_child)))

# Zmiana płatkika
fields.append((u'topmostSubform[0].Page2[0].WybórTAKNIE3[0]', former_insurance(this_parent)))

# Drugi rodzic
fields.append((u'topmostSubform[0].Page3[0].PESEL[0]', other_parent['id']))
# (u'topmostSubform[0].Page3[0].Rodzajseriainumerdokumentu[0]', None),   # Dokument tożsamości
fields.append((u'topmostSubform[0].Page3[0].Imię[0]', other_parent['first_name']))
fields.append((u'topmostSubform[0].Page3[0].Nazwisko[0]', other_parent['last_name']))

# Czy drugi rodzic pracuje?
try:
    t = other_parent['employer']
except KeyError:
    t = None
fields.append((u'topmostSubform[0].Page3[0].WybórTAKNIE[0]',
               FDFTrue if t else FDFFalse))

# Czy drugi rodzic pracuje w trybie zmianowym?
f = u'topmostSubform[0].Page3[0].WybórTAKNIE5[0]'
if t is None:
    fields.append((f, FDFOff))
else:
    try:
        t = other_parent['shift_work']
    except KeyError:
        t = False
    fields.append((f, FDFTrue if t else FDFFalse))

# Czy drugi rodzic otrzymał zasiłek opiekuńczy?
fields.extend(other_parent_took_care(other_parent))

# TODO: Wypisanie informacji o małżonku lub innym członku rodziny

####
fields.append((u'topmostSubform[0].Page4[0].Numerrachunku[0]', this_parent['bank_account']))
fields.append((u'topmostSubform[0].Page4[0].Data[0]', opt_date.strftime("%d%m%Y")))

fdf = forge_fdf("", fields, [], [], [])
fdf_file = open(opt_outfile, "wb")
fdf_file.write(fdf)
fdf_file.close()
