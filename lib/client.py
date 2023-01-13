import requests
import json
import pickle
from os import path
from datetime import datetime


class InstaClient:

    # User endpoint
    url = 'https://www.instagram.com/'
    url_shared_data = 'https://www.instagram.com/api/v1/web/data/shared_data/'
    url_login = 'https://www.instagram.com/api/v1/web/accounts/login/ajax/'
    url_get_user_info = "https://www.instagram.com/api/v1/users/web_profile_info/?username=%s"

    # Media endpoint
    url_get_media_info = "https://www.instagram.com/api/v1/media/%s/info/"
    url_get_feed = "https://www.instagram.com/api/v1/feed/user/%s/username/?count=%s"
    url_like_post = "https://www.instagram.com/api/v1/web/likes/%s/like/"
    url_unlike_post = "https://www.instagram.com/api/v1/web/likes/%s/unlike/"

    # Debug Settings
    time_in_debug = True
    output_debug = False
    write_log = True

    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 105.0.0.11.118 (iPhone11,8; iOS 12_3_1; en_US; en-US; scale=2.00; 828x1792; 165586599)"

    def __init__(self, username, password, debug=False):

        # Inizio la sessione requests e archivio username e password
        self.s = requests.Session()
        self.user_login = username.lower()
        self.password_login = password
        
        self.log(f'Inizializzata la sessione per l\'utente: {self.user_login}')

        # Controllo se esiste un file di sessione per l'utente, se il recupero sessione non va a buon fine, rieseguo il login
        if path.exists(f'./sessions/{self.user_login}.pkl'):
            if not self.recoverySession():
                self.login()
        else:
            # Se non esiste eseguo nuovamente l'autenticazione
            login = self.login()

            # DEBUG
            self.log(f"Stato autenticazione: {login['status']}")

    def recoverySession(self):

        # DEBUG
        self.log("Provo a recuperare la sessione precedente")

        with open(f'./sessions/{self.user_login}.pkl', 'rb') as f:
            self.s = pickle.load(f)

        userInfo = self.getUserInfoByUsername(self.user_login)
        if userInfo['status'] == False:
            self.log(
                    'Non è stato possibile recuperare la sessione. Rieseguo l\'autenticazione.')
            return False
        else:
            self.log('Sessione recuperata correttamente.')
            return True

    """
    Function that execute login on Instagram platform

    Response:
        - status (Bool - True = OK, False = ERROR)
    """

    def login(self):

        # Richiesta alla homepage di Instagram
        self.s.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.instagram.com/',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'viewport-width': '560',
        })
        self.s.get(self.url)

        # Ottiene il CSRFTOKEN e lo aggiunge all'header
        r = self.s.get(self.url_shared_data)
        r_json = json.loads(r.text)

        self.csrf_token = r_json['config']['csrf_token']
        self.ig_did = r_json['device_id']

        self.s.headers.update({
            'x-csrftoken': self.csrf_token,
            'X-Instagram-AJAX': '1',
            'x-requested-with': 'XMLHttpRequest'
        })

        # Effettua il login con headers ottenuti
        time = int(datetime.now().timestamp())
        r_login = self.s.post(
            self.url_login,
            data={
                'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{time}:{self.password_login}',
                'username': self.user_login,
                'queryParams': {},
                'optIntoOneTap': 'false',
                'trustedDeviceRecords': {},
            },
        )
        r_login_json = json.loads(r_login.text)
        if r_login_json['status'] == 'fail':
            if 'two_factor_required' in r_login_json:
                self.two_factor_identifier = r_login_json['two_factor_info']['two_factor_identifier']
                return {
                    'status': False,
                    'error_type': "two_factor_required",
                    'message': "È richiesta l'autenticazione a due fattori."
                }
            else:
                return {
                    'status': False,
                    'error_type': "",
                    'message': r_login_json['message']
                }

        self.s.headers.update({
            "x-csrftoken": r_login.cookies['csrftoken'],
        })
                
        self.csrf_token = r_login.cookies['csrftoken']
        self.saveSession()
        return {
            'status': True
        }

    """
    Function to get user information by username.

    Params: username (String)
    Response:
        - status (Bool - True = OK, False = ERROR)
        - error_message (String)
        - data (Dict)
    """

    def getUserInfoByUsername(self, username):

        # Update Request Referer
        self.s.headers.update({
            'referer': f'https://www.instagram.com/{username}/'
        })
        r = self.s.get(self.url_get_user_info % (username))
        r_json = json.loads(r.text)

        # Check reponse status
        if 'status' in r_json:
            if r_json['status'] == 'fail':
                return {
                    'status': False,
                    'error_message': r_json['message']
                }
        return {
            'status': True,
            'error_message': None,
            'data': r_json['data'],
        }

    """
    """
    
    def getFeedByUsername(self, username, limit=12):
        
        self.s.headers.update({
            'referer': f'https://www.instagram.com/{username}/'
        })

        r = self.s.get(self.url_get_feed % (username, limit))
        r_json = json.loads(r.text)

        return {
            'status': True,
            'items': r_json['items'],
        }

    def likePost(self, post_id, post_code):

        self.s.headers.update({
            'referer': f'https://www.instagram.com/p/{post_code}/'
        })

        r = self.s.post(self.url_like_post % (post_id))
        r_json = json.loads(r.text)

        if 'status' in r_json:
            if r_json['status'] == 'ok':
                return True
        return False

    def unlikePost(self, post_id, post_code):
        self.s.headers.update({
            'referer': f'https://www.instagram.com/p/{post_code}/'
        })

        r = self.s.post(self.url_unlike_post % (post_id))
        r_json = json.loads(r.text)

        if 'status' in r_json:
            if r_json['status'] == 'ok':
                return True
        return False

    def saveSession(self):
        f = open(f'./sessions/{self.user_login}.pkl', 'wb')
        pickle.dump(self.s, f)

    """
    Function that define log format.

    TIME IN DEBUG:
        - [InstaClient] (DATE TIME): OUTPUT MESSAGE.

    NO TIME IN DEBUG:
        - [InstaClient]: OUTPUT MESSAGE.

    """

    def log(self, text):

        # Manage log in console and in file
        now = datetime.now()
        if self.write_log:
            f = open('latest.log', 'a')
            f.write(f'[InstaClient] ({now.strftime("%d/%m/%Y %H:%M:%S")}): {text}\n')
            f.close()
        
        if self.output_debug:
            if self.time_in_debug:
                print(f'[InstaClient] ({now.strftime("%d/%m/%Y %H:%M:%S")}): {text}')
            else:
                print(f'[InstaClient]: {text}')