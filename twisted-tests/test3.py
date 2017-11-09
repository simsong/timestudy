from twisted.python.log import err
from twisted.web.client import Agent
from twisted.internet import reactor
from twisted.internet.ssl import ClientContextFactory

class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)

def display(response):
    print "Received response"
    print response

def main():
    contextFactory = WebClientContextFactory()
    agent = Agent(reactor, contextFactory)
    d = agent.request("GET", "https://example.com/")
    d.addCallbacks(display, err)
    d.addCallback(lambda ignored: reactor.stop())
    reactor.run()

if __name__ == "__main__":
    main()
