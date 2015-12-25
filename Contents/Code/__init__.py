from operator import itemgetter
from HTMLParser import HTMLParser
import urllib, urllib2, cookielib, re

class MLStripper(HTMLParser):
	def __init__(self):
		self.reset()
		self.fed = []
	def handle_data(self, d):
		self.fed.append(d)
	def handle_entityref(self, name):
		self.fed.append('&%s;' % name)
	def get_data(self):
		return ''.join(self.fed)

def html_to_text(html):
	s = MLStripper()
	s.feed(html)
	return s.get_data()

def create_meta_re(prop):
	return re.compile('<meta.*property=[\'"]%s[\'"].*content=[\'"](?P<match>[^"\']+)[\'\"].*>' % prop)

BASE_URL = 'https://www.tytnetwork.com/'
TITLE    = 'The Young Turks'
PREFIX   = '/video/theyoungturks'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
RSS_FEEDS = [
	'https://www.tytnetwork.com/category/membership/main-show-hour-1/feed/',
	'https://www.tytnetwork.com/category/membership/main-show-hour-2/feed/',
	'https://www.tytnetwork.com/category/membership/post-game/feed/',
]
RE_VIDEO_URL = re.compile('<source.*src=[\'"](?P<video_url>[^"\']+)[\'\"].*>')
RE_TITLE = create_meta_re('og:title')
RE_DESCRIPTION = create_meta_re('og:description')
RE_THUMB = create_meta_re('og:image')
RE_PPK = re.compile('powerpresskey=(?P<ppk>[a-z0-9-]+)')

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

@route(PREFIX + '/authenticate')
def Authenticate():
	# Only when username and password are set
	if Prefs['username'] and Prefs['password']:
		login_data = urllib.urlencode({
			'log' : Prefs['username'],
			'pwd' : Prefs['password'],
		})
		opener.addheaders = [
			('origin', BASE_URL),
			('referer', BASE_URL),
		]
		
		try:
			opener.open('https://www.tytnetwork.com/wp-login.php?wpe-login=tyt', login_data)
			content = opener.open('https://www.tytnetwork.com/tyt-network-podcasting/').read()
			Dict['ppk'] = RE_PPK.search(content).group('ppk')
			return True

		except Exception as e:
			Log("Login Failed")
			Log(e)
			return False
	else:
		return False
	
def Start():
	ObjectContainer.title1 = TITLE
	ObjectContainer.art = R(ART)
	DirectoryObject.thumb = R(ICON)
	DirectoryObject.art = R(ART)
	EpisodeObject.thumb = R(ICON)
	EpisodeObject.art = R(ART)
	VideoClipObject.thumb = R(ICON)
	VideoClipObject.art = R(ART)
	Dict.Reset()
	if not Authenticate():
		return MessageContainer("Login", "Enter your username and password in Preferences.")

@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def MainMenu():
	oc = ObjectContainer(title2=TITLE)
	oc.add(PrefsObject(title=L('Preferences')))
	# TYT doesn't provide a single feed of their videos, only the last three in each category. So we concatenate the
	# feeds from the three categories (Hour 1, Hour 2, Post Game), sort them by date, and THEN add them to the OC
	items = []
	for feed in RSS_FEEDS:
		url = '%s?powerpresskey=%s' % (feed, Dict['ppk'])
		xml = RSS.FeedFromURL(url)
		items += [item for item in xml.entries]
	items.sort(key=itemgetter('updated_parsed'), reverse=True)
	
	for item in items:
		oc.add(VideoClipObject(
			key=Callback(GetEpisodeData, url=item.link),
			rating_key=item.link,
			title=item.title,
			summary=html_to_text(item.description), 
			thumb=R(ICON),
			originally_available_at=Datetime.ParseDate(item.date),
		))

	# This code below is helpful to show when a source is empty
	if len(oc) < 1:
		Log('still no value for objects')
		return ObjectContainer(header="Empty", message="Unable to display videos for this show right now.")

	return oc

@route(PREFIX + '/data')
def GetEpisodeData(url):
	page = opener.open(url).read()
	title = RE_TITLE.search(page).group('match')
	description = RE_DESCRIPTION.search(page).group('match')
	thumb = RE_THUMB.search(page).group('match')
	video = RE_VIDEO_URL.search(page).group('video_url')
	oc = ObjectContainer()
	oc.add(VideoClipObject(
		url=url + ('?video=%s' % video),
		title=title,
		summary=description,
		thumb=thumb,
	))
	return oc