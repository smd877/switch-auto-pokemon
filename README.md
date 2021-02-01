# switch-auto-pokemon

Switchの Bluetooth疑似コントローラのプロジェクト  
https://github.com/mart1nro/joycontrol

と、それを拡張したプロジェクト  
https://github.com/Almtr/joycontrol-pluginloader

を、さらに拡張して画像処理とOCRを組み込んで自動操作をリッチにしてみました。

動作確認はラズパイ4で行っています。

## インストール

最初に上記2つの記事を見てください。  
一応、以下のコマンドで環境用意はできるかと思います。

```sh
$ sudo apt update
$ sudo apt install git python3-pip python3-dbus libhidapi-hidraw0 -y
$ git clone https://github.com/mart1nro/joycontrol.git ~/joycontrol
$ sudo pip3 install ~/joycontrol/
$ git clone --recursive https://github.com/Almtr/joycontrol-pluginloader.git ~/joycontrol-pluginloader
$ sudo pip3 install ~/joycontrol-pluginloader/
```

画像処理とOCRを利用するための準備

詳細は以下を確認してください  
https://smdbanana.hatenablog.com/entry/2021/01/14/022816

または以下のコマンドで用意してください。

```sh
$ sudo apt install python3-dev python3-pip python3-setuptools
$ sudo apt install libopencv-dev opencv-data
$ sudo python3 -m pip install opencv-python
$ sudo apt install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config
$ sudo python3 -m pip install tesserocr
$ sudo wget https://github.com/tesseract-ocr/tessdata_best/raw/master/jpn.traineddata -O /usr/share/tesseract-ocr/4.00/tessdata/jpn.traineddata
$ sudo wget https://github.com/tesseract-ocr/tessdata_best/raw/master/jpn_vert.traineddata -O /usr/share/tesseract-ocr/4.00/tessdata/jpn_vert.traineddata
```

このプロジェクトをcloneする

```sh
$ git clone https://github.com/smd877/switch-auto-pokemon.git ~/switch-auto-pokemon
```

処理完了を通知するためにSlackのチャット送信を利用しています。  
詳細は以下を確認してください  
https://smdbanana.hatenablog.com/entry/2021/01/30/000222

記事でも書いていますが簡単な設定は以下です。

```sh
$ sudo vi /etc/environment

// 末尾に以下追加
POST_SLACK_TOKEN_ID=取得したアクセストークン
POST_SLACK_CHANNEL_ID=送信先のチャンネルID
```

↑リスクに感じる場合は他の設定の仕方をしてください。私は面倒なのでこれで良いです。

## 動作デモ

[![](http://img.youtube.com/vi/5Pq410SAGIg/0.jpg)](http://www.youtube.com/watch?v=5Pq410SAGIg)

## 作ったものたち

- HatchEggsOCR : 孵化作業に画像処理とOCRを追加 [README_HatchEggsOCR.md](./README_HatchEggsOCR.md)