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
from time import time

requests = {}

def context_factory():
    context_store = []
    def inner():
        if not context_store:
            context_store.append(zmq.Context())
        return context_store[0]

    return inner

get_context = context_factory()

def start_request(req, collect=False, collector_addr='tcp://127.0.0.2:2345', prefix='my_app'):
    """
    register a request

    registers a request in the internal request table, optionally also sends it to the collector

    :param req: request, can be mostly any hash-able object
    :param collect: whether to send the request started event to the collector (bool)
    :param collector_addr: collector address, in zeromq format (string, default tcp://127.0.0.2:2345)
    :param prefix: label under which to register the request (string, default my_app)
    """

    if collect:
        collector = get_context().socket(zmq.PUSH)

        collector.connect(collector_addr)
        collector.send_multipart([prefix, ''])
        collector.close()

    requests[hash(req)] = time()

def end_request(req, collector_addr='tcp://127.0.0.2:2345', prefix='my_app'):
    """
    registers the end of a request

    registers the end of a request, computes elapsed time, sends it to the collector

    :param req: request, can be mostly any hash-able object
    :param collector_addr: collector address, in zeromq format (string, default tcp://127.0.0.2:2345)
    :param prefix: label under which to register the request (string, default my_app)
    """

    req_end = time()
    hreq = hash(req)

    if hreq in requests:
        req_time = req_end - requests[hreq]
        req_time *= 1000

        del requests[hreq]
        
        collector = get_context().socket(zmq.PUSH)

        collector.connect(collector_addr)
        collector.send_multipart([prefix, str(req_time)])
        collector.close()()

        return req_time

