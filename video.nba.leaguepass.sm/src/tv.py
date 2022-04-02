import datetime
import time
import json
import sys

from xml.dom.minidom import parseString

import pytz

import xbmc
import xbmcaddon
import xbmcplugin

import common
from shareddata import SharedData
from videos import videoMenu
import utils
import vars

try:
    from urllib.parse import urlencode
    import urllib.request  as urllib2
except ImportError:
    from urllib import urlencode
    import urllib2


class TV:

    @staticmethod
    def menu():
        common.addListItem('Live', '', 'nba_tv_play_live', '')
        common.addListItem('Today\'s programming', '', 'nba_tv_episode_menu', '', isfolder=True)
        common.addListItem('Select date', '', 'nba_tv_episode_menu', '', isfolder=True, customparams={
            'custom_date': True
        })
        common.addListItem('NBA TV Series', '', 'nba_tv_series', '', isfolder=True)
        common.addListItem('Video Collections', '', 'nba_tv_videolist', '', isfolder=True, customparams={
            'url': 'https://content-api-prod.nba.com/public/1/endeavor/layout/watch/nbatv'
        })
        common.addListItem('NBA TV Clips', '', 'videolist', '', True, customparams={
            'video_tag':'nba-tv-clips', 'pagination': True
        })

    @staticmethod
    def episode_menu():
        et_tz = pytz.timezone('US/Eastern')
        date_et = common.get_date() if vars.params.get('custom_date', False) else utils.tznow(et_tz).date()

        # Avoid possible caching by using query string
        epg_url = 'https://nlnbamdnyc-a.akamaihd.net/fs/nba/feeds/epg/%d/%d_%d.js?t=%d' % (
            date_et.year, date_et.month, date_et.day, time.time())
        response = utils.fetch(epg_url)
        g_epg = json.loads(response[response.find('['):])

        for epg_item in g_epg:
            entry = epg_item['entry']

            start_et_hours, start_et_minutes = map(int, entry['start'].split(':'))
            duration_hours, duration_minutes = map(int, entry['duration'].split(':'))

            dt_et = et_tz.localize(datetime.datetime(date_et.year, date_et.month, date_et.day, start_et_hours, start_et_minutes))
            dt_utc = dt_et.astimezone(pytz.utc)

            start_timestamp = int((dt_utc - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()) * 1000  # in milliseconds
            duration = (duration_hours * 60 + duration_minutes) * 60 * 1000  # in milliseconds

            params = {
                'start_timestamp': start_timestamp,
                'duration': duration,
            }
            utils.log(params, xbmc.LOGDEBUG)

            name = '%s %s: %s' % (
                entry['start'], dt_et.tzname(), entry['showTitle'] if entry['showTitle'] else entry['title'])
            common.addListItem(name, '', 'nba_tv_play_episode', iconimage=entry['image'], customparams=params)
    
    #get the list of available series
    @staticmethod
    def series_Menu():
        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
        url = "https://content-api-prod.nba.com/public/1/endeavor/video-list/nba-tv-series"
        json_parser = json.loads(utils.stringify(urllib2.urlopen(url).read()))
        for serie in json_parser['results']:
            name = serie['series']['name']
            plot = serie['series']['description']
            slug = serie['series']['slug']
            thumb = serie['series']['coverImage']['portrait']
            infoList = {
                    "mediatype": "tvshow",
                    "title": name,
                    "TVShowTitle": name,
                    "plot": plot
                    }
            common.addListItem(
                        name,
                        '',
                        'nba_tv_seasons',
                        thumb,
                        isfolder=True,
                        customparams={'slug': slug, 'video_type': 'nba-tv-series', 'serie_title': name,  'pagination': True},
                        infoList=infoList)

    #get the list of available seasons for a serie
    @staticmethod
    def season_Menu():
        xbmcplugin.setContent(int(sys.argv[1]), 'seasons')
        slug = vars.params.get("slug")
        serie_title = vars.params.get("serie_title")
        page = int(vars.params.get("page", 1))
        per_page = 20
        utils.log("seasonListMenu: tag is %s, page is %d" % (slug, page), xbmc.LOGDEBUG)
        base_url = "https://content-api-prod.nba.com/public/1/endeavor/video-list/nba-tv-series/%s?"
        params = urlencode({
            "sort": "releaseDate desc",
            "page": page,
            "count": per_page
        })
        url = base_url % slug + params
        response = utils.stringify(urllib2.urlopen(url).read())
        utils.log("seasonListMenu: response: %s" % response, xbmc.LOGDEBUG)
        jsonresponse = json.loads(response)
        seasonicon = jsonresponse['results']['series']['coverImage']['portrait']
        # idx is the index of the season in the json data
        # to do: avoid fetching the same page for season and episodes
        idx = 0
        for season in jsonresponse['results']['seasons']:
            name = 'Season %s' % season['season']
            common.addListItem(name, '',
                    'nba_tv_episode',
                    seasonicon,
                    isfolder=True,
                    customparams={'url':url, 'seasonidx': idx, 'serie_title': serie_title})
            idx = idx +1

    #get the list of available episodes for a season
    @staticmethod
    def episodes_list_Menu():
        xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
        url = vars.params.get("url")
        serie_title = vars.params.get("serie_title")
        seasonidx = int(vars.params.get("seasonidx"))
        response = utils.stringify(urllib2.urlopen(url).read())
        utils.log("episodeListMenu: response: %s" % response, xbmc.LOGDEBUG)
        jsonresponse = json.loads(response)
        episodes = jsonresponse['results']['seasons'][seasonidx]['episodes']
        for episode in episodes:
            name = episode['title']
            release_date = episode['releaseDate'].split('T')[0]
            plot = episode['description']
            runtime = episode['program']['runtimeHours'].split(':')
            seconds = int(runtime[-1])
            minutes = int(runtime[-2])
            duration = minutes * 60 + seconds
            if len(runtime) == 3:
                hours = int(runtime[0])
                duration = duration + hours * 3600
            thumb = episode['image']
            infoList = {
                    "mediatype": "episode",
                    "title": name,
                    "TVShowTitle": serie_title,
                    "duration": duration,
                    "plot": plot,
                    "aired":str(release_date)
                    }
            common.addListItem(url=str(episode['program']['id']), name=name, mode='nba_tv_play_serieepisode', iconimage=thumb, infoList=infoList)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    @staticmethod
    def nba_tv_videoMenu():
        xbmcplugin.setContent(int(sys.argv[1]), 'videos')
        url = "https://content-api-prod.nba.com/public/1/endeavor/layout/watch/nbatv"
        json_parser = json.loads(utils.stringify(urllib2.urlopen(url).read()))
        for category in json_parser['results']['carousels']:
            if category['type'] == "video_carousel":
                common.addListItem(category['title'], '',
                    'nba_tv_videoplay', category['value']['videos'][0]['image'], True,
                    customparams={'slug':category['value']['slug'], 'pagination': True})
            elif category['type'] == "collection_cards":
                for collection in category['value']['items']:
                    common.addListItem(collection['name'], '',
                    'nba_tv_videoplay', collection['image'], True,
                    customparams={'slug':collection['slug'], 'pagination': True})


    @staticmethod
    def nba_tv_videoPlay():
        xbmcplugin.setContent(int(sys.argv[1]), 'videos')
        slug = vars.params.get("slug")
        page = int(vars.params.get("page", 1))
        per_page = 22
        utils.log("nba_tv_videoPlay: collection is %s, page is %d" % (slug, page), xbmc.LOGDEBUG)
        base_url = "https://content-api-prod.nba.com/public/1/endeavor/video-list/collection/%s?"
        params = urlencode({
            "sort": "releaseDate desc",
            "page": page,
            "count": per_page
        })
        url = base_url % slug + params
        utils.log("nba_tv_videoPlay: %s: url of collection is %s" % (slug, url), xbmc.LOGDEBUG)
        response = utils.stringify(urllib2.urlopen(url).read())
        utils.log("nba_tv_videoPlay: response: %s" % response, xbmc.LOGDEBUG)
        jsonresponse = json.loads(response)
        for video in jsonresponse['results']['videos']:
            name = video['title']
            entitlement = video['entitlements']
            release_date = video['releaseDate'].split('T')[0]
            plot = video['description']
            thumb = video['image']
            runtime = video['program']['runtimeHours'].split(':')
            seconds = int(runtime[-1])
            minutes = int(runtime[-2])
            duration = minutes * 60 + seconds
            if len(runtime) == 3:
                hours = int(runtime[0])
                duration = duration + hours * 3600
            infoList = {
                    "mediatype": "video",
                    "title": name,
                    "duration": duration,
                    "plot": plot,
                    "aired":str(release_date)
                    }
            if entitlement == 'free':
                common.addListItem(url=str(video['program']['id']), name=name, mode='videoplay', iconimage=thumb, infoList=infoList)
            else:
                common.addListItem(url=str(video['program']['id']), name=name, mode='nba_tv_play_serieepisode', iconimage=thumb, infoList=infoList)
        if vars.params.get("pagination") and page+1 <= jsonresponse['results']['pages']:
            next_page_name = xbmcaddon.Addon().getLocalizedString(50008)
    
            # Add "next page" link
            custom_params = {
                'slug': slug,
                'page': page + 1,
                'pagination': True
            }
            common.addListItem(next_page_name, '', 'nba_tv_videolist', '', True, customparams=custom_params)    
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))


    @staticmethod
    def play_live():
        live = TV.get_live()
        if live is not None:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'nba_tv_live',
            })
            common.play(live)

    @staticmethod
    def play_episode():
        start_timestamp = vars.params.get('start_timestamp')
        duration = vars.params.get('duration')
        episode = TV.get_episode(start_timestamp, duration)
        if episode is not None:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'nba_tv_episode',
                'data': {
                    'start_timestamp': start_timestamp,
                    'duration': duration,
                },
            })
            common.play(episode)

    @staticmethod
    def play_serieepisode():
        episode = TV.get_serie_episode()
        if episode is not None:
            shared_data = SharedData()
            shared_data.set('playing', {
                'what': 'episode_nba_tv',
            })
            common.play(episode)

    @staticmethod
    def get_episode(start_timestamp, duration):
        if not common.authenticate():
            return None

        url = vars.config['publish_endpoint']
        headers = {
            'Cookie': vars.cookies,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        body = {
            'type': 'channel',
            'id': 1,
            'drmtoken': True,
            'token': vars.access_token,
            'deviceid': xbmc.getInfoLabel('Network.MacAddress'),  # TODO
            'st': start_timestamp,
            'dur': duration,
            'pcid': vars.player_id,
            'format': 'xml',
        }

        body = urlencode(body).encode()
        utils.log('the body of publishpoint request is: %s' % body, xbmc.LOGDEBUG)

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request, timeout=30)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.logHttpException(err, url)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return None

        xml = parseString(utils.stringify(content))
        url = xml.getElementsByTagName('path')[0].childNodes[0].nodeValue
        utils.log('response URL from publishpoint: %s' % url, xbmc.LOGDEBUG)
        drm = xml.getElementsByTagName('drmToken')[0].childNodes[0].nodeValue
        utils.log(drm, xbmc.LOGDEBUG)

        return {'url': url, 'drm': drm}

    @staticmethod
    def get_live():
        if not common.authenticate():
            return None

        url = vars.config['publish_endpoint']
        headers = {
            'Cookie': vars.cookies,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        body = {
            'type': 'channel',
            'id': 1,
            'drmtoken': True,
            'token': vars.access_token,
            'deviceid': xbmc.getInfoLabel('Network.MacAddress'),  # TODO
            'pcid': vars.player_id,
            'format': 'xml',
        }

        body = urlencode(body).encode()
        utils.log('the body of publishpoint request is: %s' % body, xbmc.LOGDEBUG)

        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request, timeout=30)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.logHttpException(err, url)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return None

        xml = parseString(utils.stringify(content))
        url = xml.getElementsByTagName('path')[0].childNodes[0].nodeValue
        utils.log('response URL from publishpoint: %s' % url, xbmc.LOGDEBUG)
        drm = xml.getElementsByTagName('drmToken')[0].childNodes[0].nodeValue
        utils.log(drm, xbmc.LOGDEBUG)

        return {'url': url, 'drm': drm}

    @staticmethod
    def get_serie_episode():
        video_id = vars.params.get("url")
        if not common.authenticate():
            return None
        url = vars.config['publish_endpoint']
        headers = {
            'Cookie': vars.cookies,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        body = {
            'type': 'video',
            'id': video_id,
            'drmtoken': True,
            'token': vars.access_token,
            'deviceid': 'web-%s' % vars.player_id,
            'pcid': vars.player_id,
            'format': 'json',
        }
        body = urlencode(body).encode()
        utils.log('the body of publishpoint request is: %s' % body, xbmc.LOGDEBUG)
        try:
            request = urllib2.Request(url, body, headers)
            response = urllib2.urlopen(request, timeout=30)
            content = response.read()
        except urllib2.HTTPError as err:
            utils.logHttpException(err, url)
            utils.littleErrorPopup(xbmcaddon.Addon().getLocalizedString(50020))
            return None
        content_json = json.loads(content)
        url = content_json['path']
        drm = content_json['drmToken']
        utils.log('response URL from publishpoint: %s' % url, xbmc.LOGDEBUG)
        utils.log(drm, xbmc.LOGDEBUG)
        
        return {'url': url, 'drm': drm}
