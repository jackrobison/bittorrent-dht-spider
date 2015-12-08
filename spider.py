from btcrawler import Disp, Crawler, Fetcher
from Queue import Queue
from time import sleep
import sys
import argparse


def main():
    queuesize = 10
    timeout = 30

    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--queuesize", help="Number of torrents to queue")
    parser.add_argument("-t", "--timeout", help="Torrent timeout in seconds")
    args = parser.parse_args()

    if args.queuesize:
        try:
            queuesize = int(args.queuesize)
        except:
            print 'Invalid queue size, using default of 10'
    if args.timeout:
        try:
            timeout = int(args.timeout)
        except:
            print 'Invalid timeout, using default of 30 seconds'

    q = Queue()
    dht = Crawler(q, 6000)
    f = Fetcher(q, queuesize, timeout, '/dev/null')  # /dev/null in case any non metadata manages to try to download
    d = Disp(q, queuesize, timeout)

    dht.start()
    f.start()
    d.start()

    # Wait for the kill signal from the disp thread
    while q.empty():
        pass

    # Give the fetcher and dht threads a few seconds to shut down
    sleep(5)

    # Display shutdown messages
    while not q.empty():
        print q.get()

    dht.join(0)
    f.join(0)
    d.join(0)


if __name__ == '__main__':
    if not main():
        print 'Exited main'
        sys.exit(0)
