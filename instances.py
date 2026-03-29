import httpx
import re
traefik_rule_matcher=re.compile(r'traefik\..*\.rule')
get_host=re.compile(r'Host\("(.*)"\)')
def start_player(player,instance):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        response = client.post(f"http://localhost/containers/{player}-{instance}/start",timeout=httpx.Timeout(30.0))

        try:
            content=response.json()
        except:
            content=None
        return {'success':response.status_code==204 or response.status_code==304,'rawError':content} # return true if success
def stop_player(player,instance):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        response = client.post(f"http://localhost/containers/{player}-{instance}/stop",timeout=httpx.Timeout(30.0))
        try:
            content=response.json()
        except:
            content=None
        return {'success':response.status_code==204 or response.status_code==304,'rawError':content} # return true if success
def get_testserver_info(player,instance):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        response = client.get(f"http://localhost/containers/{player}-{instance}/json",timeout=httpx.Timeout(30.0))
        try:
            content=response.json()
        except:
            content=None
        return content # return the test server info

def get_url(container):
    labels=container['Config']['Labels']
    for label in labels:
        if traefik_rule_matcher.match(label):
            rule=labels[label]
            if matches:=get_host.search(rule):
                return matches.group(1)
            else:
                raise KeyError
    raise KeyError

def get_observer_key(container):
    return container['Config']['Labels']['observer_key']

def is_running(container):
    return container['State']['Running']