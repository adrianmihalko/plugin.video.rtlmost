# -*- coding: utf-8 -*-

'''
    RTL Most Add-on
    Copyright (C) 2018

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import os,sys,json,xbmc,xbmcaddon,xbmcgui,xbmcplugin,re
from resources.lib.modules import net
from resources.lib.modules import m3u8_parser
from resources.lib.modules.utils import py2_encode

token_url = 'https://6play-users.6play.fr/v2/platforms/m6group_web/services/rtlhu_rtl_most/users/%s/videos/%s/upfront-token'
getjwt_url = 'https://auth.6play.fr/v2/platforms/m6group_web/getJwt'

class player:
    def __init__(self):
        self.uid = xbmcaddon.Addon().getSetting('userid')


    def play(self, id, streams, image, meta):
        streams = sorted(streams)
        #dash_url = [i for i in streams if 'drmnp.ism/Manifest.mpd' in i]
        dash_url = [i for i in streams if re.match(r'(.*)drm(.*)Manifest.mpd(.*)', i)]
        hls_url = [i for i in streams if 'unpnp.ism/Manifest.m3u8' in i]
        live_url = [i for i in streams if 'stream.m3u8' in i]
        li = None

        if dash_url != []:
            # Inputstream and DRM
            #manifest_url = net.request(dash_url[0], redirect=False)
            #stream_url = os.path.dirname(manifest_url) + '/Manifest.mpd'         
            stream_url=dash_url[0]
            headers = {
                'x-auth-gigya-uid': self.uid,
                'x-auth-gigya-signature': xbmcaddon.Addon().getSetting('signature'),
                'x-auth-gigya-signature-timestamp': xbmcaddon.Addon().getSetting('s.timestamp'),
                'Origin': 'https://www.rtlmost.hu'}

            token_source = net.request(token_url % (self.uid, id), headers=headers)
            token_source = json.loads(token_source)
            x_dt_auth_token = py2_encode(token_source['token'])

            license_headers = 'x-dt-auth-token=' + x_dt_auth_token + '&Origin=https://www.rtlmost.hu&Content-Type='
            license_key = 'https://lic.drmtoday.com/license-proxy-widevine/cenc/' + '|' + license_headers + '|R{SSM}|JBlicense'
            DRM = 'com.widevine.alpha'
            PROTOCOL = 'mpd'

            from inputstreamhelper import Helper
            is_helper = Helper(PROTOCOL, drm=DRM)
            if is_helper.check_inputstream():
                li = xbmcgui.ListItem(path=stream_url)
                if sys.version_info < (3, 0):  # if python version < 3 is safe to assume we are running on Kodi 18
                    li.setProperty('inputstreamaddon', 'inputstream.adaptive')   # compatible with Kodi 18 API
                else:
                    li.setProperty('inputstream', 'inputstream.adaptive')  # compatible with recent builds Kodi 19 API
                li.setProperty('inputstreamaddon', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
                li.setProperty('inputstream.adaptive.license_type', DRM)
                li.setProperty('inputstream.adaptive.license_key', license_key)
                li.setMimeType('application/dash+xml')
                li.setContentLookup(False)

        elif hls_url != []:
            stream_url = hls_url[0]
            manifest_url = net.request(stream_url, redirect=False)

            manifest = net.request(manifest_url)
            sources = m3u8_parser.parse(manifest)
            if len(sources) == 0:
                manifest_url = stream_url
                manifest = net.request(manifest_url)
                sources = m3u8_parser.parse(manifest)

            root = os.path.dirname(manifest_url)

            sources = sorted(sources, key=lambda x: x['resolution'])[::-1]

            auto_pick = xbmcaddon.Addon().getSetting('hls_quality') == '0'

            if len(sources) == 1 or auto_pick == True:
                source = sources[0]['uri']
            else:
                result = xbmcgui.Dialog().select(u'Min\u0151s\u00E9g', [str(source['resolution']) if 'resolution' in source else 'Unknown' for source in sources])
                if result == -1:
                    return
                else:
                    source = sources[result]['uri']
            stream_url = root + '/' + source
            li = xbmcgui.ListItem(path=stream_url)

        elif live_url != []:
            live_url.sort(reverse=True)
            sources = []
            for i in live_url:
                stream_url = i
                try:
                    manifest = net.request(stream_url, timeout=30)
                    sources_temp = m3u8_parser.parse(manifest)
                    root = os.path.dirname(stream_url)
                    for j in sources_temp:
                        j['root'] = root
                    sources.extend(sources_temp)
                    if len(sources)>0:
                        break
                except:
                        pass
            sources = sorted(sources, key=lambda x: x['resolution'], reverse=False)
            auto_pick = xbmcaddon.Addon().getSetting('hls_quality') == '0'

            if len(sources) > 0:
                if len(sources) == 1 or auto_pick == True:
                    source = sources[0]['uri']
                else:
                    result = xbmcgui.Dialog().select(u'Min\u0151s\u00E9g', [str(source['resolution']) if 'resolution' in source else 'Unknown' for source in sources])
                    if result == -1:
                        return
                    else:
                        source = sources[result]['uri']
                stream_url = root + '/' + source
            else:
                stream_url = live_url[0]
            li = xbmcgui.ListItem(path=stream_url)
            meta = json.loads(meta)
            li.setInfo(type='Video', infoLabels = meta)
            xbmc.Player().play(stream_url, li)
            return

        if li is None:
            xbmcgui.Dialog().notification(u'Lej\u00E1tsz\u00E1s sikertelen. DRM v\u00E9dett m\u0171sor.', 'RTL Most', time=8000)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            return

        stream_url_content = net.request(stream_url)
        meta = json.loads(meta)
        li.setArt({'icon': image, 'thumb': image, 'poster': image, 'tvshow.poster': image})
        li.setInfo(type='Video', infoLabels = meta)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
