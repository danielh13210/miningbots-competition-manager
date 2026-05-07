import httpx
import re

def safe_extract(zip_file, target_dir):
    for info in zip_file.infolist():
        # Check for symlinks
        if stat.S_ISLNK(info.external_attr >> 16):
            continue

        # Build safe path
        extracted_path = os.path.join(target_dir, info.filename)
        abs_target = os.path.abspath(target_dir)
        abs_extracted = os.path.abspath(extracted_path)

        # Prevent path traversal
        if not abs_extracted.startswith(abs_target):
            continue

        zip_file.extract(info, target_dir)

traefik_rule_matcher=re.compile(r'traefik\..*\.rule')
get_host=re.compile(r'Host\("(.*)"\)')
def start_player(ownerID, player, instance):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        response = client.post(f"http://localhost/containers/{ownerID}-{instance}-{player}/start",timeout=httpx.Timeout(30.0))

        try:
            content=response.json()
        except:
            content=None
        return {'success':response.status_code==204 or response.status_code==304,'rawError':content} # return true if success
def stop_player(ownerID, player, instance):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        response = client.post(f"http://localhost/containers/{ownerID}-{instance}-{player}/stop",timeout=httpx.Timeout(30.0))
        try:
            content=response.json()
        except:
            content=None
        return {'success':response.status_code==204 or response.status_code==304,'rawError':content} # return true if success
def get_testserver_info(ownerID, player, instance):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        response = client.get(f"http://localhost/containers/{ownerID}-{instance}-{player}/json",timeout=httpx.Timeout(30.0))
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
