# Google カレンダーにイベントを追加

## Usage

### クローン

```shel
git clone 
```
### 環境構築
ここではconda環境を使う．

仮想環境を新規作成
```
conda create --name inputcal python=3.10
```

仮想環境に入る
```
conda activate inputcal
```

必要なライブラリをインストール
```
pip install flask google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### client_secret.jsonを作成
[クイックスタート](https://developers.google.com/calendar/api/quickstart/python?hl=ja#)に倣ってclient_secret.jsonを作成

### run

```shel
python app.py
```