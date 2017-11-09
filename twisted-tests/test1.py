# http://twistedmatrix.com/documents/16.4.0/web/howto/client.html

from __future__ import print_function

from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

def cbResponse(ignored):
    print('Response received:',ignored)

def cbShutdown(ignored):
    print("cbShutdown:",ignored)
    reactor.stop()

def main():
    agent = Agent(reactor)

    d = agent.request(
        'GET',
        b'https://simson.net/',
        Headers({'User-Agent': ['Twisted Web Client Example']}),
        None)

    d.addCallback(cbResponse)
    d.addBoth(cbShutdown)
    reactor.run()

if __name__=="__main__":
    main()

