**Disclaimer:**

This program was designed for experimental purposes. It blindly downloads magnet links to acquire metadata and cannot verify the legitimacy of the publisher or the content. Use it at your own risk.

**Dependencies:**

mongod
pymongo
libtorrent-rasterbar
bencode

**To start this program:**

1. Start mongod using whatever dbpath you'd like
2. Navigate to this folder and run 'python spider.py', use -h to for more about optional arguments

The database this program builds has two collections, 'dht' and 'torrent'.

'dht' is populated by posts in the format: {'_id': infohash, 'address': [list of peer IP addresses]}
IPs are recorded to approximate popularity, which is necessary to determine how to prioritize metadata aquisition.

'torrent' is populated by posts in the format:
 {'magnet': magnet link, 'name':, torrent description, 'info': [{'path': file name, 'size': file size}]}
