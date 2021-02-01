import os
import logging
from JoycontrolPlugin import JoycontrolPlugin
# OpenCV関連
import cv2
import numpy as np
from PIL import Image
# OCR関連
from tesserocr import PyTessBaseAPI, PSM
import difflib
# Slack関連
import urllib.request, urllib.parse

logger = logging.getLogger(__name__)

# OpenCVでビデオキャプチャする際に指定するID
DEVICE_ID = 0
# ビデオキャプチャのサイズ指定
CAP_WIDTH = 1920
CAP_HEIGHT = 1080

class CustomCommon(JoycontrolPlugin):
    def __init__(self, controller_state, options):
        super().__init__(controller_state, options)
        self.setup_video()

    def setup_video(self):
        # キャプチャを開始する
        self.cap = cv2.VideoCapture(DEVICE_ID)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)

    def get_threshhold_img(self, img_path):
        # グレースケールで画像読み込み→二値化して返却
        img = cv2.imread(img_path, 0)
        ret, thresh_img = cv2.threshold(img, 0, 255, cv2.THRESH_OTSU)
        return thresh_img

    async def write_cv2_img(self, img_path, img):
        # 指定のパスに画像を保存する
        cv2.imwrite(img_path, img)

    async def open_pokemon_box(self):
        # メニューを開く
        await self.button_ctl('x', w_sec=0.5)
        # 左上のポケモンからボックスを開く
        await self.button_ctl('up', 'left', p_sec=1.0, w_sec=0.1)
        await self.button_ctl('a', w_sec=2.0)
        await self.button_ctl('r', w_sec=2.5)

    async def open_date_and_time_settings(self):
        # ホーム画面を開く
        await self.button_ctl('home', w_sec=0.8)
        # 設定を開く
        await self.button_ctl('left', w_sec=0.1)
        await self.button_ctl('down')
        await self.button_ctl('left')
        await self.button_ctl('a', w_sec=0.5)
        # メニューで「本体」を選択
        await self.button_ctl('down', p_sec=1.6)
        await self.button_ctl('a', w_sec=0.3)
        # 「日付と時刻」を選択
        await self.button_ctl('down')
        await self.button_ctl('down')
        await self.button_ctl('down')
        await self.button_ctl('down')
        await self.button_ctl('a', w_sec=0.5)
        # 「現在の日付と時刻」を選択
        await self.button_ctl('down')
        await self.button_ctl('down')
        await self.button_ctl('a', w_sec=0.3)

    async def change_year(self):
        # インターネットで現在時刻が正しいものになっている前提
        # 「現在の日付と時刻」まで移動
        await self.open_date_and_time_settings()
        # 年を1つ上げて閉じる
        await self.button_ctl('up')
        await self.button_ctl('right', w_sec=0)
        await self.button_ctl('a', w_sec=0)
        await self.button_ctl('right', w_sec=0)
        await self.button_ctl('a', w_sec=0)
        await self.button_ctl('right', w_sec=0.1)
        await self.button_ctl('a', w_sec=0.5)
        # 「インターネットで時刻をあわせる」のオンオフで日時を戻す
        await self.button_ctl('up')
        await self.button_ctl('up')
        await self.button_ctl('a', w_sec=0.3)
        await self.button_ctl('a', w_sec=0.3)
        # ゲームに戻る
        await self.button_ctl('home', w_sec=1.0)
        await self.button_ctl('a', w_sec=1.0)

    async def change_days(self, days):
        # 「現在の日付と時刻」まで移動
        await self.open_date_and_time_settings()
        # 日の位置まで移動
        await self.button_ctl('right')
        await self.button_ctl('right')
        # 日の変更
        if days >= 0:
            for _ in range(days):
                await self.button_ctl('up')
        else:
            for _ in range(days * -1):
                await self.button_ctl('down')
        await self.button_ctl('right')
        await self.button_ctl('right')
        await self.button_ctl('right')
        await self.button_ctl('a', w_sec=0.5)
        # ゲームに戻る
        await self.button_ctl('home', w_sec=1.0)
        await self.button_ctl('a', w_sec=1.0)

    async def button_ctl(self, *buttons, p_sec=0.05, w_sec=0.05):
        # ボタンの押下時間と解放後待機時間を指定する
        await self.button_press(*buttons)
        await self.wait(p_sec)
        await self.button_release(*buttons)
        await self.wait(w_sec)

    async def get_thresh_img(self, frame, x_point, y_point, x_size, y_size):
        # フレーム画像から指定領域のトリミング
        trim_img = frame[y_point : y_point + y_size, x_point : x_point + x_size]
        # トリミング画像をグレースケール
        gray_img = cv2.cvtColor(trim_img, cv2.COLOR_BGR2GRAY)
        # 二値化して返却
        ret, thresh_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_OTSU)
        return thresh_img

    async def check_nonzero(self, img1, img2, limit):
        # 要素数を比較する
        ret = np.count_nonzero(img1 == img2)
        # 要素数と、要素数が既定値を超えているかのフラグを戻り値とする。
        return ret, ret >= limit

    async def get_ocr_text(self, thresh_img):
        # OCRにかけられるように画像変換
        pil_img = Image.fromarray(thresh_img)
        # OCR処理
        api = PyTessBaseAPI(psm=PSM.AUTO, lang='jpn')
        api.SetImage(pil_img)
        # 空白文字と改行を除去して結果を返却
        return api.GetUTF8Text().replace(' ','').replace('\n','')

    async def words_match(self, word1, word2, ratio_threshold=0.6):
        # 2つの単語の類似度を取得する
        ret = difflib.SequenceMatcher(None, word1, word2).ratio()
        # 類似度と、類似度が既定値を超えているかのフラグを戻り値とする。
        return ret, ret >= ratio_threshold

    async def send_slack_message(self, msg):
        # Slackでメッセージ送信
        URL = 'https://slack.com/api/chat.postMessage'
        headers = {
                'Authorization': 'Bearer ' + os.environ.get('POST_SLACK_TOKEN_ID')
        }
        message = {
                'text' : msg,
                'channel' : os.environ.get('POST_SLACK_CHANNEL_ID')
        }
        data = urllib.parse.urlencode(message).encode("utf-8")
        req = urllib.request.Request(URL,data=data,headers=headers,method='POST')
        urllib.request.urlopen(req)
