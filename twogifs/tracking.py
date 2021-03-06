"""Anonymous tracking! Yay!"""
from os import getenv
from multiprocessing import Pool

from mixpanel import Mixpanel

mp = Mixpanel(getenv('MIXPANEL_TOKEN'))
pool = Pool(2)


user_id = lambda session: session.get('uid', 'anon')
request_metadata = lambda request: {
    '$browser': request.user_agent.browser,
    '$browser_version': request.user_agent.version,
    '$initial_referrer': request.args.get('ref', request.referrer),
    'ip': request.access_route[0], }


def track_vote(request, session, up, down):
    properties = request_metadata(request)
    properties.update({'up': up, 'down': down})

    pool.apply_async(mp.track, [user_id(session), 'vote', properties])
