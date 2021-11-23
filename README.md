# PYTHON PARSING AND SUMMARIZING
By using this project, we can parse data from coinmarketcap and save it to the db. Also, with the help of transformers user can get the summary of parsed paragraphs. 

## Installation
```
pip install flask
pip install flask-sqlalchemy
pip install bs4
pip install selenium
pip install webdriver_manager
pip install transformers
pip install jwt
pip install werkzeug.utils
```

## Usage
```
from flask import Flask, request, jsonify, make_response, session, render_template
from flask.templating import render_template
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from transformers import pipeline
import jwt
from datetime import datetime, timedelta 
from werkzeug.utils import redirect
```
## Examples

![image](https://user-images.githubusercontent.com/80178491/143136614-84721774-2bf8-4dcb-8144-fc3961d45672.png)
