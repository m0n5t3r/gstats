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
from datetime import datetime

requests = {}

def context_factory():
    context_store = []
    def inner():
        if not context_store:
            context_store.append(zmq.Context())
        return context_store[0]

    return inner

get_context = context_factory()

collector_addr = 'tcp://127.0.0.2:2345'

def pre_request(worker, req):
    _collector = get_context().socket(zmq.REQ)
    _collector.connect(collector_addr)

    _collector.send_multipart(['my_app', ''])
    _collector.recv()
    requests[hash(req)] = datetime.now()

def post_request(worker, req):
    req_end = datetime.now()
    req = hash(req)

    if req in requests:
        req_time = req_end - requests[req]
        req_time = req_time.seconds * 1000 + req_time.microseconds / 1000

        del requests[req]
        
        _collector = get_context().socket(zmq.REQ)
        _collector.connect(collector_addr)

        _collector.send_multipart(['my_app', str(req_time)])
        _collector.recv()

