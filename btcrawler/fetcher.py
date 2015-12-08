import libtorrent as lt
import datetime
import socket
from threading import Timer, Thread
from time import sleep
from pymongo import MongoClient


class Fetcher(Thread):
    def __init__(self, q, quantity, timeout, save_path):
        Thread.__init__(self)
        self.setDaemon(True)
        self.q = q
        self.quantity = quantity
        self.timeout = timeout
        self.params = {
            'save_path': save_path,
            'storage_mode': lt.storage_mode_t(2),
            'paused': False,
            'auto_managed': False,
            'duplicate_is_error': True,
            'dont_count_slow_torrents': True,
            'flag_upload_mode': True
        }
        self.ses = lt.session()
        self.ses.set_upload_rate_limit(0)
        self.ses.set_download_rate_limit(2048 * self.quantity)  # Limit the download speed to 2kbps per torrent
        conn = MongoClient()
        mongodht = conn['dht']
        mongotorrent = conn['torrent']
        self.magnetposts = mongodht.posts
        self.torrentposts = mongotorrent.posts

    def run(self):
        self.ses.add_dht_router(socket.gethostbyname_ex('router.bittorrent.com')[2][0], 6881)
        self.ses.add_dht_router(socket.gethostbyname_ex('router.utorrent.com')[2][0], 6881)
        self.ses.start_dht()
        self.handles = []
        self.skip = []
        self.cnt = 0
        self.done = [i for i in self.torrentposts.find()]
        t = []
        magnets = []

        # main loop, runs until the the gui sends a kill signal to the Queue()
        while self.q.empty():
            self.cnt += 1
            t += [i for i in
                 self.magnetposts.find().skip(len(magnets))]  # get new magnet links and sort them by peer count
            magnets = ['magnet:?xt=urn:btih:' + i['_id'] for i in
                       [q for q in sorted(t, key=lambda t: len(t['address']), reverse=True)]]

            # remove completed, skipped, and magnets currently being downloaded from the list
            for i in self.done:
                try:
                    magnets.remove(i['magnet'])
                except:
                    pass
            for i in self.skip:
                try:
                    magnets.remove(i)
                except:
                    pass
            for h in self.handles:
                try:
                    magnets.remove(h[2])
                except:
                    pass

            # if there are enough remaining torrents in the list, check to see if more should be added to the dl queue
            if len(magnets) > self.quantity:
                if len(self.handles) < self.quantity:
                    i = 0
                    while True:
                        try:
                            magnet = magnets[i]
                            h = lt.add_magnet_uri(self.ses, str(magnet), self.params)
                            h.set_download_limit(2048)
                            h.set_upload_limit(0)
                            self.handles.append([h, datetime.datetime.now(), magnet])
                        except:
                            pass
                        i += 1
                        if len(self.handles) >= self.quantity:
                            break

            # Check queued torrents to see if they have aquired metadata or timed out, remove them if they have
            for handle, starttime, m in self.handles:
                if handle.has_metadata():
                    info = handle.get_torrent_info()
                    tinfo = {'magnet': str(m), 'name': str(info.name()),
                             'info': [{'path': str(f.path), 'size': str(f.size)} for f in info.files()]}
                    if not tinfo in self.torrentposts.find():
                        self.torrentposts.insert(tinfo)  # only insert new torrent record if it isn't there already
                    handle.pause()
                    self.handles.remove([handle, starttime, m])
                    self.done.append(tinfo)
                if (datetime.datetime.now() - starttime).total_seconds() > self.timeout:
                    handle.pause()
                    try:
                        self.handles.remove([handle, starttime, m])
                    except:
                        pass
                    self.skip.append(m)

        # upon exiting the main loop stop all queued torrents
        try:
            for handle, starttime in self.handles:
                handle.pause()
                self.handles.remove(handle)
        except ValueError:
            pass
        self.ses.stop_dht()
        del self.ses
        self.q.put('fetcher shutdown')
        sleep(1)
