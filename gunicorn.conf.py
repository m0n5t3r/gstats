def setup_context(): # work around a bug in zmq, python dies if zmq.Context is called more than once
    if 'zmq_context' not in __builtins__:
        __builtins__['zmq_context'] = zmq.Context()

requests = {}

def pre_request(worker, req):
    setup_context()
    _collector = zmq_context.socket(zmq.REQ)
    _collector.connect('tcp://127.0.0.2:2345')

    _collector.send('')
    _collector.recv()
    requests[req] = datetime.now()

def post_request(worker, req):
    req_end = datetime.now()
    sys.stdout.flush()
    if req in requests:
        req_time = req_end - requests[req]
        req_time = req_time.seconds * 1000 + req_time.microseconds / 1000

        del requests[req]

        setup_context()
        _collector = zmq_context.socket(zmq.REQ)
        _collector.connect('tcp://127.0.0.2:2345')

        _collector.send(str(req_time))
        _collector.recv()
