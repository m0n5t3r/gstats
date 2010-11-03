import zmq
import signal

from threading import Thread
from math import sqrt

class StopThread(Exception):
    pass

class StatsCollector(Thread):
    def __init__(self, zmq_context):
        super(StatsCollector, self).__init__()
        self.ctx = zmq_context
        self.reset_stats()

    def reset_stats(self):
        self.requests_started = 0
        self.requests_finished = 0
        self.request_time = 0
        self.request_time_avg = 0
        self.request_time_std = 0

    def collect_stats(self, req_time):
        if not req_time:
            self.requests_started += 1
        else:
            self.requests_finished += 1
            self.request_time += req_time
            self.request_time_avg = float(self.request_time) / self.requests_finished
            self.request_time_std += (req_time - self.request_time_avg) ** 2

    def assemble_stats(self):
        return {
            'started': self.requests_started,
            'finished': self.requests_finished,
            'processing': self.requests_started - self.requests_finished,
            'processing_time': {
                'avg': self.request_time_avg,
                'std': sqrt(float(self.request_time_std) / float(self.requests_finished or 1)),
                'total': self.request_time,
            }
        }

    def die(self, *args):
        raise StopThread()

    def run(self):
        collector = self.ctx.socket(zmq.REP)
        comm = self.ctx.socket(zmq.PAIR)
        sig = self.ctx.socket(zmq.PAIR)

        collector.bind('tcp://127.0.0.2:2345')
        comm.bind('inproc://comm')
        sig.bind('inproc://signals')

        def on_collector():
            req_time = collector.recv()
            req_time = req_time and float(req_time) or 0
            self.collect_stats(req_time)
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
    sig = zmq_context.socket(zmq.PAIR)
    sig.connect('inproc://signals')

    sig.send(str(signum))


if 'zmq_context' not in __builtins__:
    __builtins__['zmq_context'] = zmq.Context()

stats_collector = StatsCollector(zmq_context)
stats_collector.start()

# TODO find something that actually works here without waiting for zmq.select
signal.signal(signal.SIGQUIT, stop_collector)
signal.signal(signal.SIGTERM, stop_collector)

app = Application(zmq_context)
