#!/usr/bin/python

__author__ = 'duh'

from StringIO import StringIO
import gzip
import urllib2
import re
import urllib
import os
import sys
import getopt
import dataset
import ssl
from texttable import Texttable
from prettytable import PrettyTable
from BeautifulSoup import BeautifulSoup

help_menu = "Usage: pirate_foot [option]...[arg]\n\
            Pirate foot download requested .torrent file from kickasstorrents site.\n\n\
            Option and arguments:\n\
                -a  --all     [id]                                    : Download all the episodes from all seasons.\n\
                -s  --season  [id] [season number]                    : Download all the episodes of the seasaon.\n\
                -e  --episode [id] [season number] [epiosode number]  : Download selected epiosode of the season.\n\
                -h  --help                                            : Print this help message.\n\
                -l  --dblist                                          : List all stored shows in database.\n\
                -i  --dbinsert link                                   : Add new show do database.\n\
                -d  --dbdel id                                        : Delete show [by id] form database.\n\n\
            Examples: \n\
                pirate_foot -a 1\n\
                pirate_foot -e 1 3 4\n\
                priate_foot -i https://link_to_the_torrent\n"


######### CONFIG ##############

# Path have to have / (slash) on the end
torrent_path = '/data/DOWNLOAD/torrenty/'
#torrent_path = './temp_dir/'

if not os.path.isdir(torrent_path):
    os.system('mkdir %s' % torrent_path)


if os.path.isfile('./ship.db'):
    db = dataset.connect('sqlite:///ship.db')
else:
    db = dataset.connect('sqlite:///ship.db')
    db.query('CREATE TABLE links (id integer primary key, link text, directory text);')


def get_soup(s_url):
    try:
        header = { 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/47.0.2526.73 Chrome/47.0.2526.73 Safari/537.36'}
        req = urllib2.Request(s_url, None, header)
        page = urllib2.urlopen(req)
    except urllib2.URLError, e:
        print "There was an error: %r" % e
        #exit()

    gzipped = page.info().get('Content-Encoding') == 'gzip'

    #dekodowanie pobranej tresci jezeli jest gzip
    if gzipped:
        buf = StringIO(page.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = page

    soup = BeautifulSoup(data)
    return soup


def get_links_list(s_url):
    s_arr = [] #tablica ze slownikami nr odcinka : link do odcinka
    s_t = [] #tablica z liczba sezonow
    e_t = [] #tablica z liczba odcinkow
    l_t = [] #tablica z linkami

    soup = get_soup(s_url)
    links = soup.findAll('a', attrs={'class': 'infoListCut'}) #odnajduje wszystkie linki do odcinkow
    seasons = soup.findAll('h3') #odnajduje wszystkie tagi h3

    #wyszukanie nazwy sezonow sposrod wszystkich tagow h3
    for s in seasons:
        sn = re.search(r'Season [0-9]{2}', str(s))
        if sn:
            s_t.append(sn.group()[-2:])


    for l in links:
        l = str(l)
        id = re.search(r'\'(\d)\w+\'', l) #wyszukiwanie id linku z torrentami per odcinek
        ep = re.search(r'Episode [0-9]{2}', l) #wyszukiwanie numerow odcinkow
        if id:
            e_t.append(ep.group()[-2:])
            l_t.append('https://kickass.to/media/getepisode/' + id.group().replace("'",""))

    x = 0
    i = 0

    while (x < len(s_t)):
        s_arr.append([]) #dodanie tablicy jako kolejny element s_arr

        while (i < len(e_t)):

            s_arr[x].append({e_t[i]:l_t[i]}) #dodanie slownika nr_odcinka : link do odcinka

            e_t.pop(i)
            l_t.pop(i) #usuniecie numer odcinka i linku ktore zostaly juz dodane do s_arr

            #warunek aby nie dodawac pustych wpisow
            if len(e_t) > 0:
                if e_t[i] > s_arr[x][-1].keys()[0]:
                    break
        x += 1
    return s_arr

def get_file(t_url):

    soup = get_soup(t_url)
    links = soup.findAll('tr', attrs={'class':['odd','even']})

    if links:
        c = 0
        for l in links:
            l = str(links[c]) #zamian w string kazdego elementu tablicy links
            f_size = re.search(r'(?<=<td\ class="nobr\ center">)(.*)(?=span>)(.*)(?=</span></td>)',l) #wyszukiwanie rozmiaru pliku
            fs = f_size.group().split(' <span>')
            if fs[1] == 'GB':
                if fs[0] >= 1.5:
                    print '%s %s: file size too large' % (fs[0], fs[1])
                    c += 1
            else:
                print '%s %s: file size ok' % (fs[0], fs[1])
                break

        t_link = re.search(r'\/\/\w+\.net\/\w+\/(\d|\w+)\.torrent', l) #wyszukiwanie link do torrentu
        f_name = re.search(r'(?<=\?title=)(.*)(?=" )', l) #wyszukiwanie nazwy dla pliku torrent


        if t_link:
            tl = t_link.group() # Returns one or more subgroups of the match
            fn = f_name.group() + '.torrent.gz'
            tl = 'http:' + tl
            d_path = torrent_path + fn

	    os.system('wget --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/47.0.2526.73 Chrome/47.0.2526.73 Safari/537.36" --no-check-certificate %s -O %s' % (tl, d_path))
            os.system('gzip -d %s' % d_path)
    else:
        print "There was an error: No links for this episode"

def get_torrents(surl,tod,season,episode):
    all_links = get_links_list(surl)
    all_links.reverse()
    season = int(season)
    episode = int(episode)
    se = season-1
    ep = episode

    if tod == 'all':
        i = 0
        print 'Downloading all seasons'
        print all_links
        while i < len(all_links):
            for l in all_links[i]:
                link = l.values()[0]
                print "link %s" % link
                get_file(link)
            i += 1

    elif tod == 'season':
        if season > len(all_links):
            print "There was an error: A non-existen season"
        else:
            print 'Downloading whole season : %i' % season
            print all_links[se]
            for l in all_links[se]:
                link = l.values()[0]
                print "link %s" % link
                get_file(link)

    elif tod == 'episode':
        if season > len(all_links):
            print "There was an error: A non-existen season"
        elif episode > len(all_links[se]):
            print episode
            print len(all_links[se])
            print "There was an error: A non-existen episode"
        else:
            print 'Downloading episode : %i from season : %i' % (episode,season)
            print all_links[se][-ep]
            link = all_links[se][-ep].values()[0]
            get_file(link)


def ship(arg,parm1=0,parm2=0,parm3=0):

    #db = dataset.connect('sqlite:///ship.db')

    table = db['links']


    def print_table():
        t = PrettyTable(['Id','Directory','Link'])
        for l in db['links']:
            t.add_row([l['id'],l['directory'],l['link']])
        print t

    if arg == '-i':
        ids = db.query('SELECT id FROM links GROUP BY id')

        tempr = []
        for r in ids:
            tempr.append(r['id'])

        if len(tempr) != 0:
            missing_id = set(range(tempr[len(tempr)-1])[1:]) - set(tempr)
            if not missing_id:
                new_id = len(tempr)+1
                link_dir = re.search(r'(?<=https:\/\/kat.cr\/)(.*)(?=-tv)',str(parm1))
                table.insert(dict(id=new_id, directory=link_dir.group()+"/", link=parm1))
            else:
                new_id = list(missing_id)[0]
                link_dir = re.search(r'(?<=https:\/\/kat.cr\/)(.*)(?=-tv)',str(parm1))
                table.insert(dict(id=new_id, directory=link_dir.group()+"/", link=parm1))
        else:
            link_dir = re.search(r'(?<=https:\/\/kat.cr\/)(.*)(?=-tv)',str(parm1))
            table.insert(dict(directory=link_dir.group()+"/", link=parm1))

        print_table()

    if arg == '-l':
        print_table()

    if arg == '-d':
        table.delete(id=parm1)
        print_table()


def main(argv):

    try: 
        opts, args = getopt.getopt(argv, "aeshidl", ["all", "episode", "season", "help","dbinsert","dbdel","dblist"])
    except getopt.GetoptError:
        print (help_menu)
        sys.exit()

    if (len(sys.argv) == 1) or (len(opts) == 0):
        print (help_menu)
        sys.exit()

    # Funtion check if id given in script argument is in db and if yes gets it. 
    def getdid():
        did = 'null'

        try:
            gotid = sys.argv[2]
        except IndexError:
            gotid = 'null'

        if (gotid != 'null'):
            q = db.query("SELECT link FROM links WHERE id= :id", id=gotid)
            q = list(q)

            if q:
                for row in q:
                    did = row['link']
            else:
                print "ID does not exists"
                sys.exit()

        return did

    

    for opt, arg in opts:

        # Select all id and convert query to list
        q = db.query("SELECT id FROM links")
        q = list(q)

        # If database is empty allow only insert statment 
        if not q and opt in ("-i", "--dbinsert"):
            print "add"
            ship(sys.argv[1],sys.argv[2])
            sys.exit()
        elif not q:
            print "There is no links stored in database. Please add one."
            print help_menu
            sys.exit()


        if opt in ("-a", "--all"):
            print "Downloading all the epiosedes from all seasons."   
            #gdid = getdid()[0]
            get_torrents(getdid(),'all',0,0)
    
        elif opt in ("-e", "--episode"):
            print "Downloading episode %s from season %s" % (sys.argv[4],sys.argv[3])
            #gdid = getdid()[0]
            get_torrents(getdid(),'episode',sys.argv[3],sys.argv[4])

        elif opt in ("-s", "--season"):
            print "Downloading all the episodes from season %s" % sys.argv[3]
            #gdid = getdid()[0]
            get_torrents(getdid(),'season',sys.argv[3],0)

        elif opt in ("-i", "--dbinsert"):
            print "add"
            ship(sys.argv[1],sys.argv[2])
        elif opt in ("-d", "--dbdel"):
            print "del"
            ship(sys.argv[1],sys.argv[2])
        elif opt in ("-l", "--dblist"):
            print "list"
            ship(sys.argv[1])
        elif opt in ("-h", "--help"):
            print help_menu
            sys.exit()
   

if __name__ == "__main__":
    main(sys.argv[1:])