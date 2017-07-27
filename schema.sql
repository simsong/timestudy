-- MySQL dump 10.13  Distrib 5.6.29, for Linux (x86_64)
--
-- Host: mysql.simson.net    Database: slgtimedb
-- ------------------------------------------------------
-- Server version	5.6.25-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dated`
--

DROP TABLE IF EXISTS `dated`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dated` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(255) DEFAULT NULL,
  `ipaddr` varchar(39) DEFAULT NULL,
  `ipv6` tinyint(1) DEFAULT '0',
  `qdate` date DEFAULT NULL,
  `qfirst` time DEFAULT NULL,
  `qlast` time DEFAULT NULL,
  `qcount` int(11) DEFAULT '0',
  `ecount` int(11) NOT NULL DEFAULT '0',
  `wtcount` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `host` (`host`,`ipaddr`,`qdate`),
  KEY `ipaddr` (`ipaddr`),
  KEY `qdate` (`qdate`,`qlast`),
  KEY `ecount` (`ecount`),
  KEY `wtcount` (`wtcount`),
  KEY `qcount` (`qcount`)
) ENGINE=InnoDB AUTO_INCREMENT=39936417 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hosts`
--

DROP TABLE IF EXISTS `hosts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hosts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(255) NOT NULL,
  `recordall` tinyint(1) DEFAULT '0',
  `usg` tinyint(1) NOT NULL DEFAULT '0',
  `qdatetime` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `host` (`host`),
  KEY `qdatetime` (`qdatetime`),
  KEY `usg` (`usg`)
) ENGINE=InnoDB AUTO_INCREMENT=1012049 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `times`
--

DROP TABLE IF EXISTS `times`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `times` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(255) DEFAULT NULL,
  `ipaddr` varchar(39) DEFAULT NULL,
  `ipv6` tinyint(1) DEFAULT '0',
  `qdatetime` datetime DEFAULT NULL,
  `qduration` float DEFAULT NULL,
  `rdatetime` datetime DEFAULT NULL,
  `offset` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `host` (`host`,`ipaddr`,`qdatetime`),
  KEY `delta` (`offset`),
  KEY `qdatetime` (`qdatetime`),
  KEY `ipaddr` (`ipaddr`)
) ENGINE=InnoDB AUTO_INCREMENT=6340999 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-06-26 18:44:42

