import urllib
import urllib2
import threading as th
import Queue
import json
import sys
import redis
import pdb

server = redis.Redis()
CACHE_EXPIRE = 60 * 10

SEARCH_API = r'http://ws.spotify.com/search/1/track.json'
MAX_PAGES = 2

PARALLELIZATION = 5

def gen_queries(line):
    words = line.split()
    for i in range(len(words)):
        for j in range(i+1, len(words)+1):
            yield ' '.join([w.lower() for w in words[i:j]])

            
def mk_query(base_url, parameters):
    return base_url + '?' + urllib.urlencode(parameters)

    
def get_matching_songs(line):    
    
    matched_songs = {}
    matched_words = set()
    anchors = set()
    
    to_queue = Queue.Queue()
    in_queue = Queue.Queue()    
    for query in gen_queries(line):
        in_queue.put(query)
     
    for i in range(PARALLELIZATION):
        Worker(in_queue, to_queue).start()
    
    for i in range(PARALLELIZATION):
        in_queue.put(None)
    
    in_queue.join()
    
    while True:
        try:
            query, href = to_queue.get_nowait()
            if href:
                matched_songs[query] = href
                words = query.split()
                for word in words:
                    matched_words.add(word)
                anchors.add(words[0])
            if not server.exists(query):
                server.set(query, json.dumps(href))
            server.expire(query, CACHE_EXPIRE)
        except Queue.Empty:
            break

    return matched_songs, matched_words, anchors


class Worker(th.Thread):

    def __init__(self, in_queue, to_queue):
        th.Thread.__init__(self)
        self.in_queue = in_queue
        self.to_queue = to_queue
        
    def run(self):
        while True:
            query = self.in_queue.get()
            if query is None:
                self.in_queue.task_done()                
                break
            else:
                self.put_matching_track(query)
                self.in_queue.task_done()

    def put_matching_track(self, query):                
        
        if server.exists(query):
            href = json.loads(server.get(query))
            self.to_queue.put((query, href))
        else:
            matched = False
            page = 1
    
            while not matched and page <= MAX_PAGES:
        
                par = {'q':query, 'page':page}
                tracks_json = urllib2.urlopen(mk_query(SEARCH_API, par)).read()
                tracks_dict = json.loads(tracks_json)
                meta, tracks = tracks_dict['info'], tracks_dict['tracks']
                num_results = meta['num_results']
        
                for track in tracks:
                    if track['name'].lower() == query:
                        self.to_queue.put((query, track['href']))
                        return
        
                if (page - 1) * 100 + len(tracks) < num_results:
                    page += 1
                else:
                    break
        self.to_queue.put((query, None))


def accept_songs(line, matched_songs, matched_words, anchors):
        
    line = line.split()
    
    accepted_songs = []
    
    current_line = ''
    for i, word in enumerate(line):
        if word in matched_words:
            try_line = (current_line + ' ' + word).strip()
            if any(song.startswith(try_line) for song in matched_songs):
                if not i == len(line) - 1:
                    next_word = line[i+1]
                    if word in anchors \
                        and (next_word in matched_words 
                             and next_word not in anchors) \
                        and len(current_line) > 0:
                        accepted_songs.append(current_line)
                        current_line = word
                    else:
                        current_line = try_line
                else:
                    accepted_songs.append(try_line)
            else:
                if len(current_line) > 0:
                    accepted_songs.append(current_line)
                current_line = word
                if i == len(line) - 1:
                    accepted_songs.append(word)
        else:
            if len(current_line) > 0:
                accepted_songs.append(current_line)
            current_line = ''
    
    return [(s, matched_songs[s]) for s in accepted_songs]

if __name__ == '__main__':
    line = sys.argv[1].lower()
    answer = get_matching_songs(line)
    for song, url in accept_songs(line, *answer):
        print '{} @ {}'.format(song, url)
        

