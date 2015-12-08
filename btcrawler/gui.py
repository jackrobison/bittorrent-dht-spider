import curses
from threading import Thread
from time import sleep
from pymongo import MongoClient
import locale


class Disp(Thread):
    def __init__(self, q, queuesize, timeout):
        Thread.__init__(self)
        self.setDaemon(True)
        locale.setlocale(locale.LC_ALL, '')
        self.code = locale.getpreferredencoding()
        self.q = q
        self.queuesize = queuesize  # number of torrents to try at a time
        self.timeout = timeout  # torrent timeout
        self.conn = MongoClient()
        self.torrentposts = self.conn['torrent'].posts
        self.dhtposts = self.conn['dht'].posts
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        self.stdscr.nodelay(0)

    def redraw(self, m, t, p):
        # refresh the torrent browser, show 40 torrents at a time
        self.stdscr.clear()
        self.stdscr.addstr(1, 1, "Bittorrent crawler")
        self.stdscr.addstr(2, 1, str(m) + " magnet links")
        self.stdscr.addstr(2, 25, "Up/down to navigate, r to refresh, s to search, q to quit")
        self.stdscr.addstr(3, 1, str(len(t)) + " torrents")
        self.stdscr.addstr(3, 17, "Cursor position: " + str(p))
        self.stdscr.addstr(4, 1, "Queue size: " + str(self.queuesize) + " torrents, timeout: " + str(
            self.timeout) + " seconds")
        self.stdscr.addstr(5, 1, "****************************************************************")
        cnt = 6
        pos = p
        while True:
            # Some strings don't play nice (addstr ERR), this is a temporary workaround
            try:
                self.stdscr.addstr(cnt, 1, str(t[pos]['name']).encode(self.code))
                cnt += 1
                pos += 1
            except:
                if pos < len(t):
                    pos += 1
                else:
                    break
            if cnt >= 46:
                break
        self.stdscr.refresh()

    def search(self, t):
        # Get a search keyword, and check to see if it exists in any of known torrent descriptions
        self.stdscr.clear()
        curses.echo()
        self.stdscr.addstr(1, 1, str(len(t)) + " searchable torrents")
        self.stdscr.addstr(2, 1, "Enter a search: ")
        self.stdscr.refresh()
        s = self.stdscr.getstr(2, 17)
        curses.noecho()
        r = [i for i in self.torrentposts.find() if str(s).lower() in i['name'].lower()]
        self.stdscr.addstr(3, 1, '********************')
        self.stdscr.addstr(4, 1, "Press enter to return to main screen")
        self.stdscr.addstr(5, 1, '********************')
        cnt = 0
        for i in r:
            try:
                self.stdscr.addstr(cnt + 6, 1, "Magnet: " + str(i['magnet']) + " | " + str(i['name']))
                cnt += 1
            except:
                pass
        self.stdscr.refresh()
        # Wait for the user to press enter
        j = self.stdscr.getstr(1, 1)

    def run(self):
        c = None
        pos = 0  # cursor position in the browser
        torrents = [i for i in self.torrentposts.find()]
        mag = self.dhtposts.count()
        self.redraw(mag, torrents, pos)

        while c != ord('q'):
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                if pos > 0:
                    pos -= 1
                    self.redraw(mag, torrents, pos)
            elif c == curses.KEY_DOWN:
                if pos + 51 < len(torrents):
                    pos += 1
                    self.redraw(mag, torrents, pos)
            elif c == ord('r'):
                # only find torrents added since the last refresh
                torrents += [i for i in self.torrentposts.find().skip(len(torrents))]
                mag = self.dhtposts.count()
                self.redraw(mag, torrents, pos)
            elif c == ord('s'):
                torrents = [i for i in self.torrentposts.find()]
                mag = self.dhtposts.count()
                self.search(torrents)
                self.redraw(mag, torrents, pos)

        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()
        self.q.put('disp shutdown')
        sleep(1)
