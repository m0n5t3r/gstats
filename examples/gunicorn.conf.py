from gstats import start_request, end_request

_collector_addr = 'tcp://127.0.0.2:2345'
_prefix = b'my_app'

def pre_request(req, worker):
    start_request(req, collect=True, collector=_collector_addr, prefix=_prefix)

def post_request(req, worker):
    end_request(req, collector=_collector_addr, prefix=_prefix)
