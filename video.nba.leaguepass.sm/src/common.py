import json
import datetime
import xbmc
import xbmcaddon
import xbmcgui
from xml.dom.minidom import parseString

import vars
from utils import *
try:
    from urllib.parse import urlencode
    import urllib.request  as urllib2
except ImportError:
    from urllib import urlencode
    import urllib2

PROTOCOLS = {
    'mpd': {'extensions': ['mpd'], 'mimetype': 'application/dash+xml'},
    'hls': {'extensions': ['m3u8', 'm3u'], 'mimetype': 'application/vnd.apple.mpegurl'},
}
DRM = 'com.widevine.alpha'  # TODO Handle other DRM_SCHEMES
LICENSE_URL = 'https://shield-twoproxy.imggaming.com/proxy'
XBMC_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split('-')[0].split('.')[0])
INPUTSTREAM_PROP = 'inputstream' if XBMC_VERSION >= 19 else 'inputstreamaddon'

def play(video):
    item = None
    if 'url' in video:
        item = xbmcgui.ListItem(path=video['url'])
        for protocol, protocol_info in PROTOCOLS.items():
            if any(".%s" % extension in video['url'] for extension in protocol_info['extensions']):
                from inputstreamhelper import Helper
                is_helper = Helper(protocol, drm=DRM)
                if is_helper.check_inputstream():
                    item.setMimeType(protocol_info['mimetype'])
                    item.setContentLookup(False)
                    item.setProperty(INPUTSTREAM_PROP, is_helper.inputstream_addon)
                    item.setProperty('inputstream.adaptive.manifest_type', protocol)
                    item.setProperty('inputstream.adaptive.license_type', DRM)
                    license_key = '%s|authorization=bearer %s|R{SSM}|' % (LICENSE_URL, video['drm'])
                    item.setProperty('inputstream.adaptive.license_key', license_key)
                    item.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')

    if item is not None:
        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)

def updateFavTeam():
    vars.fav_team_abbrs = None

    settings = xbmcaddon.Addon(id=vars.__addon_id__)
    fav_team_name = settings.getSetting(id="fav_team")
    if fav_team_name:
        for franchise, abbrs in vars.config['franchises'].items():
            if fav_team_name == franchise:
                vars.fav_team_abbrs = abbrs
                xbmc.log(msg="fav_team_abbrs set to %s" % vars.fav_team_abbrs, level=xbmc.LOGWARNING)

def getFanartImage():
    # Get the feed url
    feed_url = "https://nlnbamdnyc-a.akamaihd.net/fs/nba/feeds/common/dl.js"
    xbmc.log(feed_url, xbmc.LOGINFO)
    req = urllib2.Request(feed_url, None)
    response = stringify(urllib2.urlopen(req, timeout=30).read())

    try:
        # Parse
        js = json.loads(response[response.find("{"):])
        dl = js["dl"]

        # for now only chose the first fanart
        first_id = dl[0]["id"]
        fanart_image = "https://nbadsdmt.akamaized.net/media/nba/nba/thumbs/dl/%s_pc.jpg" % first_id
        xbmc.log(fanart_image, xbmc.LOGINFO)
        vars.settings.setSetting("fanart_image", fanart_image)
    except:
        # I don't care
        pass

def get_date(default='', heading='Please enter date (YYYY/MM/DD)', hidden=False):
    now = datetime.datetime.now()
    default = "%04d" % now.year + '/' + "%02d" % now.month + '/' + "%02d" % now.day
    keyboard = xbmc.Keyboard(default, heading, hidden)
    keyboard.doModal()
    ret = datetime.date.today()
    if keyboard.isConfirmed():
        sDate = keyboard.getText()
        temp = sDate.split("/")
        ret = datetime.date(int(temp[0]), int(temp[1]), int(temp[2]))
    return ret

def authenticate():
    email = vars.settings.getSetting(id="email")
    password = vars.settings.getSetting(id="password")

    if not email or not password:
        littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50024))
        return False

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
            'Content-Type': 'application/json',
            'X-Client-Platform': 'web',
        }
        body = json.dumps({
            'email': email,
            'password': password,
            'rememberMe': True,
        }).encode()

        request = urllib2.Request('https://identity.nba.com/api/v1/auth', body, headers)
        response = urllib2.urlopen(request, timeout=30)
        content = response.read()
        content_json = json.loads(content)
        vars.cookies = response.info()['Set-Cookie'].partition(';')[0]
    except urllib2.HTTPError as err:
        littleErrorPopup(err)
        return False

    try:
        headers = {
            'Cookie': vars.cookies,
            'Referer': 'https://watch.nba.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        body = {
            'format': 'json',
            'accesstoken': 'true',
            'ciamlogin': 'true',
        }
        body = urlencode(body).encode()

        request = urllib2.Request('https://watch.nba.com/secure/authenticate', body, headers)
        response = urllib2.urlopen(request, timeout=30)
        content = response.read()
        content_json = json.loads(content)
        login_status = content_json['code']
        vars.access_token = content_json['data']['accessToken']
    except urllib2.HTTPError as err:
        littleErrorPopup(err)
        return False
    try:
        headers = {
            'authorization': 'Bearer %s'%vars.access_token,
            'Referer': 'https://watch.nba.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        request = urllib2.Request('http://nbaapi.neulion.com/api_nba/v1/account/subscriptions?associations=false', None, headers)
        response = urllib2.urlopen(request)
        content_json = json.loads(response.read())
        if 'subs' in content_json:
            subscrition = content_json['subs'][0]['name']
            expiration_ = content_json['subs'][0]['accessThrough']
            country = content_json['subs'][0]['country']
            expiration_ = content_json['subs'][0]['accessThrough']
            packages = content_json['subs'][0]['details']
        elif login_status == "loginsuccess":
            littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50025))
    except urllib2.HTTPError as err:
        if err == 'HTTP Error 401: Unauthorized':
            littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50021))
        return False
    return True
