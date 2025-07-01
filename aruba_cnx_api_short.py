import json
import sys
import os
import requests
import time
from datetime import datetime
import threading
import signal
from collections import OrderedDict

base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
filename_param = "aruba_cnx_api_param.json"
path_param = os.path.join(base_path, filename_param)
path_result = "" #パラメータで取得

# グローバル変数でトークン管理
# ==== クライアント保持 ====
clients = []

token_info = {
    "access_token": None,
    "token_type": None,
    "expires_in": 3600  # default
}

# CTRL+C で停止したら終了
def quit_handler(signal, frame):
	print('quit')
	sys.exit(0)

def gen_token():
    url = "https://sso.common.cloud.hpe.com/as/token.oauth2"
    payload = {
        "client_id" : aruba_param['CLIENT_ID'],
        "client_secret" : aruba_param['CLIENT_SECRET'],
        "grant_type" : "client_credentials"
    }
    headers = {
        "accept": "*/*",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=payload, headers=headers, verify=False)

    # 結果の表示
    if response.status_code == 200:
        token_data = response.json()
        #print("Access Token:", token_data["access_token"])
        update_token_info(response.json())
        #print(token_data)
        #print(token["access_token"])
    else:
        print("Generate token failed.")

def update_token_info(data):
    token_info["access_token"] = data["access_token"]
    token_info["token_type"] = data["token_type"]
    token_info["expires_in"] = data["expires_in"]
    print("[OK] Access Token Updated")
    print("Access Token (short):", token_info["access_token"][:20], "...")

    # 次回リフレッシュタイミング（例：90%の時間経過で更新）
    refresh_in = int(token_info["expires_in"] * 0.9)
    t = threading.Timer(refresh_in, gen_token)
    t.daemon = True
    t.start()
    print(f"[TIMER] Next token refresh scheduled in {refresh_in} seconds")

def call_api():
    cur_time = datetime.now()
    strCurTime = cur_time.strftime('%Y/%m/%D %H:%M:%S')
    print(f"{cur_time} ... call API: {aruba_param['API_METHOD']} {aruba_param['API_REQUEST']}")
    url = f"https://{aruba_param['BASE_URL']}{aruba_param['API_REQUEST']}"
    payload = aruba_param["API_PARAM"]
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {token_info['access_token']}",
    }

    if(aruba_param["API_METHOD"] == 'GET'):
        response = requests.get(url, params=payload, headers=headers, verify=False)
    elif(aruba_param["API_METHOD"] == 'POST'):
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = requests.post(url, data=payload, headers=headers, verify=False)
    elif(aruba_param["API_METHOD"] == 'DELETE'):
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = requests.delete(url, data=payload, headers=headers, verify=False)
    elif(aruba_param["API_METHOD"] == 'PATCH'):
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = requests.patch(url, data=payload, headers=headers, verify=False)
    elif(aruba_param["API_METHOD"] == 'PUT'):
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = requests.put(url, data=payload, headers=headers, verify=False)

    # 結果の表示
    if response.status_code == 200:
        response_data = response.json()
        write_result(response_data)
        print(response_data)
    else:
        print("API request failed.")
        print(response)

# ==== 結果出力 ====
def write_result(result_json):
    cur_time = datetime.now()
    strCurTime = cur_time.strftime('%Y/%m/%D %H:%M:%S')
    pretty_json = json.dumps(result_json, sort_keys=True, indent=2)
    with open(path_result, mode='a', encoding="utf-8") as f:
        f.write(strCurTime)
        f.write('\n')
        f.write(pretty_json)
        f.write('\n\n')
        f.close()

# ==== 設定読み込み ====
def read_param():
    try:
        with open(path_param, 'r', encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error: Cannot open param file. ", e)
        sys.exit(1)


# ==== メイン実行 ====
if __name__ == "__main__":
    aruba_param = read_param()
    filename_result = aruba_param["RESULT_FILENAME"]
    path_result = os.path.join(base_path, filename_result)
    gen_token()

	# CTRL+C をキャッチ
    signal.signal(signal.SIGINT, quit_handler)

    #SLEEP_SEC が 0 ならループせずに終了
    if(aruba_param["SLEEP_SEC"] == 0):
        sys.exit(0)

    while(True):
        call_api()
        time.sleep(aruba_param["SLEEP_SEC"])
