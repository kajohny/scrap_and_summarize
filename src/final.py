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

app = Flask(__name__)

app.config['SECRET_KEY'] = 's3cr3tk3y'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/python'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQLAlchemy(app)

summarizer = pipeline('summarization')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column('id', db.Integer, primary_key=True)
    login = db.Column('login', db.String(50))
    password = db.Column('password', db.String(255))
    token = db.Column('token', db.String(255))
    def __init__(self, login, password):
        self.login = login
        self.password = password

class News(db.Model):
    __tablename__ = 'news'
    id = db.Column('id', db.Integer, primary_key=True)
    coin_name = db.Column('coin_name', db.String(50), index=True, unique=True)
    news_paragraph = db.Column('news_paragraph', db.Text)
    news_summary = db.Column('news_summary', db.Text)
    def __init__(self, coin_name, news_paragraph, news_summary):
        self.coin_name = coin_name
        self.news_paragraph = news_paragraph
        self.news_summary = news_summary

class Blogs(db.Model):
    __tablename__ = 'blogs'
    id = db.Column('id', db.Integer, primary_key=True)
    coin_name = db.Column('coin_name', db.String(50), index=True, unique=True)
    blogs_paragraph = db.Column('blogs_paragraph', db.Text)
    blogs_summary = db.Column('blogs_summary', db.Text)
    def __init__(self, coin_name, blogs_paragraph, blogs_summary):
        self.coin_name = coin_name
        self.blogs_paragraph = blogs_paragraph
        self.blogs_summary = blogs_summary
db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password: 
        return make_response('Please, your login and password', 401, {'WWW-Authenticate':'Basic realm="Login required"'})
    user = User.query.filter_by(login = auth.username).first()
    if not user: 
        return make_response('Could not found a user with login: ' + auth.username, 401, {'WWW-Authenticate':'Basic realm="Login required"'})
    if (user.password, auth.password):
        token = jwt.encode({'id' : user.id, 'exp' : datetime.utcnow() + timedelta(seconds = 30)}, app.config['SECRET_KEY'])
        update_token = User.query.filter_by(id = user.id).first()
        update_token.token = token
        session['token'] = token
        db.session.commit()
        return jsonify({'token' : token})
    return make_response('Could not verify', 401, {'WWW-Authenticate':'Basic realm="Login required"'})

@app.route('/logout')
def logout():
    session['token'] = None
    return redirect('/')

@app.route('/protected', methods = ['GET'])
def pass_token():
    token = request.args.get('token')
    user = User.query.filter_by(token = token).first()
    if not user:
        return 'Hello, could not verify the token'
    return 'Hello, token which is provided is correct'
    
def summarize(text):
    text = text.replace('.', '.<eos>')
    text = text.replace('!', '!<eos>')
    text = text.replace('?', '?<eos>')
    sentences = text.split('<eos>')
    max_chunk = 500
    current_chunk = 0
    chunks = []
    for sentence in sentences:
        if len(chunks) == current_chunk + 1:
            if len(chunks[current_chunk]) + len(sentence.split(' ')) <= max_chunk:
                chunks[current_chunk].extend(sentence.split(' '))
            else:
                current_chunk += 1
                chunks.append(sentence.split(' '))
        else:
            chunks.append(sentence.split(' '))
    for chunk_id in range(len(chunks)):
        chunks[chunk_id] = ' '.join(chunks[chunk_id])
    res = summarizer(chunks, max_length = 120, min_length = 30, do_sample = False)
    paragraph = ' '.join([summ['summary_text'] for summ in res])
    return paragraph

@app.route('/news', methods=['GET', 'POST'])
def news():
    if not session.get('token'):
        return redirect("/login")
    else:
        if request.method == 'POST':
            coin = request.form.get('coin')
            results = News.query.filter_by(coin_name = coin).first()

            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            driver = webdriver.Chrome(ChromeDriverManager().install(), options = options)
            driver.get('https://coinmarketcap.com/currencies/' + coin + '/news/')
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            newsList = soup.select('p.sc-1eb5slv-0.svowul-3.ddtKCV')
            text = [lists.text for lists in newsList]
            paragraph = ' '.join(text)
            summary = summarize(paragraph)

            if results:
                results.news_paragraph = paragraph
                results.news_summary = summary            
                db.session.commit()
                return render_template('blogs.html', blogs_t = results.news_paragraph, blogs_s = results.news_summary)
            else:
                new_paragraph = News(coin, paragraph, summary)
                db.session.add(new_paragraph)
                db.session.commit()
                return render_template('blogs.html', blogs_t = new_paragraph.news_paragraph, blogs_s = new_paragraph.news_summary)

        return render_template('blogs.html')

@app.route('/blogs', methods=['GET', 'POST'])
def blogs():
    if request.method == 'POST':
        coin = request.form.get('coin')
        results = Blogs.query.filter_by(coin_name = coin).first()

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(ChromeDriverManager().install(), options = options)
        driver.get('https://coinmarketcap.com/currencies/' + coin)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        if results:
            return render_template('blogs.html', blogs_t = results.blogs_paragraph, blogs_s = results.blogs_summary)
        else:
            blogsList = soup.select('div.sc-16r8icm-0.kjciSH.contentClosed.hasShadow, p')
            text = [lists.text for lists in blogsList[4:-8]]
            paragraph = ' '.join(text)
            summary = summarize(paragraph)

            new_paragraph = Blogs(coin, paragraph, summary)
            db.session.add(new_paragraph)
            db.session.commit()
            return render_template('blogs.html', blogs_t = new_paragraph.blogs_paragraph, blogs_s = new_paragraph.blogs_summary)
    return render_template('blogs.html', blogs_p = 'JOPA')

if __name__ == '__main__':
    app.run(debug=True) 
