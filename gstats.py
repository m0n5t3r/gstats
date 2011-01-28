# Copyright (c) 2010 Sabin Iacob <iacobs@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
#     The above copyright notice and this permission notice shall be included in
#     all copies or substantial portions of the Software.
# 
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#     IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#     FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#     AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#     LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#     OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#     THE SOFTWARE.

import zmq
import signal

from threading import Thread
from math import sqrt
from collections import defaultdict, deque
from time import time

class TimeRingBuffer(object):
    """
    Timed ring buffer: holds onjects passed in the last <interval> seconds
    """
    def __init__(self, interval):
        """
        :param interval: ring buffer's dimension (seconds)
        :type interval: int
        """
        self.__size = interval
        self.__things = deque()
        self.__count = 0L

    @property
    def _current_timestamp(self):
        return int(time())

    @property
    def values(self):
        return [t[1] for t in self.__things]

    @property
    def count(self):
        return self.__count

    def __len__(self):
        return len(self.__things)
     
    def append(self, val):
        ts = self._current_timestamp
        oldest = ts - self.__size

        while self.__things and self.__things[0][0] < oldest:
            self.__things.popleft()

        self.__things.append((ts, val))
        self.__count += 1

class StopThread(Exception):
    pass

class StatsCollector(Thread):
    def __init__(self, zmq_context, bind_address, buffer_length=600):
        super(StatsCollector, self).__init__()
        self.ctx = zmq_context
        self.bind_address = bind_address
        self.buffer_length = buffer_length
        self.reset_stats()

    def reset_stats(self):
        self.stats = defaultdict(lambda: {
            'started': TimeRingBuffer(self.buffer_length),
            'finished': TimeRingBuffer(self.buffer_length)
        })

    def collect_stats(self, prefix='default', req_time=0):
        stats = self.stats[prefix]
        if not req_time:
            stats['started'].append(0)
        else:
            stats['finished'].append(req_time)

    def assemble_stats(self):
        ret = {}

        for prefix, data in self.stats.items():
            started = data['started'].values
            finished = data['finished'].values

            finished_cnt = len(finished)

            if finished_cnt < 1:
                finished_cnt = 1

            time_total = sum(finished)
            time_avg = time_total / float(finished_cnt)

            ret[prefix] = {
                'started': data['started'].count,
                'finished': data['finished'].count,
                'processing_time': {
                    'avg': time_avg,
                    'std': sqrt(sum(((t - time_avg) ** 2 for t in finished)) / finished_cnt)
                }
            }

        return ret

    def die(self, *args):
        raise StopThread()

    def run(self):
        collector = self.ctx.socket(zmq.REP)
        comm = self.ctx.socket(zmq.PAIR)
        sig = self.ctx.socket(zmq.PAIR)

        collector.bind(self.bind_address)
        comm.bind('inproc://comm')
        sig.bind('inproc://signals')

        def on_collector():
            prefix, req_time = collector.recv_multipart()

            prefix = prefix or 'default'
            req_time = req_time and float(req_time) or 0

            self.collect_stats(prefix, req_time)
            collector.send('OK')

        def on_comm():
            cmd = comm.recv()
            if cmd not in commands:
                comm.send('ERROR')
                return

            ret = commands[cmd]()
            comm.send_json(ret)

        def on_sig():
            signum = int(sig.recv())

            if sig not in signals:
                return

            signals[signum]()

        commands = {
            'GET': self.assemble_stats,
        }

        signals = {
            signal.SIGQUIT: self.die,
            signal.SIGTERM: self.die,
            signal.SIGUSR1: self.reset_stats,
        }

        read_handlers  = {
            collector: on_collector,
            comm: on_comm,
            sig: on_sig,
        }

        try:
            while True:
                r,w,x = zmq.select([collector, comm, sig], [collector, comm], [])

                for s in r:
                    read_handlers[s]()

        except StopThread:
            pass

class Application(object):
    def __init__(self, zmq_context):
        self.ctx = zmq_context

    def dispatch(self, env):
        """ very simple URL dispatch, a la Cake: /zelink maps to handle_zelink """

        path = filter(None, env['PATH_INFO'].split('/'))

        handler = getattr(self, 'handle_%s' % path[0], None)
        if not handler:
            return '404 Not Found', '%(PATH_INFO)s not found' % env

        return handler(env)

    def handle__status(self, env):
        comm = self.ctx.socket(zmq.PAIR)
        comm.connect('inproc://comm')

        comm.send('GET')
        ret = comm.recv()

        comm.close()

        return '200 OK', [ret]

    def __call__(self, env, start_response):
        if env['REMOTE_ADDR'] != '127.0.0.1':
            start_response('403 Forbidden', [])
            return ['You are not allowed to see this!']
        
        status, ret = self.dispatch(env)
        start_response(status, [])
        return ret


def stop_collector(signum, frame):
    sig = get_context().socket(zmq.PAIR)
    sig.connect('inproc://signals')

    sig.send(str(signum))


def context_factory():
    context_store = []
    def inner():
        if not context_store:
            context_store.append(zmq.Context())
        return context_store[0]

    return inner

get_context = context_factory()

stats_collector = StatsCollector(get_context(), 'tcp://127.0.0.2:2345')
stats_collector.start()

# TODO find something that actually works here without waiting for zmq.select
signal.signal(signal.SIGQUIT, stop_collector)
signal.signal(signal.SIGTERM, stop_collector)

app = Application(get_context())
