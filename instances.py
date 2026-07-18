import os

import httpx
import re

class ConflictException(ValueError): pass

import stat

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


def rebase_path_for_docker(path):
    from pathlib import Path

    old_base = Path("/tmp")
    new_base = Path("/data/mcm-data")
    original_file = Path(path)

    # Calculate the path relative to the old base, then join to the new base
    relative_path = original_file.relative_to(old_base)
    return (new_base / relative_path).as_posix()
traefik_rule_matcher=re.compile(r'traefik\..*\.rule')
get_host=re.compile(r'Host\("(.*)"\)')
def spawn_player(username, player, instance,observer_key,config_dir):
    with httpx.Client(transport=httpx.HTTPTransport(uds="/var/run/docker.sock")) as client:
        payload={
            "Image": "miningbots-server",
            "Labels": {
                "traefik.enable": "true",
                f"traefik.http.routers.{username}-{instance}-{player}-mb.rule": f'Host("{username}-{instance}-{player}-mb.{os.environ["BASE_DOMAIN"]}")',
                f"traefik.http.routers.{username}-{instance}-{player}-mb.entrypoints": "https",
                f"traefik.http.routers.{username}-{instance}-{player}-mb.tls": "true",
                f"traefik.http.routers.{username}-{instance}-{player}-mb.tls.certresolver": "letsencrypt",
                f"traefik.http.services.{username}-{instance}-{player}.loadbalancer.server.port": "9003",
                "observer_key": str(observer_key) # labels must be strings
            },
            "HostConfig": {
                "NetworkMode": "mb-instances",
                    "Mounts": [
                        {
                            "Type": "bind",
                            "Source": rebase_path_for_docker(config_dir),
                            "Target": "/miningbots-server/config",
                            "ReadOnly": True
                        }
                    ],
                    "AutoRemove": True
            }
        }
        resp = client.post(f"http://localhost/containers/create",
                           params={"name":f"{username}-{instance}-{player}"},
                           json=payload)
        if resp.status_code!=201:
            if resp.status_code==409:
                raise ConflictException
            else:
                return {'success':False,'rawError':f"cannot create: http error {resp.status_code} {resp.json()}"}
        start_url = f"http://localhost/containers/{username}-{instance}-{player}/start"
        resp = client.post(start_url)
        if resp.status_code!=204: return {'success':False,'rawError':resp.json()}
        return {'success':True,'rawError':None}

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
        if response.status_code!=200:
            return None
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
