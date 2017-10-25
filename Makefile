install:
	install html/index.html		   /var/www/html/
	install search.py db.py config.ini /var/www/cgi-bin/

top-100m.csv:
	wget http://s3.amazonaws.com/alexa-static/top-1m.csv.zip
	unzip top-1m.csv.zip
	/bin/rm -f top-1m.csv.zip

schema.sql:
	python3 db.py --dumpschema schema.sql

backup:
	python3 db.py --dumpdb database.sql

