-- updates to make schema.sql schemav2.sql

ALTER TABLE hosts ADD cohort varchar(256) NOT NULL DEFAULT '';
ALTER TABLE times ADD isv6  tinyint(1) NOT NULL default 0;
ALTER TABLE times ADD https tinyint(1) NOT NULL default 0;

DROP TABLE IF EXISTS `metadata`;
CREATE TABLE `metadata` (
  `name` varchar(255) default NULL,
  `value` varchar(255) default NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `log`;
CREATE TABLE `log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `modified` timestamp NOT NULL,
  `value` varchar(65535) default NULL,
  PRIMARY KEY (`id`),
  KEY `modified` (`modified`),
  KEY `value` (`value` (256))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
