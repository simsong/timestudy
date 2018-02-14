install:
	@echo "Installing html and CGI scripts; please verify differences in config.ini"
	mkdir -p /var/www/html /var/www/cgi-bin/etc
	install html/index.html		   /var/www/html/
	install search.py db.py		   /var/www/cgi-bin/
	install etc/*			   /var/www/cgi-bin/etc/
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
	@python3 db.py --dumpdb | gzip -9 >  database.sql.gz


full:
	@echo Make and publish all the graphs
	python3 graph_gen_html_page.py 
	mkdir -p /var/www/html/debug/hostplots
	mv -f plots/*.html /var/www/html/debug/
	mv -f plots/hostplots/*.png /var/www/html/debug/hostplots
	chcon -R -t httpd_sys_rw_content_t /var/www/html/debug


quick:
	@echo Quick test of graph system
	mkdir -p plots/hostplots
	python3 graph_gen_html_page.py --host=airnow.gov --debug --nosizes
	cp -r plots /var/www/html/debug/
	chcon -R -t httpd_sys_rw_content_t /var/www/html/debug
	@echo check out http://timedb.simson.net/debug/plots/

