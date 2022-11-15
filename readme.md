# My Talks
My talks is a chat application connecting you with other random stranger. Server is created with Flask-socketio and SQLite and serves jinja templates styled with bootstrap.
## Demo
* App demo is hosted on https://my-talks.fly.dev
## Content
When opening the app, you can either sign in or sign up. After either of these your input is validated, and user session is created.
Hence, you can enter the chat screen where you might wait for someone else to connect.
If you accidentally press refresh button or accidentally close the browser your connection to the other user is not lost, you will be reconnected. 
After pressing leave chat button, you can write few words about your experience. The rating is saved in SQLite database.
## Screenshots
![Home page](./screenshots/sc1.png "Home page")
![Chat page](./screenshots/sc2.png "Chat page")
## How to run locally
1. pip install -r requirements.txt
2. python server.py
## Todo
* Write unit tests
* Use logger

## Changelog
* / 59f1d1f / Swithed from vanilla Sqlite to SQLalchemy
* / 59f1d1f / Changed error message style in forms

