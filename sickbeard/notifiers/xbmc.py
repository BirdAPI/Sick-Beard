# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import urllib, urllib2
import socket
import sys
import base64
import time, struct
import sqlite3

#import config

import sickbeard

from sickbeard import logger
from sickbeard import common

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

class XBMCNotifier:

    def notify_snatch(self, ep_name):
        if sickbeard.XBMC_NOTIFY_ONSNATCH:
            self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.XBMC_NOTIFY_ONDOWNLOAD:
            self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        self._notifyXBMC("Testing XBMC notifications from Sick Beard", "Test Notification", host, username, password, force=True)

    def update_library(self, show_name):
        if sickbeard.XBMC_UPDATE_LIBRARY:
            for curHost in [x.strip() for x in sickbeard.XBMC_HOST.split(",")]:
                # do a per-show update first, if possible
                if not self._update_library(curHost, showName=show_name) and sickbeard.XBMC_UPDATE_FULL:
                    # do a full update if requested
                    logger.log(u"Update of show directory failed on " + curHost + ", trying full update as requested", logger.ERROR)
                    self._update_library(curHost)


    def _sendToXBMC(self, command, host, username=None, password=None):
        '''
        Handles communication with XBMC servers
    
        command - Dictionary of field/data pairs, encoded via urllib.urlencode and
        passed to /xbmcCmds/xbmcHttp
    
        host - host/ip + port (foo:8080)
        '''
    
        if not username:
            username = sickbeard.XBMC_USERNAME
        if not password:
            password = sickbeard.XBMC_PASSWORD
    
        for key in command:
            if type(command[key]) == unicode:
                command[key] = command[key].encode('utf-8')
    
        enc_command = urllib.urlencode(command)
        logger.log(u"Encoded command is " + enc_command, logger.DEBUG)
        # Web server doesn't like POST, GET is the way to go
        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)
    
        try:
            # If we have a password, use authentication
            req = urllib2.Request(url)
            if password:
                logger.log(u"Adding Password to XBMC url", logger.DEBUG)
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
    
            logger.log(u"Contacting XBMC via url: " + url, logger.DEBUG)
            handle = urllib2.urlopen(req)
            response = handle.read()
            logger.log(u"response: " + response, logger.DEBUG)
        except IOError, e:
            # print "Warning: Couldn't contact XBMC HTTP server at " + host + ": " + str(e)
            logger.log(u"Warning: Couldn't contact XBMC HTTP server at " + host + ": " + str(e))
            response = ''
    
        return response

    def _notifyXBMC(self, input, title="Sick Beard", host=None, username=None, password=None, force=False):
    
        if not sickbeard.USE_XBMC and not force:
            logger.log("Notification for XBMC not enabled, skipping this notification", logger.DEBUG)
            return False
    
        if not host:
            host = sickbeard.XBMC_HOST
        if not username:
            username = sickbeard.XBMC_USERNAME
        if not password:
            password = sickbeard.XBMC_PASSWORD
    
        logger.log(u"Sending notification for " + input, logger.DEBUG)
    
        fileString = title + "," + input
    
        for curHost in [x.strip() for x in host.split(",")]:
            command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' +fileString + ')' }
            logger.log(u"Sending notification to XBMC via host: "+ curHost +"username: "+ username + " password: " + password, logger.DEBUG)
            request = self._sendToXBMC(command, curHost, username, password)

    def _update_library(self, host, showName=None):
    
        if not sickbeard.USE_XBMC:
            logger.log("Notifications for XBMC not enabled, skipping library update", logger.DEBUG)
            return False
    
        logger.log(u"Updating library in XBMC", logger.DEBUG)
    
        if not host:
            logger.log('No host specified, no updates done', logger.DEBUG)
            return False
    
        # if we're doing per-show
        if showName:
            pathSql = 'select path.strPath from path, tvshow, tvshowlinkpath where ' \
                'tvshow.c00 = "%s" and tvshowlinkpath.idShow = tvshow.idShow ' \
                'and tvshowlinkpath.idPath = path.idPath' % (showName)
    
            # Use this to get xml back for the path lookups
            xmlCommand = {'command': 'SetResponseFormat(webheader;false;webfooter;false;header;<xml>;footer;</xml>;opentag;<tag>;closetag;</tag>;closefinaltag;false)'}
            # Sql used to grab path(s)
            sqlCommand = {'command': 'QueryVideoDatabase(%s)' % (pathSql)}
            # Set output back to default
            resetCommand = {'command': 'SetResponseFormat()'}
    
            # Set xml response format, if this fails then don't bother with the rest
            request = self._sendToXBMC(xmlCommand, host)
            if not request:
                return False
    
            sqlXML = self._sendToXBMC(sqlCommand, host)
            request = self._sendToXBMC(resetCommand, host)
    
            if not sqlXML:
                logger.log(u"Invalid response for " + showName + " on " + host, logger.DEBUG)
                return False
    
            encSqlXML = urllib.quote(sqlXML,':\\/<>')
            try:
                et = etree.fromstring(encSqlXML)
            except SyntaxError, e:
                logger.log("Unable to parse XML returned from XBMC: "+str(e), logger.ERROR)
                return False
    
            paths = et.findall('.//field')
    
            if not paths:
                logger.log(u"No valid paths found for " + showName + " on " + host, logger.DEBUG)
                return False
    
            for path in paths:
                # Don't need it double-encoded, gawd this is dumb
                unEncPath = urllib.unquote(path.text)
                logger.log(u"XBMC Updating " + showName + " on " + host + " at " + unEncPath, logger.DEBUG)
                updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video, %s)' % (unEncPath)}
                request = self._sendToXBMC(updateCommand, host)
                if not request:
                    return False
                # Sleep for a few seconds just to be sure xbmc has a chance to finish
                # each directory
                if len(paths) > 1:
                    time.sleep(5)
        else:
            logger.log(u"XBMC Updating " + host, logger.DEBUG)
            updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}
            request = self._sendToXBMC(updateCommand, host)
    
            if not request:
                return False
    
        return True

# Wake function
def wakeOnLan(ethernet_address):
    addr_byte = ethernet_address.split(':')
    hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16),
    int(addr_byte[1], 16),
    int(addr_byte[2], 16),
    int(addr_byte[3], 16),
    int(addr_byte[4], 16),
    int(addr_byte[5], 16))

    # Build the Wake-On-LAN "Magic Packet"...
    msg = '\xff' * 6 + hw_addr * 16

    # ...and send it to the broadcast address using UDP
    ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ss.sendto(msg, ('<broadcast>', 9))
    ss.close()

# Test Connection function
def isHostUp(host, port, timeout = None):

    (family, socktype, proto, garbage, address) = socket.getaddrinfo(host, port)[0]
    s = socket.socket(family, socktype, proto)
    
    try:
        if timeout is not None:
            s.settimeout(timeout)
        s.connect(address)
        return "Up"
    except:
        return "Down"


def checkHost(host, port):

    # we should try to get this programmatically from the IP
    mac = ""

    i=1
    while isHostUp(host,port)=="Down" and i<4:
        wakeOnLan(mac)
        time.sleep(20)
        i=i+1


# Returns the first available xbmc host that is online, or None if none are online
def getFirstOnlineHost(timeout = 0.5):
    anyHostsUp = False
    # Check each host if they are up and use the first one available
    for curHost in [x.strip() for x in sickbeard.XBMC_HOST.split(",")]:
        colonIndex = curHost.find(":")
        if colonIndex != -1:
            # Get everything before the colon as the Host
            host = curHost[:colonIndex]
            # Get everything after the colon as the Port
            port = curHost[colonIndex + 1:]
            # Check if the xbmc host is up (using a 0.5 second timeout to prevent slowdowns from down hosts) -- But will this cause false negatives?
            if sickbeard.notifiers.xbmc.isHostUp(host, port, timeout) == "Up":
                onlineHost = curHost
                anyHostsUp = True
                break
    return onlineHost if anyHostsUp else None
         

         
XBMC_DB_FILENAME = "C:/Users/BirdTV/AppData/Roaming/XBMC/userdata/Database/MyVideos34.db"

MYSQL_HOST = "localhost"
MYSQL_USERNAME = "xbmc"
MYSQL_PASSWORD = "xbmc"

XBMC_API = "XBMC_API"
SQLITE = "SQLITE"
MYSQL = "MYSQL"

XBMC_WATCHED_METHOD = XBMC_API
         
class XBMCWatchedIntegration:
    
    # Returns the watched result for each episode in sbSqlEpisodes or None if there was an error
    def getWatchedEpisodes(self, showName, sbSqlEpisodes):   
        sqlQuery = """
                SELECT  episode.c12 AS season, 
                        episode.c13 AS epNumber, 
                        files.playCount IS NOT NULL AS watched 
                FROM episode
                JOIN files ON episode.idFile = files.idFile
                JOIN tvshowlinkepisode ON episode.idEpisode = tvshowlinkepisode.idEpisode
                JOIN tvshow ON tvshowlinkepisode.idShow = tvshow.idShow
                WHERE tvshow.c00 = "%s"
                """ % ( showName )
        rows = self.executeQuery(sqlQuery, 3)
        if rows is None:
            return None
        else:
            return self.__matchSqlWatchedEpisodeResults(sbSqlEpisodes, rows)
        

    # Given a list of xml fields and the fields per group
    # This will return a list of tuples which contain fieldsPerGroup item each
    def groupXmlFields(self, allFields, fieldsPerGroup):
        resultLength = len(allFields)
        rows = []
        if resultLength % fieldsPerGroup != 0:
            rows = None
        else:
            # Loop through and grab the itms out "fieldsPerGroup" items at a time
            i = 0
            while i + fieldsPerGroup <= resultLength:
                #row = []
                #for j in range(fieldsPerGroup):
                #    row.append(allFields[i+j].text)
                row = [ allFields[i+j].text for j in range(fieldsPerGroup) ]
                rows.append(row)
                i += fieldsPerGroup
        return rows

        
    def executeQuery(self, sqlQuery, columnsCount):
        if XBMC_WATCHED_METHOD == XBMC_API:
            return self.__executeQuery_XBMC_API(sqlQuery, columnsCount)
        elif XBMC_WATCHED_METHOD == SQLITE or XBMC_WATCHED_METHOD == MYSQL:
            return self.__executeQuery_SQL(sqlQuery)
        else:
            return None

            
    def __executeQuery_XBMC_API(self, sqlQuery, columnsCount):
        onlineHost = getFirstOnlineHost()
        if onlineHost is None:
            logger.log(u"No XBMC hosts are responding", logger.ERROR)
            return None
            
        # Use this to get xml back for the path lookups
        xmlCommand = {'command': 'SetResponseFormat(webheader;false;webfooter;false;header;<xml>;footer;</xml>;opentag;<tag>;closetag;</tag>;closefinaltag;false)'}
        # SQL Query
        sqlCommand = {'command': 'QueryVideoDatabase(%s)' % (sqlQuery)}
        # Set output back to default
        resetCommand = {'command': 'SetResponseFormat()'}
        # Set xml response format, only continue if this works
        request = sickbeard.notifiers.xbmc_notifier._sendToXBMC(xmlCommand, onlineHost)
        if not request:
            logger.log(u"XBMC host failed to set output mode", logger.ERROR)
            return None
            
        sqlXML = sickbeard.notifiers.xbmc_notifier._sendToXBMC(sqlCommand, onlineHost)
        request = sickbeard.notifiers.xbmc_notifier._sendToXBMC(resetCommand, onlineHost)
        encSqlXML = urllib.quote(sqlXML,':\\/<>')
        try:
            et = etree.fromstring(encSqlXML)
        except SyntaxError, e:
            logger.log("Unable to parse XML returned from XBMC: "+str(e), logger.ERROR)
            return None
        fields = et.findall('.//field')
        rows = self.groupXmlFields(fields, columnsCount)
        return rows
         
                
    def __executeQuery_SQL(self, sqlQuery):
        if XBMC_WATCHED_METHOD == SQLITE:
            conn = sqlite3.connect(XBMC_DB_FILENAME, 20)
        elif XBMC_WATCHED_METHOD == MYSQL:
            try:
                import MySQLdb
            except ImportError:
                return None
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USERNAME, passwd=MYSQL_PASSWORD, db="xbmc_video")
        else: 
            return None
        cursor = conn.cursor()
        cursor.execute(sqlQuery)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    

    def __matchSqlWatchedEpisodeResults(self, sbSqlEpisodes, sqlRows):
        watchedResults = {}
        for epResult in sbSqlEpisodes:
            watched = "N/A"
            for row in sqlRows:
                if int(row[0]) == int(epResult["season"]) and int(row[1]) == int(epResult["episode"]):
                    watched = "Watched" if int(row[2]) == 1 else "New"
                    break
            watchedResults[epResult["episode_id"]] = watched
        return watchedResults


notifier = XBMCNotifier