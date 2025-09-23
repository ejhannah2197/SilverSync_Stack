from flask import Flask

app = Flask(__name__) #create the app object

from app import routes #import routes module from app package