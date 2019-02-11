# coding: iso8859-2
#
# A module for handling PESEL numbers.
# Copyright (C) 2006  Marcin Rzepniewski
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

'''Moduł do sprawdzania numeru PESEL oraz jego autorskiej modyfikacji IDENT
IDENT może być PESELem lub numerem stworzonym z:
- "U", daty urodzenia i inicjałów (naz, im) np. U19390901KJ
- "N", daty nadania numeru, płci i kolejnego numeru, np. N20060706M1

'''

import datetime
from calendar import leapdays
import re
import string

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

def pesel_k(nrid):
    '''Podaje czy PESEL (bez sprawdzania poprawności) może należeć do kobiety'''
    return (int(nrid[9])%2==0)

def pesel_data(nrid):
    '''Podaje datę urodzenia na podstawie PESELu o ile jest poprawny'''
    if pesel_ok(nrid):
        d,m,r=int(nrid[4:6]),int(nrid[2:4]),int(nrid[0:2])
        r,m=int((m>80)*1800+(m<80)*(1900+(m/20)*100)+r),int(m%20)
        if m in range(1,13):
            return datetime.date(r,m,d)
        else:
          raise PeselError('Blad 3 lub 4 cyfry!')
    else:
        raise PeselError('Blad numeru PESEL')

def ident_type(nrid):
    '''Podaje typ IDENTu znak P,U,N lub X dla nie pasujących lub błędnych.'''
    if re.match('^\d{11}$',nrid):
        if pesel_ok(nrid):
            return "P"
        else:
            return "X"
    elif re.match('^U\d{8}[A-Z]{2}$',nrid):
        return "U"
    elif re.match('^N\d{8}[MK]\d$',nrid):
        return "N"
    else:
        return "X"

def ident_ok(nrid):
    '''Określa poprawność numeru PESEL lub pozostałych IDENT'''
    return (ident_type(nrid)!="X")

def ident_data(nrid):
    '''Podaje datę urodzenia na podstawie IDENTu o ile jest poprawny
    (lub None dla poprawnych typu "N")'''
    typ=ident_type(nrid)
    if typ=="P":
        return pesel_data(nrid)
    elif typ=="N":
        return None
    elif typ=="U":
        d,m,r=int(nrid[7:9]),int(nrid[5:7]),int(nrid[1:5])
        if m in range(1,13):
            return datetime.date(r,m,d)
        else:
          raise PeselError('Blad cyfry miesiaca w IDENT typu U!')
    else:
        raise PeselError('Blad numeru IDENT')

def pesel2ident(nrid,nazwisko,imie):
    '''Tworzy IDENT typu U na podstawie PESEL i inicjałów.'''
    typ=ident_type(nrid)
    if typ=="P":
        d=pesel_data(nrid).strftime("%Y%m%d")
        return string.upper(string.join(['U',d,nazwisko[0],imie[0]],''))
    elif typ=="U":
        return string.upper(string.join([nrid[:9],nazwisko[0],imie[0]],''))
    else:
        return None

def wiek(data,LMDT=False,dzis=None):
    '''Podaje wiek osoby, której datę urodzin podano w pierwszym parametrze
    parametr "LMDT" prosi o zwrot typu (5,'M') "pięć miesięcy" (domyślnie podaje
    tylko wiek "rocznikowy" w latach), parametr "dzis" pozwala podać inny niż
    aktualny dzień odniesienia.'''
    if dzis==None:
        dzis=datetime.date.today()
    if LMDT:
        d=(dzis-data).days
        dp=leapdays(data.year,dzis.year)
        l=(d-dp)/365
        if l>0:
            return l,'L'
        else:
            d=d-dp-365*l
            m=d/30
            if m>0:
                return m,'M'
            else:
                d=d-30*m
                t=d/7
                if t>0:
                    return t,'T'
                else:
                    return d,'D'
    else:
        return dzis.year-data.year

class Pesel:
    '''obiekt inicjowany jednym parametrem - nr PESEL
    Udostępnia zmienne i metody do odczytywania różnych danych z PESELu'''

    def __init__(self,nrid):
        if ident_type(nrid)=="P":
            self.nrid=nrid
            self.data=pesel_data(nrid)
            if pesel_k(nrid):
                self.plec="K"
            else:
                self.plec="M"
        else:
            self.nrid=self.data=self.plec=None

    def __str__(self):
        return self.nrid

class Ident:
    '''obiekt inicjowany jednym parametrem - nr PESEL lub inny IDENT
    Udostępnia zmienne i metody do odczytywania różnych danych z numeru'''

    def __init__(self,nrid):
        self.typ=ident_type(nrid)
        if self.typ!="X":
            self.nrid=nrid
            self.data=ident_data(nrid)
            if self.typ=="P":
                if pesel_k(nrid):
                    self.plec="K"
                else:
                    self.plec="M"
            else:
                self.plec=None
        else:
            self.uident=self.nrid=self.data=self.plec=None

    def __str__(self):
        return self.nrid

    def uident(self,nazwisko,imie):
        if self.typ in 'PU':
            return pesel2ident(self.nrid,nazwisko,imie)
        else:
            return None
