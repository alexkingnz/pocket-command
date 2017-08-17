#!/usr/bin/python3
import requests
import http.server
import json
import subprocess
import sys
import appdirs
import yaml
import os

BROWSER='firefox'

class PocketRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write('<html><body>Thank you from PocketCommand</body></html>'.encode('UTF-8'))
        self.server.callback(self.requestline)

class PocketHTTPServer(http.server.HTTPServer):
    def __init__(self, port, callback):
        http.server.HTTPServer.__init__(self, ('localhost',port), PocketRequestHandler)
        self.callback = callback

class PocketCommand:
    PLATFORM_CONSUMER_KEY = "69837-cd901fd9f9a7a4538f6686cd"
    port=8910
    headers = {'Content-Type': 'application/json; charset=UTF-8', 
               'X-Accept': 'application/json'}

    def __init__(self):
        try:
            os.mkdir(appdirs.user_data_dir('pocketcommand'))
        except OSError:
            pass
        self.config_file = os.path.join(appdirs.user_data_dir('pocketcommand'),'sessiondata')

    def _post(self, path, data, phase):
        uri = 'https://getpocket.com/v3/%s' % path
        r = requests.post(uri, data = json.dumps(data),
                             headers = self.headers )
        if r.status_code != requests.codes.ok:
            print('%s to pocket failed with %d, %s' % (phase, r.status_code, r.headers['X-Error']))
            r.raise_for_status()
        return r

    def authenticate(self, online=False):
        if online:
            self.authenticate_online()
            return
        try:
            cdata = yaml.safe_load(open(self.config_file))
        except OSError:
            self.authenticate_online()
            return
        try:
            self.access_token = cdata["access_token"]
            self.username = cdata["username"]
            self.auth_from_file = True
        except (KeyError, TypeError):
            os.ulink(self.config_file)
            self.authenticate_online()


    def authenticate_online(self):
        self.server = PocketHTTPServer(self.port, self.recv_callback)
        redirect_uri = 'http://localhost:%d/reportback' % self.port
        data = {'consumer_key': self.PLATFORM_CONSUMER_KEY,
                'redirect_uri': redirect_uri}
        r = self._post('oauth/request', data, 'connecting')
        self.request_token = r.json()['code']
        uri="https://getpocket.com/auth/authorize?request_token=%s&redirect_uri=%s" % (self.request_token, redirect_uri)
        subprocess.Popen([BROWSER, uri])
        self.server.handle_request()
        print("Logging in and making a POST request...")
        data = {"consumer_key": self.PLATFORM_CONSUMER_KEY,
                "code": self.request_token}
        r = self._post('oauth/authorize', data, 'authorizing')
        self.access_token = r.json()['access_token']
        self.username = r.json()['username']
        print("Logged in as %s" % self.username)
        try:
            yaml.safe_dump({'access_token': self.access_token, 'username': self.username}, open((self.config_file),"w"))
        except:
            pass
        self.auth_from_file = False

    def recv_callback(self, url):
        pass

    def add_url(self, url):
        data = {'url': url,
                "consumer_key": self.PLATFORM_CONSUMER_KEY,
                "access_token": self.access_token}
        r = self._post('add', data, 'adding')
        if r.status_code == requests.codes.ok:
            print("Added url successfully")

if __name__=="__main__":
    url=sys.argv[1]
    p=PocketCommand()
    print("Adding %s to Pocket...." % url)
    p.authenticate()
    try:
        p.add_url(url)
    except requests.exceptions.HTTPError:
        if p.auth_from_file:
            p.authenticate(online=True)
            p.add_url(url)
        raise
