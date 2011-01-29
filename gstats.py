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
        comm.connect('ipc://collectd_comm')

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
    sig.connect('ipc://collectd_signals')

    sig.send(str(signum))


def context_factory():
    context_store = []
    def inner():
        if not context_store:
            context_store.append(zmq.Context())
        return context_store[0]

    return inner

get_context = context_factory()

# TODO find something that actually works here without waiting for zmq.select
signal.signal(signal.SIGQUIT, stop_collector)
signal.signal(signal.SIGTERM, stop_collector)

app = Application(get_context())
