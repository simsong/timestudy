install:
	@echo "Installing html and CGI scripts; please verify differences in config.ini"
	install html/index.html		   /var/www/html/
	install search.py db.py /var/www/cgi-bin/
	diff config.ini /var/www/cgi-bin/config.ini

clean:
	find . -name '*~' -print -exec rm {} \;

top-100m.csv:
	wget http://s3.amazonaws.com/alexa-static/top-1m.csv.zip
	unzip top-1m.csv.zip
	/bin/rm -f top-1m.csv.zip

schema.sql: Makefile webtime.py
	python3 db.py --dumpschema | sed 's/ AUTO_INCREMENT=[0-9]*//g' > schema.sql

backup:
	python3 db.py --dumpdb > database.sql

