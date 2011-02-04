#!/usr/bin/env python

import sys

from random import random
from time import sleep
from threading import Thread, active_count

execfile('gunicorn.conf.py')

class Worker(Thread):
    def __init__(self, nreq):
        super(Worker, self).__init__()
        self.nreq = nreq

    def run(self):
        """
        generate <nreq> requests taking a random amount of time between 0 and 0.5 seconds
        """
        for i in xrange(self.nreq):
            req = '%s_%s' % (self.ident, i)
            pre_request(None, req)
            sleep(random() / 2)
            post_request(None, req)


if __name__ == '__main__':
    # simulate workload: <sys.argv[1]> workers serving <sys.argv[2]> requests each
    workers = []

    nw = int(sys.argv[1])
    nr = int(sys.argv[2])

    for n in range(nw):
        t = Worker(nr)
        t.start()
        workers.append(t)
        print '%s started' % t.name

    while active_count() > 1:
        for t in workers:
            if t.is_alive():
                t.join(0.1)
                if not t.is_alive():
                    print '%s finished' % t.name

