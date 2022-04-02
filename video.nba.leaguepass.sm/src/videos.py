import json
import datetime, time
from datetime import timedelta

import xbmc, xbmcplugin, xbmcgui, xbmcaddon
from xml.dom.minidom import parseString
import re

from utils import *
from common import *
import vars
try:
    from urllib.parse import unquote_plus
    from urllib.parse import urlencode
    import urllib.request  as urllib2
except ImportError:
    from urllib import unquote_plus
    from urllib import urlencode
    import urllib2

def videoDateMenu():
    video_tag = vars.params.get("video_tag")

    dates = []
    current_date = datetime.date.today() - timedelta(days=1)
    last_date = current_date - timedelta(days=7)
    while current_date - timedelta(days=1) > last_date:
        dates.append(current_date)
        current_date = current_date - timedelta(days=1)

    for date in dates:
        params = {'date': date, 'video_tag': video_tag}
        addListItem(name=str(date), url='', mode='videolist', iconimage='', isfolder=True, customparams=params)
    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

def videoMenu():
    xbmcplugin.setContent(int(sys.argv[1]), 'videos')
    url = vars.params.get("url", None)
    if not url:
        url = "https://content-api-prod.nba.com/public/1/endeavor/layout/watch/landing"
    json_parser = json.loads(stringify(urllib2.urlopen(url).read()))
    for category in json_parser['results']['carousels']:
        if category['type'] == "video_carousel":
            addListItem(category['title'], '',
                'videolist', category['value']['videos'][0]['image'], True,
                customparams={'video_tag':category['value']['slug'], 'pagination': True})
        elif category['type'] == "collection_cards":
            for collection in category['value']['items']:
                addListItem(collection['name'], '',
                'videolist', collection['image'], True,
                customparams={'video_tag':collection['slug'], 'pagination': True})

def videoListMenu():
    xbmcplugin.setContent(int(sys.argv[1]), 'videos')
    video_tag = vars.params.get("video_tag")
    page = int(vars.params.get("page", 1))
    per_page = 22
    log("videoListMenu: tag is %s, page is %d" % (video_tag, page), xbmc.LOGDEBUG)

    base_url = "https://content-api-prod.nba.com/public/1/endeavor/video-list/collection/%s?"
    params = urlencode({
        "sort": "releaseDate desc",
        "page": page,
        "count": per_page
    })
    url = base_url%video_tag + params
    log("videoListMenu: %s: url of tag is %s" % (video_tag, url), xbmc.LOGDEBUG)
    response = stringify(urllib2.urlopen(url).read())
    log("videoListMenu: response: %s" % response, xbmc.LOGDEBUG)
    jsonresponse = json.loads(response)
    for video in jsonresponse['results']['videos']:
        name = video['title']
        thumb = video['image']
        release_date = video['releaseDate'].split('T')[0]
        plot = video['description']
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
        addListItem(url=str(video['program']['id']), name=name, mode='videoplay', iconimage=thumb, infoList=infoList)
    if vars.params.get("pagination") and page+1 <= jsonresponse['results']['pages']:
        next_page_name = xbmcaddon.Addon().getLocalizedString(50008)

        # Add "next page" link
        custom_params = {
            'video_tag': video_tag,
            'page': page + 1,
            'pagination': True
        }

        addListItem(next_page_name, '', 'videolist', '', True, customparams=custom_params)

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

def videoPlay():
    video_id = vars.params.get("url")
    if not authenticate():
        return

    url = vars.config['publish_endpoint']
    headers = {
        'authorization': 'Bearer %s'%vars.access_token,
        'Content-type': 'application/x-www-form-urlencoded',
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
    }
    body = urlencode({
        'id': str(video_id),
        'format': 'json',
        'type': 'video',
    })
    try:
        request = urllib2.Request(url+'?%s'%body, None, headers=headers)
        response = urllib2.urlopen(request, timeout=30)
        content = response.read()
    except urllib2.HTTPError as e:
        logHttpException(e, url, body)
        littleErrorPopup("Failed to get video url. Please check log for details")
        return ''

    json_parser = json.loads(stringify(content))
    video_url = json_parser['path']
    log("videoPlay: video url is %s" % video_url, xbmc.LOGDEBUG)

    # Remove query string
    #video_url = re.sub("\?[^?]+$", "", video_url)

    item = xbmcgui.ListItem(path=video_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
