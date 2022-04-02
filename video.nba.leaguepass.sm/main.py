import xbmc, xbmcaddon, xbmcvfs
import sys, os


my_addon = xbmcaddon.Addon('video.nba.leaguepass.sm')
addon_dir = xbmcvfs.translatePath(my_addon.getAddonInfo('path'))

sys.path.append(os.path.join(addon_dir, 'src'))

from leaguepass import *
