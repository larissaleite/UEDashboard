# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, make_response, request, flash, json
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import datetime
  
app = Flask(__name__)

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://root:root@localhost:3306/sinfominer?charset=utf8'
SQLALCHEMY_BINDS = {
    'db_commits': 'mysql+mysqldb://root:root@localhost:3306/sinfominer?charset=utf8',
    'db_events': 'mysql+mysqldb://root:root@localhost:3306/uedashboard?charset=utf8'
}

app.config['SQLALCHEMY_BINDS'] = SQLALCHEMY_BINDS
db = SQLAlchemy(app) 

user = "arthurmacedo"

months_map = { '1' : "Jan", '2' : "Feb", '3' : "Mar", '4' : "Apr", '5' : "May", '6' : "Jun", '7' : "Jul", '8' : "Aug", '9' : "Sep", '10' : "Oct" , '11' : "Nov", '12' : "Dec" }

def get_all_users():
	sql = text('select distinct developer from commit;')
	result = db.get_engine(app, 'db_commits').execute(sql)

	users = []

	for row in result:
		users.append(str(row["developer"]))
	return users

def get_months_ordered():
	months = []
	sql = text('select distinct MONTH(date) as month from commit;')
	result = db.get_engine(app, 'db_commits').execute(sql)
	
	for row in result:
		months.append(int(row["month"]))
	return months

def get_months_categories():
	months = get_months_ordered()
	months_categories = []

	for month in months:
		month_name = months_map[str(month)]
		months_categories.append(month_name)
	return months_categories

def get_commits_user():
	commits = []
	commits_by_month = []
	for month in get_months_ordered():
		sql = text("select count(*) from commit where author='"+user+"' and MONTH(date)="+str(month))
		result = db.get_engine(app, 'db_commits').execute(sql)
		n = str(result.fetchone()[0])
		commits_by_month.append(int(n))

	commits.append({ 'data' : commits_by_month, 'name' : str(user) })

	return commits

def get_events_user():
	events = []
	sql = text("select commit.id as id_commit, commit.date, commit.message, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id where commit.developer='"+user+"'")
	result = db.get_engine(app, 'db_events').execute(sql)
#	sql = text("select modification.file, modification.type from modification inner join commit on commit.id = modification.id_commit where commit.id="+id_commit+";")
	for row in result:
		events.append({ 'date' : row["date"], 'commit_message' : row["message"], 'message' : row["msg"], 'type' : row["type"], 'id' : row["id"], 'id_commit' : row["id_commit"] })
	return events

def get_events_team():
	events = []
	sql = text("select commit.date, commit.message, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id")
	result = db.get_engine(app, 'db_events').execute(sql)
	for row in result:
		events.append({ 'date' : row["date"], 'commit_message' : row["message"], 'message' : row["msg"], 'type' : row["type"], 'id' : row["id"] })
	return events

#TEMPLATE FILES
@app.route('/', methods = ['POST', 'GET'])
def show_home_page():
	commits = get_commits_user()
	months_categories = get_months_categories()
	events = get_events_user()
	return render_template('index.html', user=user, commits=commits, months_categories=months_categories, events=events)

@app.route('/team/commits')
def show_team_commits():
	sql = text('select developer, count(*) from commit group by developer order by count(*) desc limit 10;')
	result = db.get_engine(app, 'db_commits').execute(sql)
	commits = []

	for row in result:
		developer = str(row["developer"])
		commits_by_month = []

		if developer != user:
			for month in get_months_ordered():
				sql = text("select count(*) from commit where developer='"+developer+"' and MONTH(date)="+str(month))
				result = db.get_engine(app, 'db_commits').execute(sql)
				n = str(result.fetchone()[0])
				commits_by_month.append(int(n))
			commits.append({ 'data' : commits_by_month, 'name' : developer })

	months_categories = get_months_categories()
	return render_template('team-commits.html', commits=commits, user=user, months_categories=months_categories)

# REST API
@app.route('/api/commits', methods = ['GET'])
def get_all_commits():
	sql = text('select * from commit')
	result = db.get_engine(app, 'db_commits').execute(sql)
	commits = []
	for row in result:
		commits.append({ 'developer' : row["developer"], 'date' : row["date"] })

	return commits

@app.route('/api/commits_detail', methods = ['POST'])
def get_detail_commit():
	commits_detail = []

	id_commit = request.json["id_commit"]

	sql = text("select modification.file, modification.type from modification inner join commit on commit.id = modification.id_commit where commit.id="+id_commit+";")
  	result = db.get_engine(app, 'db_events').execute(sql)
  	modifications = []
  	for row in result:
  		modifications.append({ 'file' : row["file"], 'type' : row["type"] })

  	sql = text("select commit.message, commit.developer, commit.date from commit where id="+id_commit+";")
  	result = db.get_engine(app, 'db_events').execute(sql)
  	commit = result.fetchone()
  	commits_detail.append({ 'message' : commit["message"], 'developer' : commit["developer"], 'date' : json.dumps(commit["date"].isoformat()), 'modifications' : modifications })

  	return jsonify(commits_detail=commits_detail)
  	 

if __name__ == '__main__':
	app.secret_key = 'secret key'
	app.run(debug=True)