import httpx
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
