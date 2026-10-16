import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButtonRequestUser
import requests, sqlite3, re, time, json, threading, html as _html
from datetime import datetime, timedelta, timezone
import os, random, string, io
import base64

_IST = timezone(timedelta(hours=5, minutes=30))
def _now_ist(): return datetime.now(_IST).strftime("%d %b %Y %I:%M %p")

def _safe_err(e):
    """Exception ko HTML-safe string mein convert karo"""
    return str(e).replace('<','&lt;').replace('>','&gt;')

def _strip_tg_emoji(text):
    """<tg-emoji ...>fallback</tg-emoji> → fallback (plain emoji only)"""
    return re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)

def _safe_send(chat_id, text, **kwargs):
    """send_message with auto-fallback: strips tg-emoji if ENTITY_TEXT_INVALID."""
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as _e:
        if 'entity_text_invalid' in str(_e).lower():
            try:
                return bot.send_message(chat_id, _strip_tg_emoji(text), **kwargs)
            except Exception as _e2:
                print(f"[SAFE_SEND] fallback failed: {_e2}")
        else:
            raise

def _send_react(chat_id, text, big=True, **kwargs):
    FREE_REACTIONS = ["👍","❤️","🔥","🥰","👏","😁","🎉","🤩","🙏","👌","😍","❤️‍🔥","💯","⚡","🏆","😎"]
    try:
        sent = bot.send_message(chat_id, text, **kwargs)
        try:
            random_emoji = random.choice(FREE_REACTIONS)
            bot.set_message_reaction(
                sent.chat.id,
                sent.message_id,
                [telebot.types.ReactionTypeEmoji(random_emoji)],
                is_big=big
            )
        except Exception as re_err:
            print(f"[REACTION ERROR] {re_err}")
        return sent
    except Exception as e:
        print(f"[SEND_REACT] {e}")

BOT_TOKEN = "8841883754:AAFS26ZBRpBYotpOI6-tQwoWZK18TWv3lsk"
OWNER_ID = 8691519315
FREE_CREDITS = 9999999
BOT_CLONE_REFERRAL_REQUIRED = 0
LOG_CHANNEL_ID   = -1003847701094
TOKEN_LOG_GROUP  = 5917496283

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ── Auto-fallback patch: strip <tg-emoji> on ENTITY_TEXT_INVALID ──
_orig_send_message = bot.send_message
def _patched_send_message(chat_id, text, **kwargs):
    try:
        return _orig_send_message(chat_id, text, **kwargs)
    except Exception as _e:
        if 'entity_text_invalid' in str(_e).lower():
            try:
                _clean = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', str(text))
                return _orig_send_message(chat_id, _clean, **kwargs)
            except Exception as _e2:
                print(f"[PATCH_SEND] fallback failed: {_e2}")
        raise
bot.send_message = _patched_send_message

_orig_reply_to = bot.reply_to
def _patched_reply_to(message, text, **kwargs):
    try:
        return _orig_reply_to(message, text, **kwargs)
    except Exception as _e:
        if 'entity_text_invalid' in str(_e).lower():
            try:
                _clean = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', str(text))
                return _orig_reply_to(message, _clean, **kwargs)
            except Exception:
                try:
                    return _orig_send_message(message.chat.id, _clean, **kwargs)
                except Exception as _e3:
                    print(f"[PATCH_REPLY] all fallbacks failed: {_e3}")
        raise
bot.reply_to = _patched_reply_to

_BOT_USERNAME_CACHE = None
_BOT_ID_CACHE = None
def _get_bot_username():
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE: return _BOT_USERNAME_CACHE
    try: _BOT_USERNAME_CACHE = bot.get_me().username
    except: _BOT_USERNAME_CACHE = "felix_modz1"
    return _BOT_USERNAME_CACHE

def _get_bot_id():
    global _BOT_ID_CACHE
    if _BOT_ID_CACHE: return _BOT_ID_CACHE
    try: _BOT_ID_CACHE = bot.get_me().id
    except: _BOT_ID_CACHE = int(BOT_TOKEN.split(':')[0])
    return _BOT_ID_CACHE

_F = "━━━━━━━━━━━━━━━━━━━━━━━━━━"

class _StyledKB(KeyboardButton):
    def __init__(self, text, style=None, icon_custom_emoji_id=None, **kwargs):
        super().__init__(text, **kwargs)
        self.__style = style
        self.__icon_emoji = icon_custom_emoji_id
    def to_dict(self):
        d = super().to_dict()
        if self.__style: d['style'] = self.__style
        if self.__icon_emoji: d['icon_custom_emoji_id'] = self.__icon_emoji
        return d

class _StyledIKB(InlineKeyboardButton):
    def __init__(self, text, style=None, icon_custom_emoji_id=None, **kwargs):
        super().__init__(text, **kwargs)
        self.__style = 'success' if style == 'active' else style
        self.__icon_emoji = icon_custom_emoji_id
    def to_dict(self):
        d = super().to_dict()
        try:
            if self.__style: d['style'] = self.__style
        except: pass
        try:
            if self.__icon_emoji: d['icon_custom_emoji_id'] = self.__icon_emoji
        except: pass
        return d

def _KB(text, style=None, icon_custom_emoji_id=None, **kwargs):
    if style == 'active': style = 'success'
    try: return _StyledKB(text, style=style, icon_custom_emoji_id=icon_custom_emoji_id, **kwargs)
    except:
        try: return KeyboardButton(text, **kwargs)
        except: return KeyboardButton(text)

def _IKB(text, style=None, icon_custom_emoji_id=None, **kwargs):
    try: return _StyledIKB(text, style=style, icon_custom_emoji_id=icon_custom_emoji_id, **kwargs)
    except:
        try: return InlineKeyboardButton(text, **kwargs)
        except:
            safe_kw = {k:v for k,v in kwargs.items() if k in ('callback_data','url','switch_inline_query','switch_inline_query_current_chat')}
            return InlineKeyboardButton(text, **safe_kw) if safe_kw else InlineKeyboardButton(text, callback_data='noop')

S_NONE='none'; S_NUM='number'; S_USER='username'; S_TID='tgid'
S_ADH='aadhar'; S_INSTA='instagram'; S_FF='freefire'; S_FFL='freefire_like'
S_VEH='vehicle'; S_CLONE='bot_clone'; S_BOMB='bomber'; S_FF_LIKE_UID='ff_like_uid'

user_state = {}
bomber_jobs = {}

def pbar(pct):
    pct = max(0, min(100, int(pct)))
    total = 13
    filled = int(round(pct / 100 * total))
    empty = total - filled
    bar = '█' * filled + '░' * empty
    return f"{bar}  {pct}%"

_ANIM_PE = "<tg-emoji emoji-id='6255767342916045646'>⚡</tg-emoji>"
_ANIM_LABELS = {
    'number':   'ꜰᴇᴛᴄʜɪɴɢ ɴᴜᴍʙᴇʀ ɪɴꜰᴏ',
    'username': 'ꜰᴇᴛᴄʜɪɴɢ ᴜꜱᴇʀɴᴀᴍᴇ ɪɴꜰᴏ',
    'tgid':     'ꜰᴇᴛᴄʜɪɴɢ ᴛɢ ɪᴅ ɪɴꜰᴏ',
    'aadhar':   'ꜰᴇᴛᴄʜɪɴɢ ᴀᴀᴅʜᴀʀ ɪɴꜰᴏ',
    'instagram':'ꜰᴇᴛᴄʜɪɴɢ ɪɴꜱᴛᴀ ɪɴꜰᴏ',
    'freefire': 'ꜰᴇᴛᴄʜɪɴɢ ꜰʀᴇᴇꜰɪʀᴇ ɪɴꜰᴏ',
    'like':     'ꜱᴇɴᴅɪɴɢ ʟɪᴋᴇꜱ',
    'viplike':  'ꜱᴇɴᴅɪɴɢ ᴠɪᴩ ʟɪᴋᴇꜱ',
    'bomber':   'ʟᴀᴜɴᴄʜɪɴɢ ʙᴏᴍʙᴇʀ',
    'vehicle':  'ꜰᴇᴛᴄʜɪɴɢ ᴠᴇʜɪᴄʟᴇ ɪɴꜰᴏ',
    'usernum':  'ꜰᴇᴛᴄʜɪɴɢ ᴜꜱᴇʀ ɪɴꜰᴏ',
}

def _start_anim(chat_id, msg_id, label_key):
    final_label = _ANIM_LABELS.get(label_key, 'ꜰᴇᴛᴄʜɪɴɢ')
    stop_flag = [False]
    def _run():
        for pct in [0, 8, 15]:
            if stop_flag[0]: return
            try:
                bot.edit_message_text(f"<blockquote>{pbar(pct)}\nʙʏᴩᴀꜱꜱɪɴɢ ꜱʏꜱᴛᴇᴍ {_ANIM_PE}</blockquote>", chat_id, msg_id, parse_mode='HTML')
            except: pass
            time.sleep(0.35)
        for pct in [22, 35, 48, 55]:
            if stop_flag[0]: return
            try:
                bot.edit_message_text(f"<blockquote>{pbar(pct)}\nꜱᴇᴀʀᴄʜɪɴɢ {_ANIM_PE}</blockquote>", chat_id, msg_id, parse_mode='HTML')
            except: pass
            time.sleep(0.4)
        _pcts = [60, 68, 75, 82, 88, 92, 95]
        _i = 0
        while not stop_flag[0] and _i < 33:
            pct = _pcts[min(_i, len(_pcts)-1)]
            try:
                bot.edit_message_text(f"<blockquote>{pbar(pct)}\n{final_label} {_ANIM_PE}</blockquote>", chat_id, msg_id, parse_mode='HTML')
            except: pass
            _i += 1
            time.sleep(0.9)
    threading.Thread(target=_run, daemon=True).start()
    return stop_flag

# ── LIKE APIs (Cooldowns & Limits Disabled) ──
LIKE_API_0 = "https://simran-like-r-bot-api.vercel.app/like"
LIKE_API_1 = "https://freefireautolikeservice.vercel.app/like"
LIKE_API_2 = "https://ff-like-api-azure.vercel.app/like"
LIKE_API_3 = "https://sexty-autolikes.vercel.app/like"
LIKE_API_4 = "https://verma-like-api.vercel.app/like"
LIKE_API_5 = "https://druu-likes-15-day.vercel.app/like"

VALID_REGIONS = ["ind","bd","id","th","vn","br","ru","my","sg","ph"]
REGION_NAMES  = {
    "ind":"🇮🇳 INDIA","bd":"🇧🇩 BANGLADESH","id":"🇮🇩 INDONESIA",
    "th":"🇹🇭 THAILAND","vn":"🇻🇳 VIETNAM","br":"🇧🇷 BRAZIL",
    "ru":"🇷🇺 RUSSIA","my":"🇲🇾 MALAYSIA","sg":"🇸🇬 SINGAPORE","ph":"🇵🇭 PHILIPPINES"
}

def _like_check_cooldown(user_id, uid):
    return True, 0, None

def _like_update_cooldown(user_id, uid, region):
    pass

def _like_check_ratelimit(user_id):
    return True

def _like_update_ratelimit(user_id):
    pass

def _like_remaining_daily(user_id):
    return "∞"

# ── DATABASE SETUP ──
_db_lock = threading.Lock()
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BOT_ID = BOT_TOKEN.split(':')[0]
_DB_FILE = os.path.join(_SCRIPT_DIR, f"bot_{_BOT_ID}.db")

conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.commit()

class _SafeCursor:
    def __init__(self, connection):
        self._conn = connection
        self._lock = _db_lock
    def execute(self, sql, params=()):
        with self._lock:
            self._cur = self._conn.cursor()
            self._cur.execute(sql, params)
            return self
    def executescript(self, sql):
        with self._lock:
            self._cur = self._conn.cursor()
            self._cur.executescript(sql)
            return self
    def fetchone(self):
        return self._cur.fetchone() if hasattr(self,'_cur') else None
    def fetchall(self):
        return self._cur.fetchall() if hasattr(self,'_cur') else []
    @property
    def rowcount(self):
        return self._cur.rowcount if hasattr(self,'_cur') else 0

c = _SafeCursor(conn)
_orig_conn = conn

def _safe_commit():
    with _db_lock:
        try: _orig_conn.commit()
        except: pass

class _ConnWrapper:
    def __init__(self, c_obj): self._c = c_obj
    def __getattr__(self, name):
        if name == 'commit': return _safe_commit
        return getattr(self._c, name)

conn = _ConnWrapper(_orig_conn)
c.executescript('''
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
  join_date TEXT, referrer INTEGER, credits INTEGER DEFAULT 999999,
  is_blocked INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 1,
  premium_until TEXT, joined_channel INTEGER DEFAULT 1, first_time INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS search_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, search_type TEXT,
  query TEXT, search_date TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS groups(
  group_id INTEGER PRIMARY KEY, group_title TEXT, added_date TEXT, added_by INTEGER,
  credits INTEGER DEFAULT 999999, unlimited INTEGER DEFAULT 1,
  is_blocked INTEGER DEFAULT 0, searches INTEGER DEFAULT 0, is_muted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS welcome_settings(
  id INTEGER PRIMARY KEY CHECK(id=1), welcome_emoji TEXT DEFAULT '👋',
  welcome_caption TEXT DEFAULT 'Welcome!',
  welcome_image TEXT, welcome_video TEXT, bot_dp TEXT, first_time_sticker TEXT);
CREATE TABLE IF NOT EXISTS feature_toggles(
  id INTEGER PRIMARY KEY AUTOINCREMENT, feature_name TEXT UNIQUE,
  is_enabled INTEGER DEFAULT 1, updated_by INTEGER, updated_date TEXT);
CREATE TABLE IF NOT EXISTS admins(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
  added_by INTEGER, added_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS api_keys(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_name TEXT UNIQUE, api_url TEXT, api_key TEXT,
  is_active INTEGER DEFAULT 1, added_by INTEGER, added_date TEXT);
''')
conn.commit()

c.execute("INSERT OR IGNORE INTO welcome_settings(id) VALUES(1)")
c.execute("INSERT OR IGNORE INTO admins(user_id,added_by,added_date) VALUES(?,?,?)",
          (OWNER_ID, OWNER_ID, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
for f in ['number','username','aadhar','instagram','freefire','tgid','freefire_like','vehicle','bomber']:
    c.execute("INSERT OR IGNORE INTO feature_toggles(feature_name,is_enabled) VALUES(?,1)", (f,))
conn.commit()

_IS_CLONE = False
_IS_CLASSIC = False
_MAIN_OWNER = OWNER_ID

_PREM_EMOJI = "<tg-emoji emoji-id='5465277838993141300'>💎</tg-emoji>"
def _CL_TOP(): return _PREM_EMOJI*10
def _CL_BOT(): return _PREM_EMOJI*10
def _SEP():    return _F
def _orig_credit():
    _L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"
    _SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    return f"{_L*10}\n{_SM} @Felix_Bhai {_CK}\n{_L*10}"
def _credit(): return _orig_credit()

# ── ALL PERMISSIONS & CREDITS BYPASSED ──
def is_admin(uid):
    return True  # Sabhi permissions open kar di gayi hain (ya sirf OWNER_ID rakhne ke liye `return uid == OWNER_ID` karein)

def get_user(uid):
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return c.fetchone()

def add_user(uid, uname, fname, ref=None):
    d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,referrer,credits,first_time) VALUES(?,?,?,?,?,?,1)",
                  (uid, uname, fname, d, ref, FREE_CREDITS))
        conn.commit()
        return True
    except: return False

def update_user(uid, **kw):
    for k, v in kw.items():
        c.execute(f"UPDATE users SET {k}=? WHERE user_id=?", (v, uid))
    conn.commit()

def get_credits(uid):
    return "∞"

def deduct_credit(uid, cost=1, context='bot'):
    return True

def refund_credit(uid, cost=1):
    pass

def is_feature_enabled(fn):
    return True

def check_channel(uid):
    return True

def get_channels_keyboard(uid=None):
    return None

def check_blocked_and_reply(uid):
    return False

def _clone_group_guard(msg):
    return False

def feat_ok(uid, fn, chat_id=None):
    return True

def add_group_to_db(gid, title):
    c.execute("INSERT OR IGNORE INTO groups(group_id,group_title,added_date,added_by,credits,unlimited,is_blocked,searches,is_muted) VALUES(?,?,?,?,999999,1,0,0,0)",
              (gid, title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), OWNER_ID))
    conn.commit()

def log_search(uid, uname, tgname, stype, query, photo=None):
    try:
        bn = _get_bot_username()
        udisp = f"@{tgname}" if tgname else "No Username"
        txt = (f"<blockquote>╭━━━━━━━━━━━━━━━✦\n│ 📊 <b>𝗦𝗘𝗔𝗥𝗖𝗛 𝗟𝗢𝗚</b>\n╰━━━━━━━━━━━━━━━✦\n\n"
               f"👤 {uname}\n🆔 {uid}\n🔗 {udisp}\n\n"
               f"{_F}\n🔍 <b>{stype.upper()}</b>\n📝 <code>{query}</code>\n{_F}\n"
               f"🤖 @{bn}\n📅 {_now_ist()}\n⚡ @Felix_modz1</blockquote>")
        bot.send_message(LOG_CHANNEL_ID, txt, parse_mode='HTML')
    except: pass

def get_welcome_settings():
    c.execute("SELECT * FROM welcome_settings WHERE id=1")
    return c.fetchone()

def format_welcome(uid, fname, credits="∞", username=""):
    fname = _html.escape(fname)
    def te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    LOOP10 = te("5465629669829128119")*10
    return (
        f"<blockquote>"
        f"{te('6284979958116786100')} ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ʙᴏᴛ\n"
        f"{LOOP10}\n"
        f"{te('4956461073550017373')}{te('4958469026595472714')} ʜᴇʟʟᴏ 殺┋ <a href='tg://user?id={uid}'><b>{fname}</b></a> !!\n\n"
        f"{te('5422827632074962213')} ꜰʀᴇᴇ ᴜɴʟɪᴍɪᴛᴇᴅ ᴏꜱɪɴᴛ ɪɴꜰᴏ ʙᴏᴛ!\n\n"
        f"{te('4956719506027185156')} ᴀᴄᴄᴇꜱꜱ : <b>ᴜɴʟɪᴍɪᴛᴇᴅ (ꜰʀᴇᴇ)</b>\n"
        f"{te('6147422674000808494')} /help — ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ᴅᴇᴋʜᴏ\n\n"
        f"{LOOP10}\n"
        f"{te('4958900559139570572')} ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1 {te('6147565374289220368')}</blockquote>"
    )

# ── API HELPERS ──
def _K(key_name):
    _defaults = {
        "key_sh4daw":"SH4DAW-D4DY","key_abdulstore":"ak_59eca148e4484ccb50e8575645c32ee1",
        "key_ff_info":"SH4DAW-D4DY","key_rlx_bomber":"rlxcoder",
        "key_numinfo":"SH4DAW-D4DY","key_aadhar":"SH4DAW-D4DY","key_instagram":"SH4DAW-D4DY",
        "key_vehicle":"SH4DAW-D4DY","key_username":"SH4DAW-D4DY"
    }
    return _defaults.get(key_name, "")

def api_number(num):
    try:
        r0 = requests.get(f"https://simran-num-info-api.vercel.app/api?number={num}&format=2", timeout=12)
        if r0.status_code == 200:
            d0 = r0.json()
            if d0 and (d0.get('success') or d0.get('status') or d0.get('data') or d0.get('name')):
                d0['success'] = True; d0['_api_source'] = 'simran_num'; return d0
    except: pass
    try:
        r0b = requests.get(f"https://numm-info-sable.vercel.app/?key=sojaa&query={num}", timeout=12)
        if r0b.status_code == 200:
            d0b = r0b.json()
            if d0b and (d0b.get('success') or d0b.get('status') or d0b.get('data') or d0b.get('0')):
                d0b['success'] = True; d0b['_api_source'] = 'numm_sable'; return d0b
    except: pass
    try:
        r1 = requests.get(f"https://r-bot-number-to-info-api.vercel.app/api?number={num}", timeout=12)
        if r1.status_code == 200:
            d1 = r1.json()
            if isinstance(d1.get('results'), list) or d1.get('success'):
                d1['success'] = True; d1['_api_source'] = 'rbot'; return d1
    except: pass
    try:
        r2 = requests.get(f"https://numbeer-info.vercel.app/?numbere={num}&key={_K('key_numinfo')}", timeout=10)
        if r2.status_code == 200:
            d2 = r2.json()
            if d2.get('success'):
                d2['_api_source'] = 'numbeer'; return d2
    except: pass
    return None

def _fetch_pfp_by_id(uid_str):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos",
                         params={"user_id": uid_str, "limit": 1}, timeout=8)
        if r.status_code == 200:
            photos = r.json().get('result', {}).get('photos', [])
            if photos and photos[0]:
                fid = photos[0][-1].get('file_id', '')
                if fid:
                    r2 = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                                      params={"file_id": fid}, timeout=8)
                    if r2.status_code == 200:
                        fpath = r2.json().get('result', {}).get('file_path', '')
                        if fpath:
                            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
    except: pass
    return None

def _fetch_tg_user_direct(uid_str):
    result = {}
    _raw = str(uid_str).strip()
    if _raw.startswith('@') or (not _raw.lstrip('-').isdigit()):
        uid_str = '@' + _raw.replace('@','').strip()
        _for_photo = None
    else:
        uid_str = re.sub(r'\D','',_raw)
        _for_photo = uid_str
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                         params={"chat_id": uid_str}, timeout=10)
        if r.status_code == 200:
            d = r.json().get('result', {})
            result['first_name'] = d.get('first_name','') or ''
            result['last_name']  = d.get('last_name','') or ''
            result['username']   = d.get('username','') or ''
            result['bio']        = d.get('bio','') or ''
            result['tg_id']      = str(d.get('id', uid_str))
            if _for_photo is None and d.get('id'):
                _for_photo = str(d['id'])
    except: pass
    if _for_photo:
        result['pfp_url'] = _fetch_pfp_by_id(_for_photo)
    return result

def _call_un_api(username):
    cl = username.replace('@','').strip()
    flat = {}; pic = None; tg_id_found = ''
    try:
        r = requests.get(f"https://user-to-num-info-zcpe.onrender.com/username/{cl}", timeout=20)
        if r.status_code == 200:
            d_un = r.json()
            _d_block = d_un.get('data') or {}
            _p1_block = _d_block.get('p1') or {} if isinstance(_d_block, dict) else {}
            _records = _p1_block.get('records') or [] if isinstance(_p1_block, dict) else []
            _id = str(d_un.get('target_id') or d_un.get('telegram_id') or d_un.get('userid') or '').strip()
            if _id and _id.lstrip('-').isdigit(): tg_id_found = _id
            _ph = ''; _country = 'India'; _cc = '+91'
            if _records and isinstance(_records, list):
                _rec0 = _records[0]
                _ph_raw = str(_rec0.get('number', '') or '').strip()
                _country = str(_rec0.get('country', 'India') or 'India').strip()
                _cc = str(_rec0.get('country_code', '+91') or '+91').strip()
                _cc_d = _cc.replace('+','').strip()
                _ph = _ph_raw[len(_cc_d):] if (_ph_raw and _cc_d and _ph_raw.startswith(_cc_d) and len(_ph_raw)-len(_cc_d)>=7) else _ph_raw
                if not tg_id_found:
                    _uid_rec = str(_rec0.get('userid', '') or '').strip()
                    if _uid_rec.lstrip('-').isdigit(): tg_id_found = _uid_rec
            else:
                _ph = str(d_un.get('number', '') or d_un.get('phone', '') or '').strip()
            flat = {'telegram_id': tg_id_found, 'username': cl, 'success': True}
            if _ph and len(_ph) >= 7:
                flat['phone'] = _ph; flat['number'] = _ph; flat['country'] = _country; flat['country_code'] = _cc
    except: pass
    d_gc = _fetch_tg_user_direct(f"@{cl}")
    if d_gc:
        if d_gc.get('tg_id') and not tg_id_found:
            tg_id_found = d_gc['tg_id']; flat['telegram_id'] = tg_id_found
        for k in ('first_name','last_name','bio','username'):
            if d_gc.get(k): flat[k] = d_gc[k]
    if tg_id_found: pic = _fetch_pfp_by_id(tg_id_found)
    return flat, pic

def _call_uid_api(uid_str):
    phone = ''; country = 'India'; cc = '+91'; ud = {}
    try:
        r = requests.get(f"https://user-to-num-info-zcpe.onrender.com/userid={uid_str}", timeout=20)
        if r.status_code == 200:
            d_new = r.json()
            _top_data = d_new.get('data') or {}
            _p1_block = _top_data.get('p1') if isinstance(_top_data, dict) else {}
            _zcpe_recs = _p1_block.get('records', []) if isinstance(_p1_block, dict) else []
            if _zcpe_recs:
                _rec0 = _zcpe_recs[0]
                _ph = str(_rec0.get('number', '') or '').strip()
                country = str(_rec0.get('country', 'India') or 'India').strip()
                cc = str(_rec0.get('country_code', '+91') or '+91').strip()
                if _ph and _ph != uid_str and len(_ph) >= 7:
                    _cc_d = cc.replace('+','').strip()
                    phone = _ph[len(_cc_d):] if (_cc_d and _ph.startswith(_cc_d) and len(_ph)-len(_cc_d)>=7) else _ph
                ud = {'telegram_id': uid_str, 'success': True, 'number': phone, 'phone': phone, 'country': country, 'country_code': cc}
    except: pass
    if not phone:
        try:
            r2 = requests.get(f"https://tg-id-2-numb-and-tg-info-v3.vercel.app/api/tg?info={uid_str}", timeout=15)
            if r2.status_code == 200:
                d2 = r2.json()
                _ph = str(d2.get('number', '') or '').strip()
                if _ph and _ph != uid_str and len(_ph) >= 7:
                    phone = _ph
                ud = {'telegram_id': uid_str, 'success': True, 'number': phone, 'phone': phone}
        except: pass
    pic = _fetch_pfp_by_id(uid_str)
    return ud, phone or 'N/A', country, cc, pic

def api_full_user(query):
    query = str(query).strip()
    is_uid = query.lstrip('-').isdigit()
    cl = query.replace('@','').strip()
    tg = _fetch_tg_user_direct(re.sub(r'\D','',query) if is_uid else query)
    if is_uid:
        uid_data, phone, country, cc, pic1 = _call_uid_api(re.sub(r'\D','',query))
        flat = {}
    else:
        flat, pic1 = _call_un_api(cl)
        uid_data = {}; phone = flat.get('phone','N/A'); country = flat.get('country','India'); cc = flat.get('country_code','+91')
        if (not phone or phone == 'N/A') and tg.get('tg_id') and tg['tg_id'].lstrip('-').isdigit():
            uid_data, phone, country, cc, _ = _call_uid_api(tg['tg_id'])
    ud = dict(uid_data)
    ud.update(flat)
    for k in ('first_name','last_name','username','bio'):
        if tg.get(k): ud[k] = tg[k]
    tg_id = tg.get('tg_id') or flat.get('telegram_id') or (re.sub(r'\D','',query) if is_uid else '')
    if tg_id: ud['telegram_id'] = tg_id
    return {
        'success': True, 'phone': phone, 'telegram_id': tg_id, 'target_id': tg_id,
        'target_username': ud.get('username', cl), 'country': country, 'country_code': cc,
        'profile_pic': tg.get('pfp_url') or pic1, 'data': ud
    }

def api_aadhar(an):
    try:
        an = re.sub(r'\D','',str(an))
        if len(an) != 12: return None
        r = requests.get(f"https://adhar-to-info.vercel.app/?key={_K('key_aadhar')}&aadhar={an}", timeout=15)
        if r.status_code == 200:
            d = r.json()
            if d.get('status') and d.get('results',{}).get('success'):
                res = d.get('results',{})
                return {'success':True,'aadhaar':res.get('aadhaar',an),'total_records':res.get('total_records',0),'data':res.get('data',[])}
    except: pass
    return None

def api_instagram(un):
    try:
        u = un.replace('@','').lower()
        r = requests.get(f"https://insta-info-eta.vercel.app/?username={u}&key={_K('key_instagram')}", timeout=15)
        if r.status_code == 200:
            d = r.json()
            if d.get('username'):
                pic = d.get('pic',''); pic = pic if pic and pic.startswith('http') else None
                return {'success':True,'id':d.get('id','N/A'),'username':d.get('username',u),
                        'name':d.get('name','N/A'),'bio':d.get('bio',''),
                        'verified':d.get('verified',False),'private':d.get('private',False),
                        'pic':pic,'followers':d.get('followers',0),
                        'following':d.get('following',0),'posts':d.get('posts',0)}
    except: pass
    return None

def api_ff(uid_ff):
    try:
        uid_ff = re.sub(r'\D','',str(uid_ff))
        r = requests.get(f"https://sextyinfo.vercel.app/player-info?uid={uid_ff}", timeout=30)
        if r.status_code != 200: return None
        d = r.json()
        if not d or not d.get('basicInfo'): return None
        bi = d.get('basicInfo',{}); si = d.get('socialInfo',{}); pet = d.get('petInfo',{})
        clan = d.get('clanBasicInfo',{}); cap = d.get('captainBasicInfo',{}); cr = d.get('creditScoreInfo',{})
        def ts2str(ts):
            try: return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y %I:%M %p")
            except: return str(ts)
        BR_RANKS = {0:'Bronze',100:'Bronze',200:'Silver',300:'Gold',400:'Platinum',500:'Diamond',600:'Heroic',700:'Grandmaster',800:'Challenger'}
        def rank_name(pts):
            try: return BR_RANKS.get(int(pts)//100*100, f"Rank {pts}")
            except: return 'N/A'
        return {
            'success':True, 'uid':bi.get('accountId',uid_ff), 'nickname':bi.get('nickname','N/A'),
            'region':bi.get('region','N/A'), 'level':bi.get('level',0), 'exp':bi.get('exp',0),
            'liked':bi.get('liked',0), 'badges':bi.get('badgeCnt',0),
            'rank_pts':bi.get('rankingPoints',0), 'cs_rank_pts':bi.get('csRankingPoints',0),
            'rank_name':rank_name(bi.get('rankingPoints',0)), 'cs_rank_name':rank_name(bi.get('csRankingPoints',0)),
            'max_br_name':rank_name(bi.get('maxRank',0)), 'max_cs_name':rank_name(bi.get('csMaxRank',0)),
            'signature':si.get('signature','—') or '—', 'language':si.get('language','N/A'),
            'mode':si.get('modePrefer','BR'),
            'create_at':ts2str(bi.get('createAt','')) if bi.get('createAt') else 'N/A',
            'last_login':ts2str(bi.get('lastLoginAt','')) if bi.get('lastLoginAt') else 'N/A',
            'ban_status':'NOT BANNED', 'credit_score':cr.get('creditScore',0),
            'version':bi.get('releaseVersion','N/A'),
            'pet_id':pet.get('id',0), 'pet_level':pet.get('level',0), 'pet_exp':pet.get('exp',0),
            'clan_name':clan.get('clanName','No Clan'), 'clan_id':clan.get('clanId',''),
            'clan_level':clan.get('clanLevel',0), 'clan_members':clan.get('memberNum',0),
            'clan_leader':cap.get('nickname',''),
        }
    except: return None

def api_vehicle(rc):
    try:
        r = requests.get(f"https://vehicle-rc-to-num.vercel.app/?rc={rc}&key={_K('key_vehicle')}", timeout=15)
        if r.status_code == 200:
            d = r.json()
            if d.get('success'):
                return {'success':True,'rc_number':rc,'owner_name':d.get('owner_name','N/A'),
                        'mobile_number':d.get('mobile_number','N/A'),'vehicle_model':d.get('vehicle_model','N/A'),
                        'registration_date':d.get('registration_date','N/A'),'fuel_type':d.get('fuel_type','N/A'),
                        'engine_number':d.get('engine_number','N/A'),'insurance_valid_till':d.get('insurance_valid_till','N/A')}
    except: pass
    return None

def do_ff_like_send(chat_id, msg_id, uid, region, user_id, fname):
    import concurrent.futures as _cfl
    region_display = REGION_NAMES.get(region.lower(), region.upper())
    def _call_url(url, params):
        try:
            r = requests.get(url, params=params, timeout=25)
            if r.status_code == 200: return r.json()
        except: pass
        return None
    with _cfl.ThreadPoolExecutor(max_workers=6) as ex:
        f0 = ex.submit(_call_url, LIKE_API_0, {"uid":uid,"server_name":region.lower()})
        fa = ex.submit(_call_url, LIKE_API_1, {"uid":uid,"server_name":region.lower()})
        fb = ex.submit(_call_url, LIKE_API_2, {"uid":uid,"server_name":region.lower()})
        fc = ex.submit(_call_url, LIKE_API_3, {"uid":uid,"server_name":region.upper()})
        fd = ex.submit(_call_url, LIKE_API_4, {"uid":uid,"region":region,"key":"UDIT"})
        fe = ex.submit(_call_url, LIKE_API_5, {"uid":uid,"server_name":region.lower()})
        api_results = [("1",fa.result()),("2",fb.result()),("3",fc.result()),("4",fd.result()),("5",fe.result()),("6",f0.result())]

    total_given = 0; api_lines = ""
    for label, data in api_results:
        if not data: continue
        status = data.get("status", 0)
        msg_txt = str(data.get("message", data.get("msg",""))).lower()
        if "already" in msg_txt or "max" in msg_txt or "limit" in msg_txt:
            api_lines += f"│ 🎮 ᴀᴩɪ {label}: ⚠️ Already Liked\n"
        elif status in [1,2,3]:
            lb2 = data.get("LikesbeforeCommand", data.get("likes_before",0))
            la2 = data.get("LikesafterCommand", data.get("likes_after",0))
            lg2 = data.get("LikesGivenByAPI", data.get("likes_given",1))
            total_given += int(lg2 or 0)
            api_lines += f"│ 🎮 ᴀᴩɪ {label}: 👑 {lb2} → {la2} (+{lg2})\n"
    if not api_lines: api_lines = "│ ❌ Koi API respond nahi ki\n"
    txt = (f"<blockquote>{_F}\n🎮 <b>ꜰꜰ ʟɪᴋᴇ ʀᴇꜱᴜʟᴛ</b>\n{_F}\n\n"
           f"🆔 UID : <code>{uid}</code>\n🌍 Region : {region_display}\n\n"
           f"╭─── 📊 ᴀᴩɪ ʀᴇꜱᴜʟᴛꜱ ───╮\n{api_lines}╰──────────────────╯\n\n"
           f"🎉 <b>TOTAL : +{total_given} LIKES !</b>\n{_F}\n{_credit()}</blockquote>")
    try: bot.edit_message_text(txt, chat_id, msg_id, parse_mode='HTML')
    except: bot.send_message(chat_id, txt, parse_mode='HTML')

# ── BOMBER ──
FLIX_BOMBER_API  = "https://bombar-api-2.vercel.app/all"
FLIX_BOMBER_STOP = "https://flix-bombar.onrender.com/stop"
RLX_BOMBER_API   = "https://rlxbomber.vercel.app/api/attack"

def _call_flix(num):
    try:
        r = requests.get(FLIX_BOMBER_API, params={"num":num}, timeout=35)
        if r.status_code == 200: return {"ok":True}
    except: pass
    return {"ok":False}

def _call_rlx(num):
    try:
        r = requests.get(RLX_BOMBER_API, params={"number":num,"key":"rlxcoder"}, timeout=35)
        if r.status_code == 200: return {"ok":True}
    except: pass
    return {"ok":False}

def run_bomber(uid, chat_id, number, msg_id):
    MAX = 600; start = time.time(); rounds = 0
    bomber_jobs[uid] = {'running':True, 'number':number}
    while bomber_jobs.get(uid,{}).get('running',False):
        el = time.time() - start
        if el >= MAX: break
        _call_flix(number); _call_rlx(number)
        rounds += 1
        pct = min(int((el/MAX)*100), 99)
        try:
            bot.edit_message_text(
                f"<blockquote>{_F}\n💣 <b>ʙᴏᴍʙɪɴɢ ɪɴ ᴩʀᴏɢʀᴇꜱꜱ...</b>\n{_F}\n\n"
                f"📱 Target: +91{number}\n🔄 Rounds: {rounds}\n{pbar(pct)}\n\n"
                f"🔴 Stop Bomber dabao band karne ke liye\n{_credit()}</blockquote>",
                chat_id, msg_id, parse_mode='HTML')
        except: pass
        time.sleep(20)
    try: requests.get(FLIX_BOMBER_STOP, params={"num":number}, timeout=8)
    except: pass
    bomber_jobs.pop(uid, None)
    try:
        bot.edit_message_text(f"<blockquote>💣 <b>ʙᴏᴍʙᴇʀ ꜱᴛᴏᴩᴩᴇᴅ</b>\n📱 Target: +91{number}\n🔄 Total Rounds: {rounds}\n{_credit()}</blockquote>", chat_id, msg_id, parse_mode='HTML')
    except: pass

# ── FORMATTERS (Without Credit Deductions/Prompts) ──
def _fmt_tg_user_short(res, query_display, now_str, credits_left=None):
    if not res or not res.get('success'):
        return f"<blockquote>{_F}\n🔍 <b>𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗜𝗡𝗙𝗢</b>\n{_F}\n\n❌ No Data Found\n🔍 <code>{query_display}</code>\n\n{_credit()}</blockquote>", None
    ud = res.get('data', {}) or {}
    tg_id = str(ud.get('telegram_id') or res.get('telegram_id') or '').strip()
    fn = str(ud.get('first_name','') or '').strip()
    ln = str(ud.get('last_name','') or '').strip()
    nm = f"{fn} {ln}".strip() or '—'
    un = str(ud.get('username') or res.get('target_username') or '').replace('@','').strip()
    un_display = f"@{un}" if un else query_display
    phone = str(res.get('phone','') or ud.get('phone','') or '').strip()
    if phone in ('N/A', tg_id): phone = ''
    country = str(res.get('country','India') or 'India').strip()
    cc = str(res.get('country_code','+91') or '+91').strip()
    num_display = f"+{cc.replace('+','')} {phone}" if phone else "🔒 Not Available"
    txt = (f"<blockquote>{_F}\n🔍 <b>𝗨𝗦𝗘𝗥 𝗜𝗡𝗙𝗢</b>\n{_F}\n\n"
           f"🍾 Name:- <b>{nm}</b>\n🌀 Username:- {un_display}\n✉️ TG ID:- <code>{tg_id or '—'}</code>\n\n"
           f"🌏 Country:- {country}\n⚜ Code:- {cc}\n📱 Number:- <b>{num_display}</b>\n\n"
           f"{_F}\n{_credit()}</blockquote>")
    return txt, None

def _fmt_tg_user(res, title_icon, title_text, query_display, now_str, credits_left=None):
    return _fmt_tg_user_short(res, query_display, now_str, credits_left)

def fmt_number(d, num, s=""):
    SEP = _F; REC_SEP = "──────────────────────"
    if not d or not d.get('success'):
        return f"<blockquote>{SEP}\n📱 <b>NUMBER INFO</b>\n{SEP}\n\n❌ No Data Found\n📱 <code>{num}</code>\n\n{_credit()}</blockquote>"
    recs = []
    if d.get('_api_source') == 'simran_num' and isinstance(d.get('data'), list):
        recs = d['data']
    elif d.get('_api_source') == 'rbot' and isinstance(d.get('results'), list):
        recs = d['results']
    else:
        recs = [d[k] for k in sorted(d.keys()) if str(k).isdigit() and isinstance(d[k], dict)]
    if not recs:
        return f"<blockquote>{SEP}\n📱 <b>NUMBER INFO</b>\n{SEP}\n\n❌ No Data Found\n📱 <code>{num}</code>\n\n{_credit()}</blockquote>"
    txt = f"<blockquote>{SEP}\n📱 <b>NUMBER INFO</b>\n{SEP}\n\n├📱 NUMBER  : <code>{num}</code>\n└📊 RECORDS : {len(recs)}\n\n"
    for i, rec in enumerate(recs[:5], 1):
        txt += (f"{REC_SEP}\n👤 RECORD {i}/{len(recs)}\n{REC_SEP}\n"
                f"├📟 MOBILE  : <code>{rec.get('mobile', num)}</code>\n"
                f"├👑 NAME    : {rec.get('name', 'N/A')}\n"
                f"├👨 FATHER  : {rec.get('fname', rec.get('father_name', 'N/A'))}\n"
                f"└🏠 ADDRESS : {rec.get('address', 'N/A')}\n\n")
    txt += f"{_credit()}</blockquote>"
    return txt

def fmt_aadhar(r, an, s=""):
    if not r or not r.get('success'):
        return f"<blockquote>📋 🆔 <b>AADHAR INFO</b>\n\n❌ No Data\n🆔 <code>{an}</code>\n\n{_F}\n{_credit()}</blockquote>"
    dl = r.get('data',[])
    txt = f"<blockquote>📋 🆔 <b>AADHAR INFO</b>\n\n├🆔 AADHAR: <code>{an}</code>\n└📊 RECORDS: {len(dl)}\n\n"
    for i, rec in enumerate(dl[:5], 1):
        txt += (f"{_F}\n📌 RECORD {i}\n{_F}\n"
                f"├👑 NAME: {rec.get('name','N/A')}\n├👨 FATHER: {rec.get('father_name','N/A')}\n"
                f"├📱 MOBILE: <code>{rec.get('mobile','N/A')}</code>\n└🏠 ADDRESS: {rec.get('address','N/A')}\n\n")
    txt += f"{_F}\n{_credit()}</blockquote>"
    return txt

def fmt_instagram(r, un, s=""):
    if not r:
        return f"<blockquote>📋 📸 <b>INSTAGRAM INFO</b>\n\n❌ No Data\n📸 @{un}\n\n{_F}\n{_credit()}</blockquote>", None
    txt = (f"<blockquote>📋 📸 <b>INSTAGRAM INFO</b>\n\n"
           f"├👤 USERNAME: @{r.get('username','N/A')}\n├👑 NAME: {r.get('name','N/A')}\n"
           f"├🆔 ID: <code>{r.get('id','N/A')}</code>\n├👥 FOLLOWERS: {r.get('followers',0)}\n"
           f"├➡️ FOLLOWING: {r.get('following',0)}\n├📸 POSTS: {r.get('posts',0)}\n"
           f"└📝 BIO: {r.get('bio','None')}\n\n{_F}\n{_credit()}</blockquote>")
    return txt, r.get('pic')

def fmt_ff(r, uid_ff, s=""):
    if not r or not r.get('success'):
        return f"<blockquote>{_F}\n🎮 <b>FREE FIRE INFO</b>\n{_F}\n\n❌ No Data Found\n🆔 UID: <code>{uid_ff}</code>\n\n{_credit()}</blockquote>", None
    p1 = (f"<blockquote>{_F}\n🎮 <b>FREE FIRE INFO</b> 🔥\n{_F}\n\n"
          f"🏷️ Name : <b>{r.get('nickname','N/A')}</b>\n🆔 UID : <code>{r.get('uid',uid_ff)}</code>\n"
          f"🌍 Region : {r.get('region','N/A')}\n🎖️ Level : {r.get('level',0)} (XP: {r.get('exp',0):,})\n"
          f"👍 Likes : {r.get('liked',0):,}\n🎯 BR Rank : {r.get('rank_name','N/A')} ({r.get('rank_pts',0)})\n"
          f"🏰 Clan : {r.get('clan_name','No Clan')}\n📅 Created : {r.get('create_at','N/A')}\n"
          f"🕒 Last Login : {r.get('last_login','N/A')}\n\n{_F}\n{_credit()}</blockquote>")
    return p1, None

def fmt_vehicle(r, rc, s=""):
    if not r or not r.get('success'):
        return f"<blockquote>📋 🚗 <b>VEHICLE INFO</b>\n\n❌ No Data\n🚗 <code>{rc}</code>\n\n{_F}\n{_credit()}</blockquote>"
    return (f"<blockquote>📋 🚗 <b>VEHICLE INFO</b>\n\n"
            f"├🚗 RC NUMBER: <code>{rc}</code>\n├👑 OWNER: {r.get('owner_name','N/A')}\n"
            f"├📱 MOBILE: <code>{r.get('mobile_number','N/A')}</code>\n├🚘 MODEL: {r.get('vehicle_model','N/A')}\n"
            f"├📅 REG DATE: {r.get('registration_date','N/A')}\n└⛽ FUEL: {r.get('fuel_type','N/A')}\n\n"
            f"{_F}\n{_credit()}</blockquote>")

# ── KEYBOARDS (Clean Without Credit Buttons) ──
def kb_p1(uid):
    mk = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.row(_KB("ɴᴜᴍʙᴇʀ ɪɴꜰᴏ", style="success"))
    mk.row(
        _KB("ᴛɢ ᴜꜱᴇʀ ᴛᴏ ɴᴜᴍ", style="success"),
        _KB("ꜱᴇʟᴇᴄᴛ ᴛᴀʀɢᴇᴛ", style="success", request_user=KeyboardButtonRequestUser(request_id=1, user_is_bot=False))
    )
    mk.row(_KB("ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ", style="success"), _KB("ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ", style="success"))
    mk.row(_KB("ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ", style="success"), _KB("ʙᴏᴍʙᴇʀ", style="success"))
    mk.row(_KB("🆔 AADHAR INFO", style="success"), _KB("🚗 VEHICLE INFO", style="success"))
    mk.row(_KB("ʜᴇʟᴩ", style="success"), _KB("ꜱᴜᴩᴩᴏʀᴛ", style="success"))
    return mk

def kb_bomber():
    mk = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.row(_KB("💣 ɴᴇᴡ ʙᴏᴍʙᴇʀ", style="success"), _KB("🔴 ꜱᴛᴏᴩ ʙᴏᴍʙᴇʀ", style="danger"))
    mk.row(_KB("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ", style="danger"))
    return mk

# ── COMMAND HANDLERS ──
@bot.message_handler(commands=['start','menu'])
def cmd_start(msg):
    if msg.chat.type == 'channel': return
    uid = msg.from_user.id
    uname = msg.from_user.username or ""
    fname = _html.escape(msg.from_user.first_name or "User")
    if not get_user(uid): add_user(uid, uname, fname)
    wtxt = format_welcome(uid, fname, "∞", uname)
    if msg.chat.type in ['group','supergroup']:
        add_group_to_db(msg.chat.id, msg.chat.title or "Unknown")
        bot.reply_to(msg, wtxt, parse_mode='HTML')
    else:
        _send_react(uid, wtxt, reply_markup=kb_p1(uid), parse_mode='HTML')

@bot.message_handler(commands=['help','hello','h','cmd'])
def cmd_hello(msg):
    txt = (f"<blockquote>{_F}\n📋 <b>ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ʟɪꜱᴛ (100% ꜰʀᴇᴇ)</b> ⚡\n{_F}\n\n"
           f"📱 <b>Number Info:</b> <code>/numinfo 9876543210</code> ya seedha number bhejo\n"
           f"📱 <b>Num2 Info:</b> <code>/num2 9876543210</code>\n"
           f"👤 <b>User Info:</b> <code>/usernum @username</code> ya <code>@username</code> bhejo\n"
           f"🎮 <b>Free Fire Info:</b> <code>/ffinfo uid</code>\n"
           f"❤️ <b>Free Fire Like:</b> <code>/like ind uid</code>\n"
           f"💣 <b>Bomber:</b> <code>/bomb 9876543210</code> | <code>/stopbomb</code>\n\n"
           f"{_F}\n💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>")
    bot.reply_to(msg, txt, parse_mode='HTML')

@bot.message_handler(commands=['numinfo'])
def cmd_numinfo(msg):
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "<blockquote>📌 Usage: <code>/numinfo 9876543210</code></blockquote>", parse_mode='HTML'); return
    num = re.sub(r'\D','',parts[1])[-10:]
    if not re.match(r'^[6-9]\d{9}$', num):
        bot.reply_to(msg, "<blockquote>❌ Valid 10-digit Indian number daalo!</blockquote>", parse_mode='HTML'); return
    sm = bot.reply_to(msg, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
    _sf = _start_anim(msg.chat.id, sm.message_id, 'number')
    res = api_number(num); _sf[0] = True
    txt = fmt_number(res, num)
    try: bot.edit_message_text(txt, msg.chat.id, sm.message_id, parse_mode='HTML')
    except: bot.send_message(msg.chat.id, txt, parse_mode='HTML')

@bot.message_handler(commands=['usernum','user'])
def cmd_usernum(msg):
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "<blockquote>📌 Usage: <code>/usernum @username</code></blockquote>", parse_mode='HTML'); return
    query = parts[1].strip()
    sm = bot.reply_to(msg, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
    _sf = _start_anim(msg.chat.id, sm.message_id, 'usernum')
    res = api_full_user(query); _sf[0] = True
    rtxt, _ = _fmt_tg_user_short(res, query, _now_ist())
    try: bot.edit_message_text(rtxt, msg.chat.id, sm.message_id, parse_mode='HTML')
    except: bot.send_message(msg.chat.id, rtxt, parse_mode='HTML')

@bot.message_handler(commands=['ffinfo','freefire','infoff','info'])
def cmd_ffinfo(msg):
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "<blockquote>📌 Usage: <code>/ffinfo 1382401870</code></blockquote>", parse_mode='HTML'); return
    ff_uid = re.sub(r'\D','',parts[1])
    sm = bot.reply_to(msg, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
    _sf = _start_anim(msg.chat.id, sm.message_id, 'freefire')
    res = api_ff(ff_uid); _sf[0] = True
    p1, _ = fmt_ff(res, ff_uid)
    try: bot.edit_message_text(p1, msg.chat.id, sm.message_id, parse_mode='HTML')
    except: bot.send_message(msg.chat.id, p1, parse_mode='HTML')

@bot.message_handler(commands=['like'])
def cmd_like(msg):
    parts = msg.text.split()
    region = "ind"; ff_uid = None
    if len(parts) == 2: ff_uid = re.sub(r'\D','',parts[1])
    elif len(parts) >= 3:
        region = parts[1].lower() if parts[1].lower() in VALID_REGIONS else "ind"
        ff_uid = re.sub(r'\D','',parts[-1])
    if not ff_uid or len(ff_uid) < 5:
        bot.reply_to(msg, "<blockquote>📌 Usage: <code>/like ind 2819649271</code></blockquote>", parse_mode='HTML'); return
    sm = bot.reply_to(msg, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
    threading.Thread(target=do_ff_like_send, args=(msg.chat.id, sm.message_id, ff_uid, region, msg.from_user.id, msg.from_user.first_name or "User"), daemon=True).start()

@bot.message_handler(commands=['bomb'])
def cmd_bomb(msg):
    uid = msg.from_user.id; parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "<blockquote>💣 Usage: <code>/bomb 9876543210</code></blockquote>", parse_mode='HTML'); return
    num = re.sub(r'\D','',parts[1])[-10:]
    if not re.match(r'^[6-9]\d{9}$', num):
        bot.reply_to(msg, "<blockquote>❌ Valid 10-digit number daalo!</blockquote>", parse_mode='HTML'); return
    sm = bot.reply_to(msg, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
    threading.Thread(target=run_bomber, args=(uid, msg.chat.id, num, sm.message_id), daemon=True).start()

@bot.message_handler(commands=['stopbomb'])
def cmd_stopbomb(msg):
    uid = msg.from_user.id
    if uid in bomber_jobs: bomber_jobs[uid]['running'] = False
    bot.reply_to(msg, "<blockquote>🔴 <b>Bomber stop signal sent!</b></blockquote>", parse_mode='HTML')

# ── BUTTON HANDLERS ──
@bot.message_handler(func=lambda m: m.text in ["🔙 MAIN MENU","🔙 ᴍᴀɪɴ ᴍᴇɴᴜ","🔙 CANCEL","🔙 ᴄᴀɴᴄᴇʟ"])
def go_main(m):
    user_state[m.from_user.id] = S_NONE
    bot.send_message(m.chat.id, "<blockquote>⬇️ <b>ᴍᴀɪɴ ᴍᴇɴᴜ</b></blockquote>", reply_markup=kb_p1(m.from_user.id), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ɴᴜᴍʙᴇʀ ɪɴꜰᴏ","📱 NUMBER INFO"])
def h_num(m):
    user_state[m.from_user.id] = S_NUM
    bot.reply_to(m, f"<blockquote>{_F}\n📱 <b>𝗡𝗨𝗠𝗕𝗘𝗥 𝗜𝗡𝗙𝗢</b>\n{_F}\n\nꜱᴇɴᴅ <b>10-ᴅɪɢɪᴛ ᴍᴏʙɪʟᴇ ɴᴜᴍʙᴇʀ</b>\nᴇxᴀᴍᴩʟᴇ: <code>9876543210</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ᴛɢ ᴜꜱᴇʀ ᴛᴏ ɴᴜᴍ","🔍 USERNAME INFO","🆔 TG ID INFO"])
def h_user(m):
    user_state[m.from_user.id] = S_USER
    bot.reply_to(m, f"<blockquote>{_F}\n🔍 <b>𝗧𝗚 𝗨𝗦𝗘𝗥 𝗧𝗢 𝗡𝗨𝗠𝗕𝗘𝗥</b>\n{_F}\n\nꜱᴇɴᴅ <b>@username</b> ʏᴀ <b>TG ID</b>\nᴇxᴀᴍᴩʟᴇ: <code>@durov</code> ʏᴀ <code>123456789</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🆔 AADHAR INFO","🆔 ᴀᴀᴅʜᴀʀ ɪɴꜰᴏ"])
def h_adh(m):
    user_state[m.from_user.id] = S_ADH
    bot.reply_to(m, f"<blockquote>{_F}\n🪪 <b>𝗔𝗔𝗗𝗛𝗔𝗥 𝗜𝗡𝗙𝗢</b>\n{_F}\n\nꜱᴇɴᴅ <b>12-ᴅɪɢɪᴛ Aadhar</b>\nᴇxᴀᴍᴩʟᴇ: <code>649964855626</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ","📸 INSTAGRAM INFO"])
def h_insta(m):
    user_state[m.from_user.id] = S_INSTA
    bot.reply_to(m, f"<blockquote>{_F}\n📸 <b>𝗜𝗡𝗦𝗧𝗔𝗚𝗥𝗔𝗠 𝗜𝗡𝗙𝗢</b>\n{_F}\n\nꜱᴇɴᴅ ɪɴꜱᴛᴀɢʀᴀᴍ ᴜꜱᴇʀɴᴀᴍᴇ\nᴇxᴀᴍᴩʟᴇ: <code>felix_bhai1</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ","🎮 FREE FIRE INFO"])
def h_ff(m):
    user_state[m.from_user.id] = S_FF
    bot.reply_to(m, f"<blockquote>{_F}\n🎮 <b>𝗙𝗥𝗘𝗘 𝗙𝗜𝗥𝗘 𝗜𝗡𝗙𝗢</b>\n{_F}\n\nꜱᴇɴᴅ FF UID\nᴇxᴀᴍᴩʟᴇ: <code>1231557272</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ","❤️ FREE FIRE LIKE"])
def h_ffl(m):
    user_state[m.from_user.id] = S_FF_LIKE_UID
    bot.reply_to(m, f"<blockquote>{_F}\n❤️ <b>𝗙𝗥𝗘𝗘 𝗙𝗜𝗥𝗘 𝗟𝗜𝗞𝗘</b>\n{_F}\n\nꜱᴇɴᴅ FF UID\nᴇxᴀᴍᴩʟᴇ: <code>1231557272</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🚗 VEHICLE INFO","🚗 ᴠᴇʜɪᴄʟᴇ ɪɴꜰᴏ"])
def h_veh(m):
    user_state[m.from_user.id] = S_VEH
    bot.reply_to(m, f"<blockquote>{_F}\n🚗 <b>𝗩𝗘𝗛𝗜𝗖𝗟𝗘 𝗜𝗡𝗙𝗢</b>\n{_F}\n\nꜱᴇɴᴅ <b>RC Number</b>\nᴇxᴀᴍᴩʟᴇ: <code>MH12AB1234</code></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ʙᴏᴍʙᴇʀ","💣 ʙᴏᴍʙᴇʀ"])
def h_bomber_menu(m):
    bot.send_message(m.chat.id, f"<blockquote>{_F}\n💣 <b>𝗡𝗨𝗠𝗕𝗘𝗥 𝗕𝗢𝗠𝗕𝗘𝗥 𝗠𝗘𝗡𝗨</b>\n{_F}</blockquote>", reply_markup=kb_bomber(), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["💣 ɴᴇᴡ ʙᴏᴍʙᴇʀ","💣 NEW BOMBER"])
def h_new_bomber(m):
    user_state[m.from_user.id] = S_BOMB
    bot.reply_to(m, f"<blockquote>{_F}\n💣 <b>𝗡𝗘𝗪 𝗕𝗢𝗠𝗕𝗘𝗥</b>\n{_F}\n\nꜱᴇɴᴅ <b>10-ᴅɪɢɪᴛ ᴛᴀʀɢᴇᴛ ɴᴜᴍʙᴇʀ</b></blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔴 ꜱᴛᴏᴩ ʙᴏᴍʙᴇʀ","🔴 STOP BOMBER"])
def h_stop_bomber(m):
    uid = m.from_user.id
    if uid in bomber_jobs: bomber_jobs[uid]['running'] = False
    user_state[uid] = S_NONE
    bot.reply_to(m, f"<blockquote>{_F}\n🔴 <b>ʙᴏᴍʙᴇʀ ꜱᴛᴏᴩᴩᴇᴅ</b>\n{_F}</blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ʜᴇʟᴩ","ℹ️ HELP"])
def h_help_btn(m):
    cmd_hello(m)

@bot.message_handler(func=lambda m: m.text in ["ꜱᴜᴩᴩᴏʀᴛ","👑 OWNER"])
def h_owner(m):
    bot.reply_to(m, f"<blockquote>{_F}\n👑 <b>ᴏᴡɴᴇʀ / ꜱᴜᴩᴩᴏʀᴛ</b>\n\n🌐 @Felix_bhai | @Felix_modz1\n{_F}</blockquote>", parse_mode='HTML')

@bot.message_handler(content_types=['users_shared'])
def h_user_shared(m):
    uid = m.from_user.id
    if not m.users_shared or not m.users_shared.user_ids: return
    _raw_obj = m.users_shared.user_ids[0]
    raw = getattr(_raw_obj, 'user_id', _raw_obj)
    ld = bot.send_message(uid, f"<blockquote>{pbar(10)}\n⚡ ꜰᴇᴛᴄʜɪɴɢ ᴀʟʟ ᴅᴀᴛᴀ...</blockquote>", parse_mode='HTML')
    res = api_full_user(str(raw))
    txt, _ = _fmt_tg_user_short(res, f"User ID: {raw}", _now_ist())
    try: bot.edit_message_text(txt, uid, ld.message_id, parse_mode='HTML')
    except: bot.send_message(uid, txt, parse_mode='HTML')

# ── COMPLETED GROUP & PRIVATE INPUT HANDLERS ──
@bot.message_handler(func=lambda m: m.chat.type in ['group','supergroup'])
def h_group(m):
    txt = (m.text or "").strip()
    if not txt: return
    add_group_to_db(m.chat.id, m.chat.title or "Unknown")
    num_clean = re.sub(r'\D','',txt)
    if len(num_clean) == 12 and num_clean.startswith('91'): num_clean = num_clean[2:]
    if re.match(r'^[6-9]\d{9}$', num_clean) and len(txt) <= 14:
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'number')
        res = api_number(num_clean); _sf[0] = True
        bot.edit_message_text(fmt_number(res, num_clean), m.chat.id, sm.message_id, parse_mode='HTML')
    elif re.match(r'^@[a-zA-Z0-9_]{4,}$', txt):
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'username')
        res = api_full_user(txt); _sf[0] = True
        rtxt, _ = _fmt_tg_user_short(res, txt, _now_ist())
        bot.edit_message_text(rtxt, m.chat.id, sm.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type == 'private', content_types=['text'])
def h_private_input(m):
    uid = m.from_user.id
    txt = (m.text or "").strip()
    st = user_state.get(uid, S_NONE)

    # Auto-detect number or @username even if state is S_NONE
    num_clean = re.sub(r'\D','',txt)
    if len(num_clean) == 12 and num_clean.startswith('91'): num_clean = num_clean[2:]

    if st == S_NUM or (st == S_NONE and re.match(r'^[6-9]\d{9}$', num_clean) and len(txt) <= 14):
        if not re.match(r'^[6-9]\d{9}$', num_clean):
            bot.reply_to(m, "<blockquote>❌ Valid 10-digit Indian mobile number bhejo!</blockquote>", parse_mode='HTML'); return
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'number')
        res = api_number(num_clean); _sf[0] = True
        bot.edit_message_text(fmt_number(res, num_clean), m.chat.id, sm.message_id, parse_mode='HTML')
        return

    if st in (S_USER, S_TID) or (st == S_NONE and txt.startswith('@')):
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'username')
        res = api_full_user(txt); _sf[0] = True
        rtxt, _ = _fmt_tg_user_short(res, txt, _now_ist())
        bot.edit_message_text(rtxt, m.chat.id, sm.message_id, parse_mode='HTML')
        return

    if st == S_ADH:
        an = re.sub(r'\D','',txt)
        if len(an) != 12:
            bot.reply_to(m, "<blockquote>❌ Valid 12-digit Aadhar number bhejo!</blockquote>", parse_mode='HTML'); return
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'aadhar')
        res = api_aadhar(an); _sf[0] = True
        bot.edit_message_text(fmt_aadhar(res, an), m.chat.id, sm.message_id, parse_mode='HTML')
        return

    if st == S_INSTA:
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'instagram')
        res = api_instagram(txt); _sf[0] = True
        rtxt, _ = fmt_instagram(res, txt)
        bot.edit_message_text(rtxt, m.chat.id, sm.message_id, parse_mode='HTML')
        return

    if st == S_FF:
        ff_uid = re.sub(r'\D','',txt)
        if len(ff_uid) < 5:
            bot.reply_to(m, "<blockquote>❌ Valid Free Fire UID bhejo!</blockquote>", parse_mode='HTML'); return
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'freefire')
        res = api_ff(ff_uid); _sf[0] = True
        p1, _ = fmt_ff(res, ff_uid)
        bot.edit_message_text(p1, m.chat.id, sm.message_id, parse_mode='HTML')
        return

    if st == S_FF_LIKE_UID:
        ff_uid = re.sub(r'\D','',txt)
        if len(ff_uid) < 5:
            bot.reply_to(m, "<blockquote>❌ Valid Free Fire UID bhejo!</blockquote>", parse_mode='HTML'); return
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        threading.Thread(target=do_ff_like_send, args=(m.chat.id, sm.message_id, ff_uid, "ind", uid, m.from_user.first_name or "User"), daemon=True).start()
        return

    if st == S_VEH:
        rc = re.sub(r'[^a-zA-Z0-9]','',txt).upper()
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        _sf = _start_anim(m.chat.id, sm.message_id, 'vehicle')
        res = api_vehicle(rc); _sf[0] = True
        bot.edit_message_text(fmt_vehicle(res, rc), m.chat.id, sm.message_id, parse_mode='HTML')
        return

    if st == S_BOMB:
        if not re.match(r'^[6-9]\d{9}$', num_clean):
            bot.reply_to(m, "<blockquote>❌ Valid 10-digit Indian number bhejo!</blockquote>", parse_mode='HTML'); return
        user_state[uid] = S_NONE
        sm = bot.reply_to(m, f"<blockquote>{pbar(0)}\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
        threading.Thread(target=run_bomber, args=(uid, m.chat.id, num_clean, sm.message_id), daemon=True).start()
        return

if __name__ == "__main__":
    print("✅ Bot started (No Credit System | All Permissions Unlocked)...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=25)
